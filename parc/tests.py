from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Affectation, Alerte, Livreur, Mission, Moto, PositionGPS, PreuveLivraison


class PositionAPITests(TestCase):
    def setUp(self):
        self.moto = Moto.objects.create(
            immatriculation="DK-1234-AB",
            marque="Yamaha",
            modele="Crypton",
        )
        self.api_headers = {"HTTP_X_API_KEY": settings.ESP32_API_KEY}

    def test_post_position_requires_api_key(self):
        response = self.client.post(
            reverse("api_position_create"),
            data={"moto_id": self.moto.id, "latitude": 14.7886, "longitude": -16.9260, "vitesse": 35.5},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(PositionGPS.objects.count(), 0)

    def test_post_position_success_with_api_key(self):
        response = self.client.post(
            reverse("api_position_create"),
            data={"moto_id": self.moto.id, "latitude": 14.7886, "longitude": -16.9260, "vitesse": 35.5},
            content_type="application/json",
            **self.api_headers,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(PositionGPS.objects.count(), 1)

    def test_post_position_without_speed_defaults_to_zero(self):
        response = self.client.post(
            reverse("api_position_create"),
            data={"moto_id": self.moto.id, "latitude": 14.123456, "longitude": -16.123456},
            content_type="application/json",
            **self.api_headers,
        )

        self.assertEqual(response.status_code, 201)
        position = PositionGPS.objects.get()
        self.assertEqual(position.latitude, 14.123456)
        self.assertEqual(position.longitude, -16.123456)
        self.assertEqual(position.vitesse, 0)

    def test_post_position_unknown_moto_with_api_key(self):
        response = self.client.post(
            reverse("api_position_create"),
            data={"moto_id": 999, "latitude": 14.7886, "longitude": -16.9260, "vitesse": 35.5},
            content_type="application/json",
            **self.api_headers,
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["status"], "error")

    def test_post_position_rejects_invalid_coordinates(self):
        response = self.client.post(
            reverse("api_position_create"),
            data={"moto_id": self.moto.id, "latitude": 0, "longitude": 0},
            content_type="application/json",
            **self.api_headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PositionGPS.objects.count(), 0)

    def test_post_position_ignores_abnormal_gps_jump(self):
        PositionGPS.objects.create(moto=self.moto, latitude=14.7886, longitude=-16.9260)

        response = self.client.post(
            reverse("api_position_create"),
            data={"moto_id": self.moto.id, "latitude": 14.95, "longitude": -16.70},
            content_type="application/json",
            **self.api_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ignored")
        self.assertEqual(response.json()["message"], "Position ignoree : saut GPS anormal")
        self.assertEqual(PositionGPS.objects.count(), 1)

    def test_speed_over_80_creates_alert(self):
        response = self.client.post(
            reverse("api_position_create"),
            data={"moto_id": self.moto.id, "latitude": 14.7886, "longitude": -16.9260, "vitesse": 95.0},
            content_type="application/json",
            **self.api_headers,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Alerte.objects.count(), 1)
        self.assertEqual(Alerte.objects.first().type_alerte, "vitesse")

    def test_latest_positions_returns_only_last_position_per_moto(self):
        PositionGPS.objects.create(
            moto=self.moto,
            latitude=14.0,
            longitude=-16.0,
            vitesse=10,
            date_heure=timezone.now() - timezone.timedelta(minutes=5),
        )
        PositionGPS.objects.create(
            moto=self.moto,
            latitude=15.0,
            longitude=-17.0,
            vitesse=20,
            date_heure=timezone.now(),
        )

        response = self.client.get(reverse("api_positions_latest"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["latitude"], 15.0)


class WebPageTests(TestCase):
    def setUp(self):
        self.responsable = User.objects.create_user(
            username="responsable",
            password="testpass123",
            is_staff=True,
        )
        self.simple_user = User.objects.create_user(username="simple", password="testpass123")
        self.livreur_user = User.objects.create_user(username="livreur", password="testpass123")
        self.livreur = Livreur.objects.create(
            user=self.livreur_user,
            nom="Diop",
            prenom="Awa",
            telephone="770000000",
            cni="CNI001",
            numero_permis="PERMIS001",
        )
        self.moto = Moto.objects.create(immatriculation="DK-5678-CD", marque="Honda", modele="Wave")
        Affectation.objects.create(livreur=self.livreur, moto=self.moto)
        self.mission = Mission.objects.create(
            client_nom="Mamadou Fall",
            client_telephone="770000001",
            adresse_livraison="Thies",
            description_lieu="Pres de la gare",
            description_colis="Petit colis",
            otp_code="123456",
            livreur=self.livreur,
            moto=self.moto,
            statut="en_cours",
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_dashboard_requires_staff_or_superuser(self):
        self.client.login(username="simple", password="testpass123")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_dashboard_accessible_to_staff_responsable(self):
        self.client.login(username="responsable", password="testpass123")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard responsable")

    def test_validate_delivery_by_otp_finishes_mission(self):
        self.mission.latitude_destination = 14.7
        self.mission.longitude_destination = -17.4
        self.mission.save(update_fields=["latitude_destination", "longitude_destination"])
        PositionGPS.objects.create(moto=self.moto, latitude=14.7001, longitude=-17.4001)

        self.client.login(username="livreur", password="testpass123")
        response = self.client.post(
            reverse("livreur_validate_delivery", args=[self.mission.id]),
            data={
                "otp_code": self.mission.otp_code,
                "latitude_validation": 14.7,
                "longitude_validation": -17.4,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.mission.refresh_from_db()
        self.mission.moto.refresh_from_db()
        self.assertEqual(self.mission.statut, "terminee")
        self.assertEqual(self.mission.moto.etat, "disponible")
        preuve = PreuveLivraison.objects.get(mission=self.mission)
        self.assertTrue(preuve.otp_valide)
        self.assertEqual(preuve.latitude_validation, 14.7001)

    def test_validate_delivery_rejects_wrong_otp(self):
        self.client.login(username="livreur", password="testpass123")
        response = self.client.post(
            reverse("livreur_validate_delivery", args=[self.mission.id]),
            data={"otp_code": "000000"},
        )

        self.assertEqual(response.status_code, 200)
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.statut, "en_cours")
        self.assertFalse(PreuveLivraison.objects.filter(mission=self.mission).exists())

    def test_validate_delivery_rejects_missing_gps_position(self):
        self.mission.latitude_destination = 14.7
        self.mission.longitude_destination = -17.4
        self.mission.save(update_fields=["latitude_destination", "longitude_destination"])

        self.client.login(username="livreur", password="testpass123")
        response = self.client.post(
            reverse("livreur_validate_delivery", args=[self.mission.id]),
            data={"otp_code": self.mission.otp_code},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aucune position GPS récente disponible pour cette moto.")
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.statut, "en_cours")
        self.assertFalse(PreuveLivraison.objects.filter(mission=self.mission).exists())

    def test_validate_delivery_rejects_old_gps_position(self):
        self.mission.latitude_destination = 14.7
        self.mission.longitude_destination = -17.4
        self.mission.save(update_fields=["latitude_destination", "longitude_destination"])
        PositionGPS.objects.create(
            moto=self.moto,
            latitude=14.7001,
            longitude=-17.4001,
            date_heure=timezone.now() - timezone.timedelta(minutes=3),
        )

        self.client.login(username="livreur", password="testpass123")
        response = self.client.post(
            reverse("livreur_validate_delivery", args=[self.mission.id]),
            data={"otp_code": self.mission.otp_code},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Position GPS trop ancienne pour valider la livraison.")
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.statut, "en_cours")
        self.assertFalse(PreuveLivraison.objects.filter(mission=self.mission).exists())

    def test_validate_delivery_rejects_far_gps_position(self):
        self.mission.latitude_destination = 14.7
        self.mission.longitude_destination = -17.4
        self.mission.save(update_fields=["latitude_destination", "longitude_destination"])
        PositionGPS.objects.create(moto=self.moto, latitude=14.75, longitude=-17.45)

        self.client.login(username="livreur", password="testpass123")
        response = self.client.post(
            reverse("livreur_validate_delivery", args=[self.mission.id]),
            data={"otp_code": self.mission.otp_code},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vous êtes trop éloigné de la destination pour valider cette livraison.")
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.statut, "en_cours")
        self.assertFalse(PreuveLivraison.objects.filter(mission=self.mission).exists())

    def test_validate_delivery_rejects_missing_destination_gps(self):
        PositionGPS.objects.create(moto=self.moto, latitude=14.7, longitude=-17.4)

        self.client.login(username="livreur", password="testpass123")
        response = self.client.post(
            reverse("livreur_validate_delivery", args=[self.mission.id]),
            data={"otp_code": self.mission.otp_code},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Destination GPS non renseignee pour cette mission.")
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.statut, "en_cours")
        self.assertFalse(PreuveLivraison.objects.filter(mission=self.mission).exists())

    def test_mission_detail_tracks_positions_after_departure_only(self):
        now = timezone.now()
        depart = now - timezone.timedelta(minutes=10)
        self.mission.date_depart = depart
        self.mission.save(update_fields=["date_depart"])
        PositionGPS.objects.create(
            moto=self.moto,
            latitude=13.0,
            longitude=-15.0,
            date_heure=depart - timezone.timedelta(minutes=5),
        )
        PositionGPS.objects.create(
            moto=self.moto,
            latitude=14.1,
            longitude=-16.1,
            date_heure=depart + timezone.timedelta(minutes=1),
        )
        PositionGPS.objects.create(
            moto=self.moto,
            latitude=14.2,
            longitude=-16.2,
            date_heure=now - timezone.timedelta(seconds=10),
        )

        self.client.login(username="responsable", password="testpass123")
        response = self.client.get(reverse("mission_detail", args=[self.mission.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Suivi GPS de la mission")
        self.assertContains(response, "Lieu actuel estime")
        self.assertContains(response, "Statut GPS")
        self.assertContains(response, "En ligne")
        self.assertContains(response, "Derniere position recue il y a")
        self.assertContains(response, "Voir donnees techniques")
        self.assertNotContains(response, "Coordonnees GPS:")
        self.assertContains(response, "Trajet GPS estime a partir des positions recues")
        positions = response.context["positions"]
        self.assertEqual(len(positions), 2)
        self.assertEqual(positions[0].latitude, 14.1)
        self.assertEqual(response.context["latest_position"].latitude, 14.2)
        self.assertEqual(response.context["gps_status"]["label"], "En ligne")

    def test_mission_detail_without_departure_has_no_track_positions(self):
        self.mission.date_depart = None
        self.mission.save(update_fields=["date_depart"])
        PositionGPS.objects.create(moto=self.moto, latitude=14.1, longitude=-16.1)

        self.client.login(username="responsable", password="testpass123")
        response = self.client.get(reverse("mission_detail", args=[self.mission.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "La mission n'a pas encore demarre.")
        self.assertEqual(response.context["positions"], [])

    def test_livreur_mission_detail_shows_tracking_after_departure(self):
        now = timezone.now()
        depart = now - timezone.timedelta(minutes=3)
        self.mission.date_depart = depart
        self.mission.save(update_fields=["date_depart"])
        PositionGPS.objects.create(
            moto=self.moto,
            latitude=14.1,
            longitude=-16.1,
            date_heure=depart + timezone.timedelta(seconds=10),
        )

        self.client.login(username="livreur", password="testpass123")
        response = self.client.get(reverse("livreur_mission_detail", args=[self.mission.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Suivi GPS de la mission")
        self.assertContains(response, "Lieu actuel estime")
        self.assertContains(response, "Statut GPS")
        self.assertEqual(len(response.context["positions"]), 1)

    def test_livreur_mission_detail_before_departure_prompts_start(self):
        self.mission.date_depart = None
        self.mission.save(update_fields=["date_depart"])
        PositionGPS.objects.create(moto=self.moto, latitude=14.1, longitude=-16.1)

        self.client.login(username="livreur", password="testpass123")
        response = self.client.get(reverse("livreur_mission_detail", args=[self.mission.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Demarrez la mission pour commencer le suivi GPS.")
        self.assertEqual(response.context["positions"], [])
