from django.db import models
from django.contrib.auth.models import User


class Organisation(models.Model):
    nom = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    telephone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom


class Departement(models.Model):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="departements"
    )

    nom = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="departements_responsable"
    )

    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organisation", "nom")

    def __str__(self):
        if self.organisation:
            return f"{self.nom} - {self.organisation.nom}"
        return self.nom


class ProfilUtilisateur(models.Model):
    ROLE_CHOICES = [
        ("ADMIN_ORGANISATION", "Admin organisation"),
        ("RESPONSABLE_DEPARTEMENT", "Responsable département"),
        ("RESPONSABLE", "Responsable"),
        ("AGENT", "Agent"),
    ]

    utilisateur = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profil"
    )

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="utilisateurs"
    )

    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default="AGENT"
    )

    departement = models.ForeignKey(
        Departement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agents"
    )

    poste = models.CharField(max_length=150, blank=True)
    matricule = models.CharField(max_length=100, blank=True)
    telephone = models.CharField(max_length=30, blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    date_naissance = models.DateField(null=True, blank=True)

    doit_changer_mot_de_passe = models.BooleanField(default=True)

    cree_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="utilisateurs_crees"
    )

    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.utilisateur.username} - {self.role}"