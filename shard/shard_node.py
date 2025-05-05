# shard/shard_node.py
import grpc, threading
from concurrent import futures
from pathlib import Path
import json, os, logging

from web3 import Web3
from dotenv import load_dotenv

from mcp2pc import two_phase_pb2, two_phase_pb2_grpc
from collections import defaultdict

from common.timeout_manager import TimeoutManager
from common.lightclient import LightClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# load environment
load_dotenv()

class Shard(two_phase_pb2_grpc.ShardServicer):
    def __init__(self, shard_id, rpc_url: str, adapter_address: str):
        self.id = shard_id
        self.state = {}
        self.prepared = defaultdict(dict)

        # off‐chain timeout manager
        self.timeout_mgr = TimeoutManager(LightClient(rpc_url))

        # set up Web3 + account for on‐chain calls
        self.w3 = LightClient(rpc_url).w3

        # pick up the shard-specific key from .env, e.g. SHARD1_KEY
        key_env_var = f"{shard_id.upper()}_KEY"
        priv_key = os.getenv(key_env_var)
        if not priv_key:
            raise RuntimeError(f"Missing {key_env_var} in environment")
        self.account = self.w3.eth.account.from_key(priv_key)
        self.w3.eth.default_account = self.account.address

        # load the adapter ABI & contract instance
        abi_path = Path(__file__).parent.parent / "abi" / "TwoPhaseAdapter.json"
        with open(abi_path) as f:
            abi = json.load(f)
        self.adapter = self.w3.eth.contract(address=adapter_address, abi=abi)

        logger.info(f"Shard {self.id} initialized; adapter at {adapter_address}")

    # --- off‐chain 2PC handlers ---

    def Prepare(self, request, context):
        # record block‐height deadline on first Prepare
        if request.transaction_id not in self.timeout_mgr.deadlines:
            self.timeout_mgr.start(request.transaction_id, request.timeout_blocks)

        # auto‐abort if deadline passed
        if self.timeout_mgr.is_expired(request.transaction_id):
            return two_phase_pb2.PrepareResponse(
                status=two_phase_pb2.PrepareResponse.ABORT,
                shard_id=self.id
            )

        # otherwise stage ops
        self.prepared[request.transaction_id] = request.operations
        return two_phase_pb2.PrepareResponse(
            status=two_phase_pb2.PrepareResponse.READY,
            shard_id=self.id
        )

    def Commit(self, request, context):
        tx = request.transaction_id
        ops = self.prepared.pop(tx, [])
        for op in ops:
            parts = op.split(maxsplit=2)
            if len(parts)==3 and parts[0].upper()=="SET":
                _, key, val = parts
                self.state[key] = val
        return two_phase_pb2.Empty()

    def Abort(self, request, context):
        self.prepared.pop(request.transaction_id, None)
        return two_phase_pb2.Empty()

    def Rollback(self, request, context):
        return self.Abort(request, context)

    # --- on‐chain adapter handlers ---

    def _sign_and_send(self, tx_dict):
        tx_dict.setdefault("chainId", self.w3.eth.chain_id)
        tx_dict.setdefault("nonce", self.w3.eth.get_transaction_count(self.account.address))
        signed = self.account.sign_transaction(tx_dict)
        return self.w3.eth.send_raw_transaction(signed.raw_transaction)

    def LockOnChain(self, request, context):
        # parse & pad the tx ID
        raw      = bytes.fromhex(request.transaction_id)
        tx_id32  = raw.rjust(32, b'\x00')

        # normalize the recipient address
        recipient = Web3.to_checksum_address(request.recipient)

        # build with a fixed gas limit (skip estimateGas)
        tx = self.adapter.functions.lockFunds(
            tx_id32,
            recipient,
            request.deadline
        ).build_transaction({
            "from":  self.account.address,
            "value": request.amount,
            "gas":   200_000,
        })

        tx_hash = self._sign_and_send(tx)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            logger.error(f"[{self.id}] onChain reverted: tx={tx_hash.hex()} status={receipt.status}")
        return two_phase_pb2.TxHash(hash=receipt.transactionHash.hex())

    def CommitOnChain(self, request, context):
        raw     = bytes.fromhex(request.transaction_id)
        tx_id32 = raw.rjust(32, b'\x00')

        try:
            tx = self.adapter.functions.commit(tx_id32).build_transaction({
                "from": self.account.address,
                "gas":  100_000,
            })
            tx_hash = self._sign_and_send(tx)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status != 1:
                # on‐chain revert
                logger.error(f"[{self.id}] commit(tx={request.transaction_id}) reverted on‐chain, status=0")
                # turn it into a gRPC error
                context.set_details("CommitOnChain reverted (past deadline or not pending)")
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                return two_phase_pb2.TxHash(hash=tx_hash.hex())

            logger.info(f"[{self.id}] CommitOnChain succeeded tx={tx_hash.hex()}")
            return two_phase_pb2.TxHash(hash=receipt.transactionHash.hex())

        except Exception as e:
            # catch anything else (ABI mismatch, RPC error, etc)
            logger.exception(f"[{self.id}] CommitOnChain exception for tx={request.transaction_id}")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return two_phase_pb2.TxHash(hash="")

    def ReclaimOnChain(self, request, context):
        raw     = bytes.fromhex(request.transaction_id)
        tx_id32 = raw.rjust(32, b'\x00')

        try:
            tx = self.adapter.functions.reclaim(tx_id32).build_transaction({
                "from": self.account.address,
                "gas":  100_000,
            })
            tx_hash = self._sign_and_send(tx)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status != 1:
                logger.error(f"[{self.id}] reclaim(tx={request.transaction_id}) reverted on‐chain, status=0")
                context.set_details("ReclaimOnChain reverted (too early or not pending)")
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                return two_phase_pb2.TxHash(hash=tx_hash.hex())

            logger.info(f"[{self.id}] ReclaimOnChain succeeded tx={tx_hash.hex()}")
            return two_phase_pb2.TxHash(hash=receipt.transactionHash.hex())

        except Exception as e:
            logger.exception(f"[{self.id}] ReclaimOnChain exception for tx={request.transaction_id}")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return two_phase_pb2.TxHash(hash="")


def serve(shard_id, port):
    base = Path(__file__).parent.parent

    # off‐chain RPC endpoints
    with open(base / 'config' / 'shard_rpcs.json') as f:
        rpc_cfg = json.load(f)
    rpc_url = rpc_cfg[shard_id]

    # on‐chain adapter addresses
    with open(base / 'config' / 'adapters.json') as f:
        adapter_cfg   = json.load(f)
    adapter_address = adapter_cfg[shard_id]

    server = grpc.server(futures.ThreadPoolExecutor())
    two_phase_pb2_grpc.add_ShardServicer_to_server(
        Shard(shard_id, rpc_url, adapter_address), server
    )
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--id', required=True)
    p.add_argument('--port', type=int, required=True)
    args = p.parse_args()
    serve(args.id, args.port)
