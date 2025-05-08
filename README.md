# Distributed Two-Phase-Commit (2PC) with Blockchain Timeouts and On-Chain Adapters

This repository implements a proof-of-concept distributed two-phase-commit (2PC) protocol over gRPC, enhanced with blockchain-native block-height timeouts and on-chain adapters for atomic cross-shard fund locking and commit/abort semantics.

## Features

* **Phase A (Classic 2PC)**

  * Coordinator and Shard services communicate over gRPC.
  * `Prepare`, `Commit`, `Abort`/`Rollback` RPCs coordinate in-memory state changes across shards.
  * Extensible protocol defined in `mcp2pc/two_phase.proto`.

* **Block-Height Timeouts**

  * Each Prepare carries a `timeout_blocks` parameter.
  * `common/lightclient.py` wraps Web3 to fetch current block height.
  * `common/timeout_manager.py` tracks per-transaction deadlines in blocks.
  * Shards auto-abort if deadline passes before commit.

* **Phase B (On-Chain Adapters)**

  * Shard nodes call into smart-contract adapters to lock, commit, or reclaim funds.
  * EVM adapter example via `contracts/evm_adapter/TwoPhaseAdapter.sol` and Web3 interaction.

* **Client & Demo**

  * `client/client.py`: sample client driving a full end-to-end transaction.
  * Demo scripts illustrate commit, timeout-abort, reclaim flows.

* **Unit Tests**

  * `tests/test_unit.py` covers shard timeout, commit/abort logic and coordinator fan-out, error-handling, idempotence.
  * Mocks out LightClient and gRPC stubs for fast testing.

## Directory Structure

```
├── abi/                   # Contract ABIs and generated schemas
├── common/                # Shared utilities (lightclient, timeout_manager)
├── coordinator/           # Coordinator gRPC service and server
├── contracts/             # Smart-contract adapters (EVM, CosmWasm, Algorand)
├── client/                # Sample client invoking Coordinator
├── shard/                 # Shard gRPC service (shard_node.py)
├── config/                # Configuration (shard RPCs, adapter addresses)
├── scripts/               # Demo scripts (timeout_demo, reclaim_demo, etc.)
├── tests/                 # Pytest unit tests
├── mcp2pc/                # Protobuf definitions and generated code
├── .env.example           # Environment variable template
└── README.md              # <-- this file
```

## Getting Started

### Prerequisites

* Python 3.10+
* `pip install -r requirements.txt`
* `.env` file with:

  ```ini
  # Ethereum (Alchemy) RPC endpoints & PRIVATE_KEY for shards
  ALCHEMY_RPC_URL=0x...  
  SHARD1_KEY=...
  SHARD2_KEY=...
  SHARD3_KEY=...
  ```

* Private keys can be obtained by installing MetaMask in your browser, creating three separate accounts for shards and one for recipient, and exporting each respective private key. The recipient key can be substitued for the one in client/client.py and reclaim_demo.py. Do not share these private keys publicly.
* Balances can be viewed directly in MetaMask (ETH balance will adjust as demo runs: lockFunds deducts, commit finalizes, reclaim returns on timeout), and full transaction history can be found on Etherscan (Go to https://sepolia.etherscan.io. Click into any tx hash to see gas used, block number, and emitted events.).

### Install

```bash
git clone https://github.com/your-user/CS2620-Project.git
cd CS2620-Project
pip install -r requirements.txt
cp .env.example .env   # then edit .env
```

### Run the Services

1. **Start Shard nodes** (each in its own terminal):

   ```bash
   python -m shard.shard_node --id shard1 --port 50061
   python -m shard.shard_node --id shard2 --port 50062
   python -m shard.shard_node --id shard3 --port 50063
   ```

2. **Start Coordinator**:

   ```bash
   python -m coordinator.coordinator
   ```

3. **Run Client Demo**:

   ```bash
   python -m client.client
   ```

4. **Timeout / Abort Demo**:

    ```bash
    python timeout_demo.py
    ```

5. **Reclaim Demo**:

    ```bash
    python reclaim_demo.py
    ```

### Running Tests

```bash
pytest
```

## Extending Adapters

* **EVM**: Solidity adapter in `contracts/evm_adapter` (deploy with `deploy_contract.py`).

Add new adapter addresses to `config/adapters.json` under your chain key, and update `config/shard_rpcs.json` as needed.
