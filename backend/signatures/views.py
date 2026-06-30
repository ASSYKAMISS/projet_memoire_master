import base64
import uuid

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404, redirect, render

from blockchain_app.services.blockchain_service import enregistrer_audit_blockchain
from documents.models import Document
from documents.services.hash_service import calculer_hash_document_signe
from documents.services.pdf_service import generer_pdf_signe
from .models import Signature


@login_required
def sign_manual(request, document_id):
    document = get_object_or_404(Document, id=document_id)

    signature = get_object_or_404(
        Signature,
        document=document,
        utilisateur=request.user
    )

    if signature.statut == 'SIGNE':
        messages.info(request, "Vous avez déjà signé ce document.")
        return redirect('document_detail', document_id=document.id)

    if document.statut != 'EN_ATTENTE_SIGNATURE':
        messages.error(request, "Ce document n'est pas en attente de signature.")
        return redirect('documents_to_sign')

    if request.method == 'POST':
        signature_source = request.POST.get('signature_source')
        signature_data = request.POST.get('signature_data')

        pdf_scale = float(request.POST.get('pdf_scale', 1) or 1)
        position_x = float(request.POST.get('position_x', 0) or 0) / pdf_scale
        position_y = float(request.POST.get('position_y', 0) or 0) / pdf_scale
        largeur = float(request.POST.get('largeur', 180) or 180) / pdf_scale
        hauteur = float(request.POST.get('hauteur', 80) or 80) / pdf_scale

        signature.position_x = position_x
        signature.position_y = position_y
        signature.largeur = largeur
        signature.hauteur = hauteur

        if signature_source == 'draw' and signature_data:
            format_part, imgstr = signature_data.split(';base64,')
            ext = format_part.split('/')[-1]
            file_name = f"signature_{uuid.uuid4()}.{ext}"

            signature.image_signature.save(
                file_name,
                ContentFile(base64.b64decode(imgstr)),
                save=False
            )
        elif signature_source == 'upload':
            uploaded_signature = request.FILES.get('signature_file')

            if uploaded_signature:
                signature.image_signature = uploaded_signature
            elif not signature.image_signature:
                messages.error(request, "Veuillez importer une signature.")
                return redirect('sign_manual', document_id=document.id)
        else:
            messages.error(request, "Veuillez dessiner ou importer une signature.")
            return redirect('sign_manual', document_id=document.id)

        signature.statut = 'SIGNE'
        signature.save()

        generer_pdf_signe(document, signature)
        hash_signe = calculer_hash_document_signe(document)

        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()

        digital_signature = private_key.sign(
            hash_signe.encode('utf-8'),
            ec.ECDSA(hashes.SHA256())
        )

        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        signature.signature_numerique = base64.b64encode(digital_signature).decode('utf-8')
        signature.cle_publique = public_key_pem.decode('utf-8')
        signature.save()

        signatures_restantes = Signature.objects.filter(
            document=document,
            statut='EN_ATTENTE'
        ).count()

        if signatures_restantes == 0:
            document.statut = 'SIGNE'
            document.save()

            audit = enregistrer_audit_blockchain(document, signature)

            if audit.statut == 'ENREGISTRE':
                messages.success(
                    request,
                    "Document signé par tous les agents requis et enregistré sur la blockchain."
                )
            else:
                messages.warning(
                    request,
                    "Document signé par tous les agents requis, mais l'enregistrement blockchain a échoué."
                )
        else:
            document.statut = 'EN_ATTENTE_SIGNATURE'
            document.save()
            messages.success(
                request,
                f"Votre signature est enregistrée. Il reste {signatures_restantes} signature(s) attendue(s)."
            )

        return redirect('document_detail', document_id=document.id)

    return render(request, 'signatures/sign_manual.html', {
        'document': document,
        'signature': signature,
        'active_page': 'to_sign',
    })

