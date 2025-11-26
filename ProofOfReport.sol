// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ProofOfReport {
    struct Report {
        address owner;
        uint256 timestamp;
    }

    mapping(bytes32 => Report) private reports;
    mapping(bytes32 => string) private cidByHash; // CID do relatório (IPFS)

    event ReportRegistered(bytes32 indexed hash, address indexed owner, uint256 timestamp);
    event ReportRegisteredWithCID(bytes32 indexed hash, address indexed owner, string cid, uint256 timestamp);

    function registerReport(bytes32 hash) external {
        require(reports[hash].timestamp == 0, "Hash ja registrado");
        reports[hash] = Report(msg.sender, block.timestamp);
        emit ReportRegistered(hash, msg.sender, block.timestamp);
    }

    function registerReportWithCID(bytes32 hash, string calldata cid) external {
        require(reports[hash].timestamp == 0, "Hash ja registrado");
        reports[hash] = Report(msg.sender, block.timestamp);
        cidByHash[hash] = cid;
        emit ReportRegisteredWithCID(hash, msg.sender, cid, block.timestamp);
    }

    function verifyReport(bytes32 hash) external view returns (bool exists, address owner, uint256 timestamp) {
        Report memory r = reports[hash];
        return (r.timestamp != 0, r.owner, r.timestamp);
    }

    function getCID(bytes32 hash) external view returns (string memory) {
        return cidByHash[hash];
    }
}
