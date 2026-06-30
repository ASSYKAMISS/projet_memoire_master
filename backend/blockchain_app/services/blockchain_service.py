import json
from datetime import datetime, timezone as dt_timezone
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from web3 import Web3

from blockchain_app.models import AuditBlockchain


def _create_failed_audit(document, signature, message=""):
    audit, _ = AuditBlockchain.objects.update_or_create(
        document=document,
        defaults={
            'hash_document': document.hash_signe or '',
            'signataire_pseudonyme': signature.utilisateur.username,
            'transaction_hash': message[:255],
            'adresse_contrat': getattr(settings, 'BLOCKCHAIN_CONTRACT_ADDRESS', ''),
            'block_number': None,
            'timestamp_blockchain': timezone.now(),
            'statut': 'ECHEC',
        }
    )

    return audit


def _load_contract_abi():
    artifact_path = Path(settings.BLOCKCHAIN_CONTRACT_ABI_PATH)

    with artifact_path.open('r', encoding='utf-8') as artifact_file:
        artifact = json.load(artifact_file)

    return artifact['abi']


def enregistrer_audit_blockchain(document, signature):
    if not document.hash_signe:
        return _create_failed_audit(
            document,
            signature,
            'hash_signe manquant'
        )

    contract_address = getattr(settings, 'BLOCKCHAIN_CONTRACT_ADDRESS', '')

    if not contract_address:
        return _create_failed_audit(
            document,
            signature,
            'adresse contrat manquante'
        )

    try:
        web3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_RPC_URL))

        if not web3.is_connected():
            return _create_failed_audit(
                document,
                signature,
                'node blockchain inaccessible'
            )

        contract = web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=_load_contract_abi(),
        )

        function_call = contract.functions.registerProof(
            int(document.id),
            document.hash_signe,
            signature.signature_numerique,
            signature.cle_publique,
            signature.utilisateur.username,
        )

        private_key = getattr(settings, 'BLOCKCHAIN_PRIVATE_KEY', '')

        if private_key:
            account = web3.eth.account.from_key(private_key)

            transaction = function_call.build_transaction({
                'from': account.address,
                'nonce': web3.eth.get_transaction_count(account.address),
                'gas': 2_000_000,
                'gasPrice': web3.eth.gas_price,
                'chainId': web3.eth.chain_id,
            })

            signed_transaction = account.sign_transaction(transaction)

            tx_hash = web3.eth.send_raw_transaction(
                signed_transaction.raw_transaction
            )

        else:
            account = getattr(settings, 'BLOCKCHAIN_ACCOUNT_ADDRESS', '')

            if not account:
                accounts = web3.eth.accounts

                if not accounts:
                    return _create_failed_audit(
                        document,
                        signature,
                        'aucun compte blockchain disponible'
                    )

                account = accounts[0]

            tx_hash = function_call.transact({
                'from': account
            })

        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        block = web3.eth.get_block(receipt.blockNumber)

        block_timestamp = datetime.fromtimestamp(
            block.timestamp,
            tz=dt_timezone.utc
        )

        audit, _ = AuditBlockchain.objects.update_or_create(
            document=document,
            defaults={
                'hash_document': document.hash_signe,
                'signataire_pseudonyme': signature.utilisateur.username,
                'transaction_hash': receipt.transactionHash.hex(),
                'adresse_contrat': contract_address,
                'block_number': receipt.blockNumber,
                'timestamp_blockchain': block_timestamp,
                'statut': 'ENREGISTRE',
            }
        )

        return audit

    except Exception as exc:
        return _create_failed_audit(
            document,
            signature,
            str(exc)
        )