from typing import Dict
from .lightclient import LightClient

class TimeoutManager:
    # manages per-transaction deadlines based on on-chain block heights
    def __init__(self, client: LightClient):
        self.client = client
        self.deadlines: Dict[str, int] = {}

    def start(self, tx_id: str, timeout_blocks: int):
        # starts a timeout for a transaction: deadline = current_height + timeout_blocks
        current_height = self.client.get_block_height()
        self.deadlines[tx_id] = current_height + timeout_blocks
        print(f"[TimeoutManager] TX {tx_id} deadline set at block {self.deadlines[tx_id]}")

    def is_expired(self, tx_id: str) -> bool:
        # checks if the current block height has passed the deadline
        if tx_id not in self.deadlines:
            raise KeyError(f"No deadline found for TX {tx_id}")
        return self.client.get_block_height() > self.deadlines[tx_id]