from django.db import models
from django.conf import settings
from signatures.models import Signature


class AnalyseSignatureIA(models.Model):
    NIVEAU_CHOICES = [
        ("REFERENCE", "Référence"),
        ("FAIBLE", "Faible"),
        ("MOYEN", "Moyen"),
        ("ELEVE", "Élevé"),
        ("SUSPECT", "Suspect"),
    ]

    SOURCE_CHOICES = [
        ("DRAW", "Signature dessinée"),
        ("UPLOAD", "Signature importée"),
    ]

    signature = models.OneToOneField(
        Signature,
        on_delete=models.CASCADE,
        related_name="analyse_ia"
    )

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="analyses_signature_ia"
    )

    source_signature = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        blank=True
    )

    image_hash = models.CharField(max_length=100, blank=True)

    distance_min = models.FloatField(null=True, blank=True)
    distance_moyenne = models.FloatField(null=True, blank=True)

    niveau_risque = models.CharField(
        max_length=20,
        choices=NIVEAU_CHOICES,
        default="REFERENCE"
    )

    anomalie_detectee = models.BooleanField(default=False)
    explication = models.TextField(blank=True)

    date_analyse = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analyse IA - {self.utilisateur} - {self.niveau_risque}"