# coordinator/coordinator.py
import grpc, json, threading, os, logging
from concurrent import futures

from mcp2pc import two_phase_pb2, two_phase_pb2_grpc
from common.timeout_manager import TimeoutManager
from common.lightclient     import LightClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Coordinator(two_phase_pb2_grpc.CoordinatorServicer):
    def __init__(self, shard_cfg, rpc_cfg, adapter_cfg, default_timeout_blocks):
        """
        shard_cfg:   { shard_id: "host:port", ... }
        rpc_cfg:     { shard_id: "https://...rpc", ... }
        adapter_cfg: { shard_id: "0xContractAddress...", ... }
        default_timeout_blocks: number of blocks before timeout
        """
        self.default_tb = default_timeout_blocks

        # off-chain 2PC stubs
        self.shard_stubs = {
            sid: two_phase_pb2_grpc.ShardStub(grpc.insecure_channel(addr))
            for sid, addr in shard_cfg.items()
        }

        # reuse same stubs for on-chain adapter calls
        self.chain_stubs_onchain = self.shard_stubs

        # per-shard timeout managers
        self.timeout_mgrs = {
            sid: TimeoutManager(LightClient(rpc_cfg[sid]))
            for sid in shard_cfg
        }

        # on-chain adapter addresses
        self.adapters = adapter_cfg

        # in-memory store for on-chain params
        self.tx_meta = {}

        logger.info(f"Coordinator listening on 50051; shards={list(shard_cfg)}; default_tb={self.default_tb}")

    def Prepare(self, request, context):
        tx_id = request.transaction_id
        tb    = request.timeout_blocks or self.default_tb
        logger.info(f"[Coordinator] Prepare(tx={tx_id}, timeout_blocks={tb})")

        # record block-height deadlines
        for sid, tm in self.timeout_mgrs.items():
            tm.start(tx_id, tb)

        # stash on-chain args for later
        self.tx_meta[tx_id] = {
            "recipient": request.onchain_recipient,
            "amount":    request.onchain_amount,
        }

        # fan-out off-chain Prepare()
        votes, threads = [], []
        def vote_thread(sid, stub):
            try:
                resp = stub.Prepare(request)
                votes.append(resp)
            except grpc.RpcError:
                votes.append(
                    two_phase_pb2.PrepareResponse(
                        status=two_phase_pb2.PrepareResponse.ABORT,
                        shard_id=sid
                    )
                )

        for sid, stub in self.shard_stubs.items():
            t = threading.Thread(target=vote_thread, args=(sid, stub))
            t.start(); threads.append(t)
        for t in threads:
            t.join()

        # stream back all votes to client
        for vote in votes:
            yield vote

    def Commit(self, request, context):
        tx_id = request.transaction_id
        logger.info(f"[Coordinator] Commit full flow for tx={tx_id}")

        # --- On-chain locking step (pull from stash) ---
        meta = self.tx_meta.get(tx_id)
        if not meta:
            raise RuntimeError(f"No metadata for tx {tx_id}")
        recipient = meta["recipient"]
        amount    = meta["amount"]

        for sid, stub in self.chain_stubs_onchain.items():
            deadline = self.timeout_mgrs[sid].deadlines.get(tx_id)
            lock_req = two_phase_pb2.LockRequest(
                transaction_id=tx_id,
                recipient     = recipient,
                amount        = amount,
                deadline      = deadline
            )
            try:
                txh = stub.LockOnChain(lock_req)
                logger.info(f"[Coordinator] LockOnChain on {sid}: {txh.hash}")
            except grpc.RpcError as e:
                logger.error(f"[Coordinator] LockOnChain failed on {sid}: {e}")

        # quick debug: compare current block vs deadline
        any_mgr = next(iter(self.timeout_mgrs.values()))
        current = any_mgr.client.get_block_height()
        logger.info(f"[Coordinator] current block height = {current}, deadline = {deadline}")

        # --- Off-chain commit step ---
        for sid, stub in self.shard_stubs.items():
            try:
                stub.Commit(request, timeout=1)
            except grpc.RpcError:
                logger.warning(f"[Coordinator] off-chain Commit failed on {sid}")

        # --- On-chain finalize step ---
        for sid, stub in self.chain_stubs_onchain.items():
            try:
                txh = stub.CommitOnChain(
                    two_phase_pb2.OnChainRequest(transaction_id=tx_id)
                )
                logger.info(f"[Coordinator] CommitOnChain on {sid}: {txh.hash}")
            except grpc.RpcError as e:
                logger.error(f"[Coordinator] CommitOnChain failed on {sid}: {e}")

        self.tx_meta.pop(tx_id, None)
        return two_phase_pb2.Empty()

    def Abort(self, request, context):
        tx_id = request.transaction_id
        logger.info(f"[Coordinator] Abort full flow for tx={tx_id}")

        # --- Off-chain abort step ---
        for sid, stub in self.shard_stubs.items():
            try:
                stub.Abort(request, timeout=1)
            except grpc.RpcError:
                logger.warning(f"[Coordinator] off-chain Abort failed on {sid}")

        # --- On-chain reclaim step ---
        for sid, stub in self.chain_stubs_onchain.items():
            try:
                txh = stub.ReclaimOnChain(
                    two_phase_pb2.OnChainRequest(transaction_id=tx_id)
                )
                logger.info(f"[Coordinator] ReclaimOnChain on {sid}: {txh.hash}")
            except grpc.RpcError as e:
                logger.error(f"[Coordinator] ReclaimOnChain failed on {sid}: {e}")

        return two_phase_pb2.Empty()

def serve():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    with open(os.path.join(base, 'config', 'shards.json'))      as f:
        shard_cfg   = json.load(f)
    with open(os.path.join(base, 'config', 'shard_rpcs.json')) as f:
        rpc_cfg     = json.load(f)
    with open(os.path.join(base, 'config', 'adapters.json'))   as f:
        adapter_cfg = json.load(f)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    two_phase_pb2_grpc.add_CoordinatorServicer_to_server(
        Coordinator(shard_cfg, rpc_cfg, adapter_cfg, default_timeout_blocks=500),
        server
    )
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
