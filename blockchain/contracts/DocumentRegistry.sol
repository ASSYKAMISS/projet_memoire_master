// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract DocumentRegistry {
    struct Proof {
        uint256 documentId;
        string hashDocument;
        string signatureNumerique;
        string clePublique;
        string signataire;
        uint256 timestamp;
        bool exists;
    }

    mapping(uint256 => Proof) private proofs;

    event ProofRegistered(
        uint256 indexed documentId,
        string hashDocument,
        string signataire,
        uint256 timestamp
    );

    function registerProof(
        uint256 documentId,
        string memory hashDocument,
        string memory signatureNumerique,
        string memory clePublique,
        string memory signataire
    ) public {
        require(documentId > 0, "DocumentRegistry: invalid document id");
        require(bytes(hashDocument).length > 0, "DocumentRegistry: empty hash");
        require(!proofs[documentId].exists, "DocumentRegistry: proof already exists");

        proofs[documentId] = Proof({
            documentId: documentId,
            hashDocument: hashDocument,
            signatureNumerique: signatureNumerique,
            clePublique: clePublique,
            signataire: signataire,
            timestamp: block.timestamp,
            exists: true
        });

        emit ProofRegistered(
            documentId,
            hashDocument,
            signataire,
            block.timestamp
        );
    }

    function getProof(uint256 documentId) public view returns (Proof memory) {
        require(proofs[documentId].exists, "DocumentRegistry: proof not found");
        return proofs[documentId];
    }

    function proofExists(uint256 documentId) public view returns (bool) {
        return proofs[documentId].exists;
    }
}