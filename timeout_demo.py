# timeout_demo.py
import time, os, uuid, grpc, json
from mcp2pc import two_phase_pb2, two_phase_pb2_grpc
from web3 import Web3
from dotenv import load_dotenv

def run_and_check_timeout():
    load_dotenv()
    w3 = Web3(Web3.HTTPProvider(os.getenv("ALCHEMY_RPC_URL")))
    abi      = json.load(open("abi/TwoPhaseAdapter.json"))
    adapters = json.load(open("config/adapters.json"))

    tx_id = uuid.uuid4().hex
    ch    = grpc.insecure_channel("localhost:50051")
    stub  = two_phase_pb2_grpc.CoordinatorStub(ch)

    # use a very small timeout to wait it out
    tb = 2
    print(f"Prepare with timeout_blocks={tb}")
    prep_req = two_phase_pb2.PrepareRequest(
        transaction_id = tx_id,
        operations     = ["SET y 2"],
        timeout_blocks = tb,
        onchain_recipient="0x0000000000000000000000000000000000000000",
        onchain_amount=0
    )
    votes = list(stub.Prepare(prep_req))
    print("  votes:", [(v.shard_id, v.status) for v in votes])

    # if all READY, wait past the deadline and then call Abort
    if all(v.status == two_phase_pb2.PrepareResponse.READY for v in votes):
        print("waiting for timeout…")
        # check current height and deadline
        from common.timeout_manager import TimeoutManager
        from common.lightclient import LightClient
        tm = TimeoutManager(LightClient(os.getenv("ALCHEMY_RPC_URL")))
        tm.start(tx_id, tb)
        while tm.client.get_block_height() <= tm.deadlines[tx_id]:
            print("  block", tm.client.get_block_height(), "≤", tm.deadlines[tx_id])
            time.sleep(10)
        print("  deadline passed, now aborting…")
        stub.Abort(two_phase_pb2.AbortRequest(transaction_id=tx_id))
    else:
        print("  already aborted in Phase 1")

    print("\n-- on-chain statuses after timeout abort --")
    padded = bytes.fromhex(tx_id).rjust(32, b"\x00")
    for sid, addr in adapters.items():
        c = w3.eth.contract(address=addr, abi=abi)
        s = c.functions.transactions(padded).call()[4]
        print(f"  {sid:6s} status =", ["None","Pending","Committed","Aborted"][s])

if __name__ == "__main__":
    run_and_check_timeout()
