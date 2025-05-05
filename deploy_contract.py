# Updated deploy_contract.py with solc install check

from dotenv import load_dotenv
load_dotenv()  # loads ALCHEMY_RPC_URL and PRIVATE_KEY from .env

from web3 import Web3
import solcx
import os

# 0. Ensure solc 0.8.0 is available
try:
    solcx.set_solc_version('0.8.0')
except solcx.exceptions.SolcNotInstalled:
    print("Solc 0.8.0 not found, installing...")
    solcx.install_solc('0.8.0')
    solcx.set_solc_version('0.8.0')

# 1. Compile the Solidity contract
compiled = solcx.compile_standard({
    "language": "Solidity",
    "sources": {
        "TwoPhaseAdapter.sol": {
            "content": '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TwoPhaseAdapter {
    enum Status { None, Pending, Committed, Aborted }
    struct TxData {
        address sender;
        address recipient;
        uint256 amount;
        uint256 deadline;
        Status  status;
    }
    mapping(bytes32 => TxData) public transactions;
    event Locked(bytes32 indexed txId, address indexed sender, address indexed recipient, uint256 amount, uint256 deadline);
    event Committed(bytes32 indexed txId);
    event Reclaimed(bytes32 indexed txId);

    function lockFunds(bytes32 txId, address recipient, uint256 deadline) external payable {
        require(transactions[txId].status == Status.None, "TX exists");
        require(msg.value > 0, "Must lock >0");
        require(deadline > block.number, "Deadline in past");
        transactions[txId] = TxData(msg.sender, recipient, msg.value, deadline, Status.Pending);
        emit Locked(txId, msg.sender, recipient, msg.value, deadline);
    }

    function commit(bytes32 txId) external {
        TxData storage t = transactions[txId];
        require(t.status == Status.Pending, "Not pending");
        require(block.number <= t.deadline, "Past deadline");
        t.status = Status.Committed;
        payable(t.recipient).transfer(t.amount);
        emit Committed(txId);
    }

    function reclaim(bytes32 txId) external {
        TxData storage t = transactions[txId];
        require(t.status == Status.Pending, "Not pending");
        require(block.number > t.deadline, "Too early");
        t.status = Status.Aborted;
        payable(t.sender).transfer(t.amount);
        emit Reclaimed(txId);
    }
}
'''
        }
    },
    "settings": {
        "outputSelection": {
            "*": { "*": ["abi", "evm.bytecode.object"] }
        }
    }
})

# Extract ABI and bytecode
contract_data = compiled["contracts"]["TwoPhaseAdapter.sol"]["TwoPhaseAdapter"]
abi = contract_data["abi"]
bytecode = contract_data["evm"]["bytecode"]["object"]

# 2. Read environment variables
alchemy_url = os.getenv("ALCHEMY_RPC_URL")
private_key = os.getenv("PRIVATE_KEY")
if not alchemy_url or not private_key:
    raise EnvironmentError("Please set ALCHEMY_RPC_URL and PRIVATE_KEY in .env")

# 3. Connect to your RPC
w3 = Web3(Web3.HTTPProvider(alchemy_url))
if not w3.is_connected:
    raise ConnectionError("Cannot connect to RPC at " + alchemy_url)

# 4. Build, sign & send the deployment transaction
account = w3.eth.account.from_key(private_key)
nonce = w3.eth.get_transaction_count(account.address)

Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

estimated = Contract.constructor().estimate_gas({
    "from": account.address
})
print("Estimated gas for deployment:", estimated)

txn = Contract.constructor().build_transaction({
    "from": account.address,
    "nonce": nonce,
    "chainId": w3.eth.chain_id,
    "gas": 1_000_000,
    "maxFeePerGas": w3.to_wei("100", "gwei"),
    "maxPriorityFeePerGas": w3.to_wei("2", "gwei"),
})

signed = w3.eth.account.sign_transaction(txn, private_key)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print("Deploy TX hash:", tx_hash.hex())

receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
print("Contract deployed at address:", receipt.contractAddress)

cost_wei = receipt.gasUsed * txn["maxFeePerGas"]
print("Actual gasUsed:", receipt.gasUsed)
print("Actual cost  :", w3.from_wei(cost_wei, "ether"), "ETH")