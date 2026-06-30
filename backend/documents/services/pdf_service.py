import os
import fitz

from django.conf import settings
from django.core.files import File


def generer_pdf_signe(document, signature=None):
    if not document.fichier_original:
        raise ValueError("Aucun fichier original trouvé.")

    signatures = document.signatures.filter(
        statut='SIGNE',
        image_signature__isnull=False,
    ).exclude(image_signature='').order_by('date_signature')

    if not signatures.exists():
        raise ValueError("Aucune signature validée trouvée.")

    original_path = document.fichier_original.path

    output_dir = os.path.join(settings.MEDIA_ROOT, "documents", "signes")
    os.makedirs(output_dir, exist_ok=True)

    output_filename = f"document_signe_{document.id}.pdf"
    output_path = os.path.join(output_dir, output_filename)

    pdf = fitz.open(original_path)
    page = pdf[0]

    for sig in signatures:
        signature_path = sig.image_signature.path

        x = float(sig.position_x)
        y = float(sig.position_y)
        largeur = float(sig.largeur)
        hauteur = float(sig.hauteur)

        rect = fitz.Rect(
            x,
            y,
            x + largeur,
            y + hauteur
        )

        page.insert_image(
            rect,
            filename=signature_path,
            keep_proportion=True
        )

    pdf.save(output_path)
    pdf.close()

    with open(output_path, "rb") as f:
        document.fichier_signe.save(
            output_filename,
            File(f),
            save=False
        )

    document.save()

    return document
