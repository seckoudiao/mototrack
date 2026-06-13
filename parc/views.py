import json
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import OuterRef, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import AffectationForm, LivreurForm, MissionForm, MotoForm, OTPValidationForm
from .models import Affectation, Alerte, Livreur, Mission, Moto, PositionGPS, PreuveLivraison
from .serializers import AlerteSerializer, LatestPositionSerializer, MotoSerializer, PositionCreateSerializer


def responsable_required(view_func):
    """Reserve une vue aux responsables connectes."""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        if hasattr(request.user, "profil_livreur"):
            return redirect("livreur_dashboard")
        messages.error(request, "Votre compte n'a pas acces a l'espace responsable.")
        return redirect("login")

    return wrapper


def livreur_required(view_func):
    """Reserve une vue au livreur connecte."""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        livreur = getattr(request.user, "profil_livreur", None)
        if livreur:
            request.livreur = livreur
            return view_func(request, *args, **kwargs)
        messages.error(request, "Aucun profil livreur n'est lie a ce compte.")
        return redirect("dashboard")

    return wrapper


def get_latest_positions():
    latest_ids = PositionGPS.objects.filter(moto=OuterRef("moto")).order_by("-date_heure").values("id")[:1]
    return (
        PositionGPS.objects.filter(id__in=Subquery(latest_ids))
        .select_related("moto")
        .prefetch_related("moto__affectations__livreur")
        .order_by("moto__immatriculation")
    )


def positions_to_map_json(positions):
    data = LatestPositionSerializer(positions, many=True).data
    return json.dumps(list(data), cls=DjangoJSONEncoder)


def mission_to_destination_json(mission):
    if mission.latitude_destination is None or mission.longitude_destination is None:
        return "{}"
    return json.dumps(
        {
            "reference": mission.reference,
            "client": mission.client_nom,
            "latitude": mission.latitude_destination,
            "longitude": mission.longitude_destination,
        },
        cls=DjangoJSONEncoder,
    )


class PositionCreateAPIView(APIView):
    """Endpoint appele par l'ESP32 toutes les 10 secondes."""

    def post(self, request):
        api_key = request.headers.get("X-API-KEY")
        if api_key != settings.ESP32_API_KEY:
            return Response(
                {"status": "error", "message": "Cle API invalide"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = PositionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"status": "error", "message": "Donnees invalides", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        moto = Moto.objects.filter(id=data["moto_id"]).first()
        if not moto:
            return Response(
                {"status": "error", "message": "Moto introuvable"},
                status=status.HTTP_404_NOT_FOUND,
            )

        vitesse = data.get("vitesse")
        if vitesse is None:
            vitesse = 0

        position = PositionGPS.objects.create(
            moto=moto,
            latitude=data["latitude"],
            longitude=data["longitude"],
            vitesse=vitesse,
        )
        mission = Mission.objects.filter(moto=moto, statut="en_cours").first()

        if position.vitesse > 80:
            Alerte.objects.create(
                moto=moto,
                mission=mission,
                type_alerte="vitesse",
                message=f"Vitesse elevee detectee: {position.vitesse} km/h pour la moto {moto.immatriculation}.",
            )

        return Response({"status": "success", "message": "Position enregistree"}, status=status.HTTP_201_CREATED)


class LatestPositionsAPIView(APIView):
    def get(self, request):
        return Response(LatestPositionSerializer(get_latest_positions(), many=True).data)


class MotoListAPIView(APIView):
    def get(self, request):
        return Response(MotoSerializer(Moto.objects.all(), many=True).data)


class AlerteListAPIView(APIView):
    def get(self, request):
        alertes = Alerte.objects.select_related("moto", "mission")
        return Response(AlerteSerializer(alertes, many=True).data)


@responsable_required
def dashboard(request):
    latest_positions = get_latest_positions()
    context = {
        "motos_count": Moto.objects.count(),
        "livreurs_count": Livreur.objects.count(),
        "missions_count": Mission.objects.count(),
        "missions_en_cours_count": Mission.objects.filter(statut="en_cours").count(),
        "alertes_non_lues_count": Alerte.objects.filter(statut="non_lue").count(),
        "latest_positions_json": positions_to_map_json(latest_positions),
        "recent_missions": Mission.objects.select_related("livreur", "moto")[:5],
        "recent_alertes": Alerte.objects.select_related("moto", "mission")[:5],
    }
    return render(request, "parc/dashboard.html", context)


@responsable_required
def moto_list(request):
    return render(request, "parc/moto_list.html", {"motos": Moto.objects.all()})


@responsable_required
def moto_create(request):
    form = MotoForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Moto ajoutee avec succes.")
        return redirect("moto_list")
    return render(request, "parc/form.html", {"form": form, "title": "Ajouter une moto"})


@responsable_required
def moto_update(request, pk):
    moto = get_object_or_404(Moto, pk=pk)
    form = MotoForm(request.POST or None, instance=moto)
    if form.is_valid():
        form.save()
        messages.success(request, "Moto modifiee avec succes.")
        return redirect("moto_list")
    return render(request, "parc/form.html", {"form": form, "title": "Modifier une moto"})


@responsable_required
def moto_delete(request, pk):
    moto = get_object_or_404(Moto, pk=pk)
    if request.method == "POST":
        moto.delete()
        messages.success(request, "Moto supprimee.")
        return redirect("moto_list")
    return render(request, "parc/confirm_delete.html", {"object": moto, "title": "Supprimer la moto"})


@responsable_required
def livreur_list(request):
    return render(request, "parc/livreur_list.html", {"livreurs": Livreur.objects.select_related("user")})


@responsable_required
def livreur_create(request):
    form = LivreurForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Livreur ajoute avec succes.")
        return redirect("livreur_list")
    return render(request, "parc/form.html", {"form": form, "title": "Ajouter un livreur"})


@responsable_required
def livreur_update(request, pk):
    livreur = get_object_or_404(Livreur, pk=pk)
    form = LivreurForm(request.POST or None, request.FILES or None, instance=livreur)
    if form.is_valid():
        form.save()
        messages.success(request, "Livreur modifie avec succes.")
        return redirect("livreur_list")
    return render(request, "parc/form.html", {"form": form, "title": "Modifier un livreur"})


@responsable_required
def livreur_deactivate(request, pk):
    livreur = get_object_or_404(Livreur, pk=pk)
    livreur.statut = "inactif"
    livreur.save(update_fields=["statut"])
    messages.success(request, "Livreur desactive.")
    return redirect("livreur_list")


@responsable_required
def affectation_list(request):
    affectations = Affectation.objects.select_related("livreur", "moto")
    return render(request, "parc/affectation_list.html", {"affectations": affectations})


@responsable_required
def affectation_create(request):
    form = AffectationForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Affectation creee avec succes.")
        return redirect("affectation_list")
    return render(request, "parc/form.html", {"form": form, "title": "Ajouter une affectation"})


@responsable_required
def mission_list(request):
    missions = Mission.objects.select_related("livreur", "moto")
    return render(request, "parc/mission_list.html", {"missions": missions})


@responsable_required
def mission_create(request):
    form = MissionForm(request.POST or None)
    if form.is_valid():
        mission = form.save()
        if mission.statut == "en_cours" and not mission.date_depart:
            mission.date_depart = timezone.now()
            mission.moto.etat = "en_service"
            mission.moto.save(update_fields=["etat"])
            mission.save(update_fields=["date_depart"])
        messages.success(request, f"Mission {mission.reference} creee. OTP client: {mission.otp_code}")
        return redirect("mission_detail", pk=mission.pk)
    return render(request, "parc/mission_form.html", {"form": form, "title": "Creer une mission"})


@responsable_required
def mission_update(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    form = MissionForm(request.POST or None, instance=mission)
    if form.is_valid():
        mission = form.save()
        if mission.statut == "en_cours" and not mission.date_depart:
            mission.date_depart = timezone.now()
        if mission.statut == "terminee" and not mission.date_fin:
            mission.date_fin = timezone.now()
        mission.save()
        messages.success(request, "Mission modifiee avec succes.")
        return redirect("mission_detail", pk=mission.pk)
    return render(request, "parc/mission_form.html", {"form": form, "title": "Modifier la mission", "mission": mission})


@responsable_required
def mission_detail(request, pk):
    mission = get_object_or_404(Mission.objects.select_related("livreur", "moto"), pk=pk)
    positions = PositionGPS.objects.filter(moto=mission.moto)[:50]
    return render(
        request,
        "parc/mission_detail.html",
        {
            "mission": mission,
            "positions": positions,
            "destination_json": mission_to_destination_json(mission),
        },
    )


@responsable_required
def carte_gps(request):
    return render(request, "parc/carte_gps.html", {"latest_positions_json": positions_to_map_json(get_latest_positions())})


@responsable_required
def historique_gps(request):
    motos = Moto.objects.all()
    moto_id = request.GET.get("moto")
    selected_moto = Moto.objects.filter(id=moto_id).first() if moto_id else None
    positions = PositionGPS.objects.filter(moto=selected_moto)[:100] if selected_moto else []
    return render(
        request,
        "parc/historique_gps.html",
        {
            "motos": motos,
            "selected_moto": selected_moto,
            "positions": positions,
            "positions_json": positions_to_map_json(positions) if selected_moto else "[]",
        },
    )


@responsable_required
def alerte_list(request):
    alertes = Alerte.objects.select_related("moto", "mission")
    return render(request, "parc/alerte_list.html", {"alertes": alertes})


@responsable_required
def alerte_change_status(request, pk, statut):
    alerte = get_object_or_404(Alerte, pk=pk)
    if statut in ["lue", "traitee"]:
        alerte.statut = statut
        alerte.save(update_fields=["statut"])
        messages.success(request, "Statut de l'alerte mis a jour.")
    return redirect("alerte_list")


@responsable_required
def preuve_list(request):
    preuves = PreuveLivraison.objects.select_related("mission", "mission__livreur", "mission__moto")
    return render(request, "parc/preuve_list.html", {"preuves": preuves})


@livreur_required
def livreur_dashboard(request):
    missions = Mission.objects.filter(livreur=request.livreur).select_related("moto")
    return render(request, "parc/livreur/dashboard.html", {"livreur": request.livreur, "missions": missions})


@livreur_required
def livreur_mission_detail(request, pk):
    mission = get_object_or_404(Mission.objects.select_related("moto"), pk=pk, livreur=request.livreur)
    return render(
        request,
        "parc/livreur/mission_detail.html",
        {"mission": mission, "destination_json": mission_to_destination_json(mission)},
    )


@livreur_required
def livreur_start_mission(request, pk):
    mission = get_object_or_404(Mission, pk=pk, livreur=request.livreur)
    if request.method == "POST" and mission.statut == "planifiee":
        mission.statut = "en_cours"
        mission.date_depart = timezone.now()
        mission.moto.etat = "en_service"
        mission.moto.save(update_fields=["etat"])
        mission.save(update_fields=["statut", "date_depart"])
        messages.success(request, "Mission demarree.")
    return redirect("livreur_mission_detail", pk=mission.pk)


@livreur_required
def livreur_validate_delivery(request, pk):
    mission = get_object_or_404(Mission, pk=pk, livreur=request.livreur)
    form = OTPValidationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        otp_code = form.cleaned_data["otp_code"]
        if otp_code != mission.otp_code:
            form.add_error("otp_code", "Code OTP incorrect.")
        else:
            PreuveLivraison.objects.update_or_create(
                mission=mission,
                defaults={
                    "otp_valide": True,
                    "latitude_validation": form.cleaned_data.get("latitude_validation"),
                    "longitude_validation": form.cleaned_data.get("longitude_validation"),
                    "date_validation": timezone.now(),
                },
            )
            mission.statut = "terminee"
            mission.date_fin = timezone.now()
            mission.moto.etat = "disponible"
            mission.moto.save(update_fields=["etat"])
            mission.save(update_fields=["statut", "date_fin"])
            messages.success(request, "Livraison validee par OTP.")
            return redirect("livreur_mission_detail", pk=mission.pk)

    return render(request, "parc/livreur/validate_otp.html", {"mission": mission, "form": form})
