from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import AuditBlockchain
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from web3 import Web3
from django.conf import settings
from django.db.models import Q
import json
from pathlib import Path

from documents.services.hash_service import calculer_sha256


ROLE_ADMIN_ORG = 'ADMIN_ORGANISATION'
ROLE_RESPONSABLE_DEPT = 'RESPONSABLE_DEPARTEMENT'
ROLE_RESPONSABLE_LEGACY = 'RESPONSABLE'
RESPONSABLE_ROLES = [ROLE_RESPONSABLE_DEPT, ROLE_RESPONSABLE_LEGACY]


def user_profile(user):
    return getattr(user, 'profil', None)


def audits_accessibles_queryset(user):
    audits = AuditBlockchain.objects.all()

    if user.is_superuser:
        return audits

    profil = user_profile(user)
    if profil is None:
        return audits.none()

    if profil.role == ROLE_ADMIN_ORG:
        return audits.filter(
            Q(document__utilisateur__profil__organisation=profil.organisation)
            | Q(document__signatures__utilisateur__profil__organisation=profil.organisation)
        ).distinct()

    if profil.role in RESPONSABLE_ROLES:
        return audits.filter(
            Q(document__utilisateur=user)
            | Q(document__signatures__utilisateur=user)
            | Q(document__utilisateur__profil__departement=profil.departement)
            | Q(document__signatures__utilisateur__profil__departement=profil.departement)
        ).distinct()

    return audits.filter(
        Q(document__utilisateur=user)
        | Q(document__signatures__utilisateur=user)
    ).distinct()


@login_required
def blockchain_audit(request):
    audits = audits_accessibles_queryset(request.user)

    audits = audits.select_related(
        'document',
        'document__utilisateur',
        'document__utilisateur__profil',
        'document__utilisateur__profil__organisation',
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
    audit = get_object_or_404(audits_accessibles_queryset(request.user), id=audit_id)

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

