from django.db import models
from django.contrib.auth.models import User


class Departement(models.Model):
    nom = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departements_responsable'
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom


class ProfilUtilisateur(models.Model):
    ROLE_CHOICES = [
        ('RESPONSABLE', 'Responsable'),
        ('AGENT', 'Agent'),
    ]

    utilisateur = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profil'
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='AGENT'
    )

    departement = models.ForeignKey(
        Departement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents'
    )

    cree_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='utilisateurs_crees'
    )

    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.utilisateur.username} - {self.role}"

    