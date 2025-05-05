# client/client.py

import grpc
import uuid
from mcp2pc import two_phase_pb2, two_phase_pb2_grpc

def run_transaction(state_ops, recipient, amount_wei, timeout_blocks=500):
    tx_id = uuid.uuid4().hex
    stub = two_phase_pb2_grpc.CoordinatorStub(
        grpc.insecure_channel("localhost:50051")
    )

    prep_req = two_phase_pb2.PrepareRequest(
        transaction_id     = tx_id,
        operations         = state_ops,
        timeout_blocks     = timeout_blocks,
        onchain_recipient  = recipient,
        onchain_amount     = amount_wei
    )

    # Phase 1: off-chain vote
    votes = [resp for resp in stub.Prepare(prep_req)]
    if any(v.status != two_phase_pb2.PrepareResponse.READY for v in votes):
        print("Abort triggered")
        stub.Abort(two_phase_pb2.AbortRequest(transaction_id=tx_id))
        return False

    # Phase 2: commit (Coordinator does off-chain Commit + on-chain finalize)
    stub.Commit(two_phase_pb2.CommitRequest(transaction_id=tx_id))
    print(f"Committed on shards {[v.shard_id for v in votes]}")
    return True

if __name__ == "__main__":
    # parameters
    recipient   = "0x24c881bF947a922cfb46794DEC370036d413b4B2"
    amount_wei  = 1_000_000_000_000_000
    state_ops   = ["SET x 42", "SET y 99"]
    timeout_bl  = 500

    print("Starting transaction…")
    success = run_transaction(state_ops, recipient, amount_wei, timeout_blocks=timeout_bl)
    if success:
        print("Transaction completed end-to-end")
    else:
        print("Transaction aborted")
