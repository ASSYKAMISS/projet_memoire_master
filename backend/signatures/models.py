from django.db import models
from django.contrib.auth.models import User
from documents.models import Document


class Signature(models.Model):

    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('SIGNE', 'Signé'),
        ('INVALIDE', 'Invalide'),
    ]

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='signatures'
    )

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='signatures'
    )

    # Signature manuscrite
    image_signature = models.ImageField(
        upload_to='signatures/manuscrites/',
        null=True,
        blank=True
    )

    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)
    largeur = models.FloatField(default=150)
    hauteur = models.FloatField(default=80)

    # Signature numérique
    signature_numerique = models.TextField(blank=True)
    cle_publique = models.TextField(blank=True)

    date_signature = models.DateTimeField(auto_now_add=True)

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='EN_ATTENTE'
    )

    def __str__(self):
        return f"{self.utilisateur.username} - {self.document.titre}"