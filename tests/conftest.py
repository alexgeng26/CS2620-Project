# tests/conftest.py
import os, sys
# add project root (one level up from tests/) to Python import search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import common.lightclient as lc

# --- stub out Web3 / LightClient so no real RPCs happen in unit tests ---

class DummyW3:
    class Eth:
        def __init__(self):
            self.chain_id = 1337
            self.default_account = None
        def account_from_key(self, k):
            return type("A", (), {"address": "0x0000000000000000000000000000000000000000"})()
        def get_transaction_count(self, addr):
            return 0
        def send_raw_transaction(self, tx):
            return b"\x00"*32
        def wait_for_transaction_receipt(self, h):
            return type("R", (), {"transactionHash": b"\x00"*32})()

    def __init__(self):
        self.eth = self.Eth()
    def is_connected(self):
        return True

class DummyLightClient:
    def __init__(self, rpc_url=""):
        self._height = 100
        self.w3 = DummyW3()
    def get_block_height(self):
        return self._height
    def is_connected(self):
        return True

@pytest.fixture(autouse=True)
def patch_lightclient(monkeypatch):
    # everywhere that does `from common.lightclient import LightClient` now gets DummyLightClient
    monkeypatch.setattr(lc, "LightClient", DummyLightClient)
