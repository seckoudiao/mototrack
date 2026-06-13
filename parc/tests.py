from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Affectation, Alerte, Livreur, Mission, Moto, PositionGPS


class PositionAPITests(TestCase):
    def setUp(self):
        self.moto = Moto.objects.create(
            immatriculation="DK-1234-AB",
            marque="Yamaha",
            modele="Crypton",
        )

    def test_post_position_success(self):
        response = self.client.post(
            reverse("api_position_create"),
            data={"moto_id": self.moto.id, "latitude": 14.7886, "longitude": -16.9260, "vitesse": 35.5},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(PositionGPS.objects.count(), 1)

    def test_post_position_unknown_moto(self):
        response = self.client.post(
            reverse("api_position_create"),
            data={"moto_id": 999, "latitude": 14.7886, "longitude": -16.9260, "vitesse": 35.5},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["status"], "error")

    def test_speed_over_80_creates_alert(self):
        response = self.client.post(
            reverse("api_position_create"),
            data={"moto_id": self.moto.id, "latitude": 14.7886, "longitude": -16.9260, "vitesse": 95.0},
            content_type="application/json",
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
        self.user = User.objects.create_user(username="responsable", password="testpass123")
        self.livreur = Livreur.objects.create(
            nom="Diop",
            prenom="Awa",
            telephone="770000000",
            cni="CNI001",
            numero_permis="PERMIS001",
        )
        self.moto = Moto.objects.create(immatriculation="DK-5678-CD", marque="Honda", modele="Wave")
        Affectation.objects.create(livreur=self.livreur, moto=self.moto)
        self.mission = Mission.objects.create(
            reference="MIS-001",
            titre="Livraison test",
            adresse_depart="Dakar",
            adresse_destination="Thies",
            livreur=self.livreur,
            moto=self.moto,
            statut="en_cours",
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_dashboard_authenticated(self):
        self.client.login(username="responsable", password="testpass123")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")

    def test_validate_delivery_finishes_mission(self):
        self.client.login(username="responsable", password="testpass123")
        response = self.client.post(
            reverse("valider_livraison", args=[self.mission.id]),
            data={
                "nom_receptionnaire": "Mamadou Fall",
                "signature": "Mamadou Fall",
                "latitude_validation": 14.7,
                "longitude_validation": -17.4,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.statut, "terminee")
        self.assertTrue(hasattr(self.mission, "preuve"))
