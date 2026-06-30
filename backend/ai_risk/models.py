from django.db import models
from documents.models import Document


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