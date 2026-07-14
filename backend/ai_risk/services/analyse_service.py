from ai_risk.models import AnalyseSignatureIA
from ai_risk.services.imagehash_service import analyser_signature_imagehash


def analyser_signature(signature):
    resultat = analyser_signature_imagehash(signature)

    analyse, created = AnalyseSignatureIA.objects.update_or_create(
        signature=signature,
        defaults={
            "utilisateur": signature.utilisateur,
            "source_signature": signature.source_signature,
            "image_hash": resultat["image_hash"],
            "distance_min": resultat["distance_min"],
            "distance_moyenne": resultat["distance_moyenne"],
            "niveau_risque": resultat["niveau"],
            "anomalie_detectee": resultat["anomalie"],
            "explication": resultat["explication"],
        }
    )

    return analyse
