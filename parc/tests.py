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
        self.assertEqual(preuve.latitude_validation, 14.7)

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
