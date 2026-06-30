import hashlib


def calculer_sha256(fichier):
    """
    Calcule le SHA-256 d'un fichier Django FileField.
    """

    sha256 = hashlib.sha256()

    fichier.open("rb")

    for chunk in fichier.chunks():
        sha256.update(chunk)

    fichier.close()

    return sha256.hexdigest()


def calculer_hash_document_signe(document):
    """
    Calcule et enregistre le hash SHA-256
    du document signé.
    """

    if not document.fichier_signe:
        raise ValueError("Aucun document signé trouvé.")

    document.hash_signe = calculer_sha256(document.fichier_signe)
    document.save()

    return document.hash_signe