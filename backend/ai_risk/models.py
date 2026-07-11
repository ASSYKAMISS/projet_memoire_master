from django.db import models
from documents.models import Document
from django.conf import settings
from signatures.models import Signature


class ScoreRisqueIA(models.Model):

    NIVEAU_CHOICES = [
        ('FAIBLE', 'Faible'),
        ('MOYEN', 'Moyen'),
        ('ELEVE', 'Élevé'),
    ]

    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='score_risque'
    )

    score = models.FloatField(default=0)

    niveau = models.CharField(
        max_length=20,
        choices=NIVEAU_CHOICES,
        default='FAIBLE'
    )

    anomalie_detectee = models.BooleanField(default=False)

    explication = models.TextField(blank=True)

    date_calcul = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Score IA - {self.document.titre}"
    
                                        

    TYPE_ANOMALIE_CHOICES = [
        ("AUCUNE", "Aucune anomalie"),
        ("SIGNATURE_TROP_SIMPLE", "Signature trop simple"),
        ("SIGNATURE_DIFFERENTE_HABITUDE", "Signature différente des habitudes"),
        ("SIGNATURE_SIMILAIRE_AUTRE_AGENT", "Signature similaire à un autre agent"),
        ("POSITION_INHABITUELLE", "Position inhabituelle"),
        ("TAILLE_INHABITUELLE", "Taille inhabituelle"),
        ("VALIDATION_TROP_RAPIDE", "Validation trop rapide"),
        ("ANOMALIE_GLOBALE", "Anomalie globale"),
    ]

    signature = models.OneToOneField(
        Signature,
        on_delete=models.CASCADE,
        related_name="analyse_fraude",
    )

    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="analyses_fraude_signature",
    )

    score_fraude = models.PositiveIntegerField(default=0)

    niveau_risque = models.CharField(
        max_length=20,
        choices=NIVEAU_RISQUE_CHOICES,
        default="FAIBLE",
    )

    anomalie_detectee = models.BooleanField(default=False)

    type_anomalie = models.CharField(
        max_length=50,
        choices=TYPE_ANOMALIE_CHOICES,
        default="AUCUNE",
    )

    explication = models.TextField(blank=True)

    image_hash = models.CharField(max_length=100, blank=True)

    date_analyse = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analyse IA - {self.agent} - {self.niveau_risque}"