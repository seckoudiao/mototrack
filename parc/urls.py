from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("motos/", views.moto_list, name="moto_list"),
    path("motos/ajouter/", views.moto_create, name="moto_create"),
    path("motos/<int:pk>/modifier/", views.moto_update, name="moto_update"),
    path("motos/<int:pk>/supprimer/", views.moto_delete, name="moto_delete"),
    path("livreurs/", views.livreur_list, name="livreur_list"),
    path("livreurs/ajouter/", views.livreur_create, name="livreur_create"),
    path("livreurs/<int:pk>/modifier/", views.livreur_update, name="livreur_update"),
    path("livreurs/<int:pk>/desactiver/", views.livreur_deactivate, name="livreur_deactivate"),
    path("affectations/", views.affectation_list, name="affectation_list"),
    path("affectations/ajouter/", views.affectation_create, name="affectation_create"),
    path("missions/", views.mission_list, name="mission_list"),
    path("missions/ajouter/", views.mission_create, name="mission_create"),
    path("missions/<int:pk>/", views.mission_detail, name="mission_detail"),
    path("missions/<int:pk>/modifier/", views.mission_update, name="mission_update"),
    path("carte/", views.carte_gps, name="carte_gps"),
    path("historique/", views.historique_gps, name="historique_gps"),
    path("alertes/", views.alerte_list, name="alerte_list"),
    path("alertes/<int:pk>/<str:statut>/", views.alerte_change_status, name="alerte_change_status"),
    path("preuves/", views.preuve_list, name="preuve_list"),
    path("espace-livreur/", views.livreur_dashboard, name="livreur_dashboard"),
    path("espace-livreur/missions/<int:pk>/", views.livreur_mission_detail, name="livreur_mission_detail"),
    path("espace-livreur/missions/<int:pk>/demarrer/", views.livreur_start_mission, name="livreur_start_mission"),
    path("espace-livreur/missions/<int:pk>/valider-otp/", views.livreur_validate_delivery, name="livreur_validate_delivery"),
    path("api/positions/", views.PositionCreateAPIView.as_view(), name="api_position_create"),
    path("api/positions/latest/", views.LatestPositionsAPIView.as_view(), name="api_positions_latest"),
    path("api/motos/", views.MotoListAPIView.as_view(), name="api_motos"),
    path("api/alertes/", views.AlerteListAPIView.as_view(), name="api_alertes"),
]
