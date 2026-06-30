from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import AuditBlockchain
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from web3 import Web3
from django.conf import settings
import json
from pathlib import Path

from documents.services.hash_service import calculer_sha256


def is_responsable(user):
    return hasattr(user, 'profil') and user.profil.role == 'RESPONSABLE'


@login_required
def blockchain_audit(request):
    if request.user.is_superuser:
        audits = AuditBlockchain.objects.all()

    elif is_responsable(request.user):
        audits = AuditBlockchain.objects.filter(
            document__utilisateur=request.user
        )

    else:
        audits = AuditBlockchain.objects.filter(
            document__signatures__utilisateur=request.user
        ).distinct()

    audits = audits.select_related(
        'document',
        'document__utilisateur'
    ).order_by('-date_enregistrement')

    total_audits = audits.count()
    total_enregistres = audits.filter(statut='ENREGISTRE').count()
    total_echecs = audits.filter(statut='ECHEC').count()

    return render(
        request,
        'blockchain/blockchain_audit.html',
        {
            'audits': audits,
            'total_audits': total_audits,
            'total_enregistres': total_enregistres,
            'total_echecs': total_echecs,
            'active_page': 'blockchain',
        }
    )


@login_required
def verify_blockchain_audit(request, audit_id):
    audit = get_object_or_404(AuditBlockchain, id=audit_id)

    if not request.user.is_superuser:
        if is_responsable(request.user):
            if audit.document.utilisateur != request.user:
                messages.error(request, "Vous n'avez pas accès à cet audit.")
                return redirect('blockchain_audit')
        else:
            is_signer = audit.document.signatures.filter(
                utilisateur=request.user
            ).exists()

            if not is_signer:
                messages.error(request, "Vous n'avez pas accès à cet audit.")
                return redirect('blockchain_audit')

    try:
        web3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_RPC_URL))

        if not web3.is_connected():
            messages.error(request, "Node blockchain inaccessible.")
            return redirect('blockchain_audit')

        artifact_path = Path(settings.BLOCKCHAIN_CONTRACT_ABI_PATH)

        with artifact_path.open('r', encoding='utf-8') as artifact_file:
            artifact = json.load(artifact_file)

        contract = web3.eth.contract(
            address=Web3.to_checksum_address(settings.BLOCKCHAIN_CONTRACT_ADDRESS),
            abi=artifact['abi'],
        )

        proof = contract.functions.getProof(audit.document.id).call()

        blockchain_hash = proof[1]

        if blockchain_hash == audit.hash_document and blockchain_hash == audit.document.hash_signe:
            messages.success(
                request,
                "Preuve blockchain valide : le hash correspond au document signé."
            )
        else:
            messages.error(
                request,
                "Preuve blockchain invalide : le hash ne correspond pas."
            )

    except Exception as exc:
        messages.error(
            request,
            f"Erreur de vérification blockchain : {exc}"
        )

    return redirect('blockchain_audit')

