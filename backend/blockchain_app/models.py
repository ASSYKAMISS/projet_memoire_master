from django.db import models
from documents.models import Document


class AuditBlockchain(models.Model):
    STATUT_CHOICES = [
        ('ENREGISTRE', 'Enregistré'),
        ('ECHEC', 'Échec'),
    ]

    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='audit_blockchain'
    )

    hash_document = models.CharField(max_length=64)
    signataire_pseudonyme = models.CharField(max_length=255)

    transaction_hash = models.CharField(max_length=255, blank=True)
    adresse_contrat = models.CharField(max_length=255, blank=True)

    block_number = models.BigIntegerField(null=True, blank=True)
    timestamp_blockchain = models.DateTimeField(null=True, blank=True)

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='ENREGISTRE'
    )

    date_enregistrement = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Audit blockchain - {self.document.titre}"
