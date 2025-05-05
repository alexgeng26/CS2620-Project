import grpc
import pytest
from collections import namedtuple

from common.timeout_manager import TimeoutManager
from shard.shard_node       import Shard
from coordinator.coordinator import Coordinator
from mcp2pc                  import two_phase_pb2

# --- Phase A core tests ---------------------------------------------------

def test_timeout_manager_start_and_expiry():
    # LightClient is stubbed by conftest to DummyLightClient
    from common.lightclient import LightClient
    client = LightClient("dummy")
    tm = TimeoutManager(client)
    tm.start("tx", timeout_blocks=5)
    assert not tm.is_expired("tx")
    client._height = 200
    assert tm.is_expired("tx")

def test_shard_prepare_timeout():
    # supply dummy adapter_address
    shard = Shard("shard1", rpc_url="dummy", adapter_address="0x0")
    # Use only off-chain logic: override the timeout manager to our stub
    from common.lightclient import LightClient
    shard.timeout_mgr = TimeoutManager(LightClient("dummy"))

    PrepareReq = namedtuple("PR", ["transaction_id", "operations", "timeout_blocks"])
    req = PrepareReq("tx1", ["SET a 1"], 0)

    # First prepare → READY
    resp1 = shard.Prepare(req, context=None)
    assert resp1.status == two_phase_pb2.PrepareResponse.READY

    # expire and prepare again → ABORT
    shard.timeout_mgr.client._height = 300
    resp2 = shard.Prepare(req, context=None)
    assert resp2.status == two_phase_pb2.PrepareResponse.ABORT

def test_shard_commit_and_rollback():
    shard = Shard("shard1", rpc_url="dummy", adapter_address="0x0")
    tx = "txc"
    shard.prepared[tx] = ["SET x 10", "BAD_OP"]
    Req = namedtuple("R", ["transaction_id"])

    shard.Commit(Req(tx), context=None)
    assert shard.state.get("x") == "10"

    shard.prepared["tx_abort"] = ["SET y 20"]
    shard.Abort(Req("tx_abort"), context=None)
    assert "tx_abort" not in shard.prepared

def test_coordinator_prepare_and_commit():
    # Dummy stub that votes READY then records Commit()
    class Stub:
        def __init__(self, status):
            self.status = status
            self.committed = False
            self.rolled = False
        def Prepare(self, req, *a, **kw):
            return [two_phase_pb2.PrepareResponse(status=self.status, shard_id="s")]
        def Commit(self, req, *a, **kw):
            self.committed = True
        def Rollback(self, req, *a, **kw):
            self.rolled = True

    shard_cfg   = {"s":"addr"}
    rpc_cfg     = {"s":"dummy"}
    adapter_cfg = {"s":"0x0"}
    coord = Coordinator(shard_cfg, rpc_cfg, adapter_cfg, default_timeout_blocks=0)

    # replace our off-chain stubs
    coord.shard_stubs = {"s": Stub(two_phase_pb2.PrepareResponse.READY)}

    # build a PrepareRequest including on-chain fields
    PrepReq = namedtuple("PrepReq",
                         ["transaction_id","operations","timeout_blocks",
                          "onchain_recipient","onchain_amount"])
    req = PrepReq("tx", ["op"], 0, "0x0", 0)

    votes = list(coord.Prepare(req, context=None))
    # flatten in case someone returns a list inside the list
    all_votes = []
    for v in votes:
        if isinstance(v, list):
            all_votes.extend(v)
        else:
            all_votes.append(v)
    assert any(v.status == two_phase_pb2.PrepareResponse.READY for v in all_votes)

    # Commit path (we only care off-chain commit in this unit test)
    CommitReq = namedtuple("CommitReq", ["transaction_id"])
    coord.Commit(CommitReq("tx"), context=None)
    assert coord.shard_stubs["s"].committed

def test_coordinator_abort_path():
    class AbortStub:
        def __init__(self): self.rolled = False
        def Prepare(self, req, *a,**kw):
            return [two_phase_pb2.PrepareResponse(status=two_phase_pb2.PrepareResponse.ABORT,
                                                 shard_id="x")]
        def Commit(self, *a,**kw): pass
        def Rollback(self, req, *a,**kw):
            self.rolled = True

    class ReadyStub(AbortStub):
        def Prepare(self, req, *a,**kw):
            return [two_phase_pb2.PrepareResponse(status=two_phase_pb2.PrepareResponse.READY,
                                                 shard_id="y")]

    adapter_cfg = {"x":"0x0","y":"0x0"}
    coord = Coordinator({"x":"a","y":"b"}, {"x":"u","y":"v"}, adapter_cfg, default_timeout_blocks=0)
    coord.shard_stubs = {"x":AbortStub(), "y":ReadyStub()}

    PrepReq = namedtuple("PrepReq",
                         ["transaction_id","operations","timeout_blocks",
                          "onchain_recipient","onchain_amount"])
    req = PrepReq("t", [], 0, "0x0", 0)

    votes = list(coord.Prepare(req, context=None))
    flat = []
    for v in votes:
        flat.extend(v if isinstance(v, list) else [v])
    statuses = {v.status for v in flat}
    assert two_phase_pb2.PrepareResponse.ABORT in statuses
    assert two_phase_pb2.PrepareResponse.READY in statuses

    # trigger Abort RPC fan-out
    AbortReq = namedtuple("AbortReq", ["transaction_id"])
    coord.Abort(AbortReq("t"), context=None)
    assert coord.shard_stubs["x"].rolled
    assert coord.shard_stubs["y"].rolled

# --- Idempotence tests -----------------------------------------------------

def test_shard_idempotence_commit_and_abort():
    # off-chain only, no on-chain interactions happen
    shard = Shard("id", rpc_url="dummy", adapter_address="0x0")
    TxReq = namedtuple("TxReq", ["transaction_id"])
    PrepReq = namedtuple("PrepReq", ["transaction_id","operations","timeout_blocks"])

    # two commits in a row
    req = PrepReq("z", ["SET a 1"], 0)
    shard.Prepare(req, None)
    shard.Commit(TxReq("z"), None)
    state1 = dict(shard.state)
    shard.Commit(TxReq("z"), None)
    assert shard.state == state1

    # two aborts in a row
    req2 = PrepReq("z2", ["SET b 2"], 0)
    shard.Prepare(req2, None)
    shard.Abort(TxReq("z2"), None)
    p1 = dict(shard.prepared)
    shard.Abort(TxReq("z2"), None)
    assert shard.prepared == p1

def test_coordinator_idempotence_commit_and_abort():
    class Stub:
        def __init__(self): self.commits = 0; self.rolls = 0
        def Prepare(self, req, *a,**kw):
            return [two_phase_pb2.PrepareResponse(status=two_phase_pb2.PrepareResponse.READY,
                                                 shard_id="s")]
        def Commit(self, req, *a,**kw): self.commits += 1
        def Rollback(self, req, *a,**kw): self.rolls   += 1

    adapter_cfg = {"s":"0x0"}
    coord = Coordinator({"s":"p"}, {"s":"u"}, adapter_cfg, default_timeout_blocks=0)
    coord.shard_stubs = {"s": Stub()}

    PrepReq = namedtuple("PrepReq",
                         ["transaction_id","operations","timeout_blocks",
                          "onchain_recipient","onchain_amount"])
    req = PrepReq("x", [], 0, "0x0", 0)
    _ = list(coord.Prepare(req, context=None))

    CommitReq = namedtuple("CommitReq", ["transaction_id"])
    coord.Commit(CommitReq("x"), None)
    coord.Commit(CommitReq("x"), None)
    assert coord.shard_stubs["s"].commits == 2

    AbortReq = namedtuple("AbortReq", ["transaction_id"])
    coord.Abort(AbortReq("x"), None)
    coord.Abort(AbortReq("x"), None)
    assert coord.shard_stubs["s"].rolls == 2
