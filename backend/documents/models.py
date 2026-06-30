from django.db import models
from django.contrib.auth.models import User
from accounts.models import Departement


class Document(models.Model):
    STATUT_CHOICES = [
        ('BROUILLON', 'Brouillon'),
        ('EN_ATTENTE_SIGNATURE', 'En attente de signature'),
        ('SIGNE', 'Signé'),
        ('VERIFIE', 'Vérifié'),
        ('INVALIDE', 'Invalide'),
    ]

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    titre = models.CharField(max_length=255)
    fichier_original = models.FileField(upload_to='documents/originaux/')
    fichier_signe = models.FileField(
        upload_to='documents/signes/',
        null=True,
        blank=True
    )
    hash_original = models.CharField(max_length=64, blank=True)
    hash_signe = models.CharField(max_length=64, blank=True)
    statut = models.CharField(
        max_length=30,
        choices=STATUT_CHOICES,
        default='BROUILLON'
    )
    date_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titre


class AccesDocument(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='acces'
    )

    agent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='documents_autorises'
    )

    departement = models.ForeignKey(
        Departement,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='documents_autorises'
    )

    peut_signer = models.BooleanField(default=True)
    date_attribution = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Accès document"
        verbose_name_plural = "Accès documents"

    def __str__(self):
        if self.agent:
            cible = self.agent.username
        elif self.departement:
            cible = self.departement.nom
        else:
            cible = "Aucune cible"

        return f"{self.document.titre} -> {cible}"


class Verification(models.Model):
    RESULTAT_CHOICES = [
        ('VALIDE', 'Valide'),
        ('INVALIDE', 'Invalide'),
        ('ERREUR', 'Erreur'),
    ]

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='verifications'
    )
    hash_verifie = models.CharField(max_length=64)
    hash_recalcule = models.CharField(max_length=64, blank=True)
    resultat = models.CharField(max_length=20, choices=RESULTAT_CHOICES)
    message = models.TextField()
    date_verification = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.titre} - {self.resultat}"


class PaquetPreuve(models.Model):
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='paquet_preuve'
    )
    fichier_preuve = models.FileField(upload_to='preuves/')
    date_generation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Preuve - {self.document.titre}"


class HistoriqueOperation(models.Model):
    ACTION_CHOICES = [
        ('UPLOAD', 'Téléversement'),
        ('ACCESS_ASSIGNMENT', 'Attribution des accès'),
        ('SIGNATURE', 'Signature'),
        ('VERIFICATION', 'Vérification'),
        ('BLOCKCHAIN_RECORD', 'Enregistrement blockchain'),
        ('AI_ANALYSIS', 'Analyse IA'),
        ('PROOF_GENERATION', 'Génération paquet de preuve'),
        ('DOWNLOAD_SIGNED', 'Téléchargement document signé'),
        ('DOWNLOAD_PROOF', 'Téléchargement paquet de preuve'),
    ]

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historiques'
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='historiques'
    )
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    details = models.TextField(blank=True)
    date_action = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} - {self.document.titre}"