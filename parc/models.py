import random

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Livreur(models.Model):
    STATUT_CHOICES = [
        ("actif", "Actif"),
        ("inactif", "Inactif"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        related_name="profil_livreur",
        blank=True,
        null=True,
        help_text="Compte utilise par le livreur pour se connecter.",
    )
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=30)
    adresse = models.TextField(blank=True)
    cni = models.CharField("CNI", max_length=50, unique=True)
    numero_permis = models.CharField(max_length=50, blank=True)
    photo = models.ImageField(upload_to="livreurs/", blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="actif")

    class Meta:
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.prenom} {self.nom}"


class Moto(models.Model):
    ETAT_CHOICES = [
        ("disponible", "Disponible"),
        ("en_service", "En service"),
        ("maintenance", "Maintenance"),
        ("hors_service", "Hors service"),
    ]

    immatriculation = models.CharField(max_length=50, unique=True)
    marque = models.CharField(max_length=100)
    modele = models.CharField(max_length=100, blank=True)
    etat = models.CharField(max_length=20, choices=ETAT_CHOICES, default="disponible")

    class Meta:
        ordering = ["immatriculation"]

    def __str__(self):
        return self.immatriculation


class Affectation(models.Model):
    livreur = models.ForeignKey(Livreur, on_delete=models.CASCADE, related_name="affectations")
    moto = models.ForeignKey(Moto, on_delete=models.CASCADE, related_name="affectations")
    date_debut = models.DateTimeField(default=timezone.now)
    date_fin = models.DateTimeField(blank=True, null=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-date_debut"]

    def __str__(self):
        return f"{self.livreur} -> {self.moto}"


class Mission(models.Model):
    STATUT_CHOICES = [
        ("planifiee", "Planifiee"),
        ("en_cours", "En cours"),
        ("terminee", "Terminee"),
        ("annulee", "Annulee"),
    ]

    reference = models.CharField(max_length=50, unique=True, blank=True)
    client_nom = models.CharField(max_length=150, default="")
    client_telephone = models.CharField(max_length=30, default="")
    adresse_livraison = models.CharField(max_length=255, default="")
    description_lieu = models.TextField(blank=True)
    description_colis = models.TextField(blank=True)
    latitude_destination = models.FloatField(blank=True, null=True)
    longitude_destination = models.FloatField(blank=True, null=True)
    otp_code = models.CharField(max_length=6, blank=True)
    livreur = models.ForeignKey(Livreur, on_delete=models.PROTECT, related_name="missions")
    moto = models.ForeignKey(Moto, on_delete=models.PROTECT, related_name="missions")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="planifiee")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_depart = models.DateTimeField(blank=True, null=True)
    date_fin = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-date_creation"]

    def __str__(self):
        return f"{self.reference} - {self.client_nom}"

    def save(self, *args, **kwargs):
        # Reference lisible pour le responsable: MT-YYYYMMDD-0001.
        if not self.reference:
            today = timezone.localdate()
            prefix = f"MT-{today:%Y%m%d}"
            count = Mission.objects.filter(reference__startswith=prefix).count() + 1
            self.reference = f"{prefix}-{count:04d}"

        if not self.otp_code:
            self.otp_code = f"{random.randint(0, 999999):06d}"

        super().save(*args, **kwargs)


class PositionGPS(models.Model):
    moto = models.ForeignKey(Moto, on_delete=models.CASCADE, related_name="positions")
    latitude = models.FloatField()
    longitude = models.FloatField()
    vitesse = models.FloatField(default=0)
    date_heure = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date_heure"]
        indexes = [
            models.Index(fields=["moto", "-date_heure"]),
        ]

    def __str__(self):
        return f"{self.moto} ({self.latitude}, {self.longitude})"


class Alerte(models.Model):
    STATUT_CHOICES = [
        ("non_lue", "Non lue"),
        ("lue", "Lue"),
        ("traitee", "Traitee"),
    ]

    moto = models.ForeignKey(Moto, on_delete=models.CASCADE, related_name="alertes")
    mission = models.ForeignKey(Mission, on_delete=models.SET_NULL, blank=True, null=True, related_name="alertes")
    type_alerte = models.CharField(max_length=100)
    message = models.TextField()
    date_heure = models.DateTimeField(default=timezone.now)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="non_lue")

    class Meta:
        ordering = ["-date_heure"]

    def __str__(self):
        return f"{self.type_alerte} - {self.moto}"


class PreuveLivraison(models.Model):
    mission = models.OneToOneField(Mission, on_delete=models.CASCADE, related_name="preuve")
    otp_valide = models.BooleanField(default=False)
    latitude_validation = models.FloatField(blank=True, null=True)
    longitude_validation = models.FloatField(blank=True, null=True)
    date_validation = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date_validation"]

    def __str__(self):
        return f"Preuve {self.mission.reference}"
