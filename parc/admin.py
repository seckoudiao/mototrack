from django.contrib import admin

from .models import Affectation, Alerte, Livreur, Mission, Moto, PositionGPS, PreuveLivraison


@admin.register(Livreur)
class LivreurAdmin(admin.ModelAdmin):
    list_display = ("nom", "prenom", "user", "telephone", "cni", "statut")
    list_filter = ("statut",)
    search_fields = ("nom", "prenom", "telephone", "cni", "user__username")


@admin.register(Moto)
class MotoAdmin(admin.ModelAdmin):
    list_display = ("immatriculation", "marque", "modele", "etat")
    list_filter = ("etat",)
    search_fields = ("immatriculation", "marque", "modele")


@admin.register(Affectation)
class AffectationAdmin(admin.ModelAdmin):
    list_display = ("livreur", "moto", "date_debut", "date_fin", "active")
    list_filter = ("active",)


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ("reference", "client_nom", "client_telephone", "livreur", "moto", "statut", "date_creation")
    list_filter = ("statut",)
    search_fields = ("reference", "client_nom", "client_telephone", "adresse_livraison")


@admin.register(PositionGPS)
class PositionGPSAdmin(admin.ModelAdmin):
    list_display = ("moto", "latitude", "longitude", "vitesse", "date_heure")
    list_filter = ("moto",)


@admin.register(Alerte)
class AlerteAdmin(admin.ModelAdmin):
    list_display = ("type_alerte", "moto", "mission", "statut", "date_heure")
    list_filter = ("statut", "type_alerte")


@admin.register(PreuveLivraison)
class PreuveLivraisonAdmin(admin.ModelAdmin):
    list_display = ("mission", "otp_valide", "date_validation")
