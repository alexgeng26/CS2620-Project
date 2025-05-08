// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title TwoPhaseAdapter
/// @notice On‐chain adapter for 2PC with block‐height timeouts.
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

    event Locked   (bytes32 indexed txId, address indexed sender, address indexed recipient, uint256 amount, uint256 deadline);
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
