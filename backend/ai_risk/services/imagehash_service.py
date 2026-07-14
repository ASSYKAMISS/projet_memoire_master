from PIL import Image
import imagehash

from signatures.models import Signature


def normaliser_signature(image_path):
    image = Image.open(image_path).convert("RGBA")

    fond = Image.new("RGBA", image.size, "WHITE")
    fond.alpha_composite(image)

    image_gris = fond.convert("L")
    pixels = image_gris.load()
    largeur, hauteur = image_gris.size

    seuil_blanc = 245
    x_min = largeur
    y_min = hauteur
    x_max = 0
    y_max = 0

    for y in range(hauteur):
        for x in range(largeur):
            if pixels[x, y] < seuil_blanc:
                x_min = min(x_min, x)
                y_min = min(y_min, y)
                x_max = max(x_max, x)
                y_max = max(y_max, y)

    if x_min > x_max or y_min > y_max:
        return image_gris.resize((256, 128))

    marge = 12
    x_min = max(x_min - marge, 0)
    y_min = max(y_min - marge, 0)
    x_max = min(x_max + marge, largeur)
    y_max = min(y_max + marge, hauteur)

    signature_recadree = image_gris.crop((x_min, y_min, x_max, y_max))

    canevas = Image.new("L", (256, 128), "WHITE")
    signature_recadree.thumbnail((236, 108), Image.Resampling.LANCZOS)

    x = (256 - signature_recadree.width) // 2
    y = (128 - signature_recadree.height) // 2
    canevas.paste(signature_recadree, (x, y))

    return canevas


def calculer_hash_signature(image_path):
    image = normaliser_signature(image_path)
    return imagehash.phash(image)


def distance_entre_images(image_path_1, image_path_2):
    hash_1 = calculer_hash_signature(image_path_1)
    hash_2 = calculer_hash_signature(image_path_2)

    return hash_1 - hash_2


def anciennes_signatures_utilisateur(signature):
    return Signature.objects.filter(
        utilisateur=signature.utilisateur,
        statut="SIGNE",
        image_signature__isnull=False
    ).exclude(
        id=signature.id
    ).exclude(
        image_signature=""
    )


def analyser_signature_imagehash(signature):
    if not signature.image_signature:
        return {
            "image_hash": "",
            "distance_min": None,
            "distance_moyenne": None,
            "niveau": "REFERENCE",
            "anomalie": False,
            "explication": "Aucune image de signature disponible."
        }

    image_hash = calculer_hash_signature(signature.image_signature.path)
    anciennes = anciennes_signatures_utilisateur(signature)

    if not anciennes.exists():
        return {
            "image_hash": str(image_hash),
            "distance_min": None,
            "distance_moyenne": None,
            "niveau": "REFERENCE",
            "anomalie": False,
            "explication": "Première signature enregistrée pour cet utilisateur."
        }

    distances = []

    for ancienne in anciennes:
        try:
            distance = distance_entre_images(
                signature.image_signature.path,
                ancienne.image_signature.path
            )
            distances.append(distance)
        except Exception:
            continue

    if not distances:
        return {
            "image_hash": str(image_hash),
            "distance_min": None,
            "distance_moyenne": None,
            "niveau": "REFERENCE",
            "anomalie": False,
            "explication": "Impossible de comparer avec les anciennes signatures."
        }

    distance_min = min(distances)
    distance_moyenne = sum(distances) / len(distances)
    source = signature.source_signature

    if distance_moyenne > 22:
        niveau = "ELEVE"
        anomalie = True
        explication = "La signature est très différente des anciennes signatures de l'utilisateur."
    elif distance_moyenne > 12:
        niveau = "MOYEN"
        anomalie = True
        explication = "La signature présente une différence moyenne avec les anciennes signatures."
    elif distance_min <= 2 and source == "DRAW":
        niveau = "SUSPECT"
        anomalie = True
        explication = "La signature dessinée est presque identique à une ancienne signature, ce qui est inhabituel."
    elif distance_min <= 2 and source == "UPLOAD":
        niveau = "FAIBLE"
        anomalie = False
        explication = "La signature importée est très proche d'une ancienne signature, ce qui peut être normal."
    else:
        niveau = "FAIBLE"
        anomalie = False
        explication = "La signature est cohérente avec les anciennes signatures de l'utilisateur."

    return {
        "image_hash": str(image_hash),
        "distance_min": distance_min,
        "distance_moyenne": distance_moyenne,
        "niveau": niveau,
        "anomalie": anomalie,
        "explication": explication
    }
