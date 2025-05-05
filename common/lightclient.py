from web3 import Web3

class LightClient:
    # minimal Ethereum light client wrapper to fetch block heights
    def __init__(self, rpc_url: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Unable to connect to RPC at {rpc_url}")

    def get_block_height(self) -> int:
        # returns the latest block number on the chain
        return self.w3.eth.block_number