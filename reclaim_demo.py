#!/usr/bin/env python3
import os, time, uuid, grpc
from dotenv import load_dotenv
from mcp2pc import two_phase_pb2, two_phase_pb2_grpc
from common.timeout_manager import TimeoutManager
from common.lightclient     import LightClient

load_dotenv()

RPC_URL  = os.getenv("ALCHEMY_RPC_URL")
TIMEOUT  = 3  # in blocks
AMOUNT   = 1_000_000_000_000_000  # 0.001 ETH
RECIP    = "0x24c881bF947a922cfb46794DEC370036d413b4B2"  # set in .env
ENDPOINT = "localhost:50051"

# set up
stub = two_phase_pb2_grpc.CoordinatorStub(
    grpc.insecure_channel(ENDPOINT)
)
tm = TimeoutManager(LightClient(RPC_URL))

# off‐chain Prepare + on‐chain lock
tx_id = uuid.uuid4().hex
prep = two_phase_pb2.PrepareRequest(
    transaction_id    = tx_id,
    operations        = ["SET a 1"],
    timeout_blocks    = TIMEOUT,
    onchain_recipient = RECIP,
    onchain_amount    = AMOUNT
)
votes = list(stub.Prepare(prep))
print("off-chain votes:", [(v.shard_id, v.status) for v in votes])
if any(v.status != two_phase_pb2.PrepareResponse.READY for v in votes):
    print("aborting early; no on-chain locks")
    exit(1)

# single Commit to locks
stub.Commit(two_phase_pb2.CommitRequest(transaction_id=tx_id))
print(f"lockFunds submitted for tx {tx_id}")

# remember deadline
tm.start(tx_id, TIMEOUT)
dl = tm.deadlines[tx_id]
print(f"  deadline at block {dl}")

# wait til after deadline
while tm.client.get_block_height() <= dl:
    print(f"block={tm.client.get_block_height()} ≤ {dl}")
    time.sleep(5)

# Abort to on-chain reclaim
print("deadline passed; reclaiming on-chain")
stub.Abort(two_phase_pb2.AbortRequest(transaction_id=tx_id))

print("Done.  Now inspect each adapter contract to confirm status=Aborted.")
