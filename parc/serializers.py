from rest_framework import serializers

from .models import Alerte, Livreur, Moto, PositionGPS


class MotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moto
        fields = ["id", "immatriculation", "marque", "modele", "etat"]


class AlerteSerializer(serializers.ModelSerializer):
    moto = MotoSerializer(read_only=True)

    class Meta:
        model = Alerte
        fields = ["id", "moto", "mission", "type_alerte", "message", "date_heure", "statut"]


class PositionCreateSerializer(serializers.Serializer):
    moto_id = serializers.IntegerField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    vitesse = serializers.FloatField(required=False, allow_null=True, default=0)


class LatestPositionSerializer(serializers.ModelSerializer):
    moto_id = serializers.IntegerField(source="moto.id", read_only=True)
    immatriculation = serializers.CharField(source="moto.immatriculation", read_only=True)
    livreur = serializers.SerializerMethodField()

    class Meta:
        model = PositionGPS
        fields = [
            "id",
            "moto_id",
            "immatriculation",
            "livreur",
            "latitude",
            "longitude",
            "vitesse",
            "date_heure",
        ]

    def get_livreur(self, obj):
        affectation = obj.moto.affectations.filter(active=True).select_related("livreur").first()
        if not affectation:
            return None
        livreur = affectation.livreur
        return {
            "id": livreur.id,
            "nom_complet": f"{livreur.prenom} {livreur.nom}",
            "telephone": livreur.telephone,
        }
