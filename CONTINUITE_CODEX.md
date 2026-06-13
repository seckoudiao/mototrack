# Continuite Codex - MotoTrack

## Etat du projet

MotoTrack est un prototype Django + Django REST Framework stabilise pour un usage local. Le projet utilise Django Templates, Bootstrap et Leaflet. La base locale SQLite a ete recreee a partir des modeles actuels, et la migration initiale `parc` reflete maintenant ces modeles.

Commandes de validation attendues:

```powershell
python manage.py check
python manage.py test
```

## Architecture metier validee

- Responsable: compte Django `is_staff` ou `is_superuser`.
- Livreur: compte Django lie a un profil `Livreur`.
- Moto: vehicule suivi par positions GPS.
- Affectation: lien entre un livreur et une moto.
- Mission: livraison attribuee a un livreur et une moto, avec destination et OTP.
- PositionGPS: point GPS envoye par ESP32.
- Alerte: evenement interne, notamment vitesse superieure a 80 km/h.
- PreuveLivraison: preuve generee par validation OTP.

La livraison est validee par OTP uniquement. Il n'y a pas de SMS ni de signature dans la version actuelle.

## Modeles principaux

- `Livreur`: profil livreur, lie optionnellement a `User`.
- `Moto`: immatriculation, marque, modele, etat.
- `Affectation`: livreur, moto, dates, statut actif.
- `Mission`: client, telephone, adresse, destination GPS optionnelle, OTP, statut, dates.
- `PositionGPS`: moto, latitude, longitude, vitesse, date.
- `Alerte`: moto, mission optionnelle, type, message, statut.
- `PreuveLivraison`: mission, OTP valide, position de validation optionnelle, date.

## Routes importantes

Routes web responsable:

- `/` dashboard responsable
- `/motos/`
- `/livreurs/`
- `/affectations/`
- `/missions/`
- `/carte/`
- `/historique/`
- `/alertes/`
- `/preuves/`

Routes livreur:

- `/espace-livreur/`
- `/espace-livreur/missions/<id>/`
- `/espace-livreur/missions/<id>/demarrer/`
- `/espace-livreur/missions/<id>/valider-otp/`

Routes API:

- `POST /api/positions/` avec header obligatoire `X-API-KEY`
- `GET /api/positions/latest/`
- `GET /api/motos/`
- `GET /api/alertes/`

## Variables d'environnement

```text
SECRET_KEY=change-moi
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=
ESP32_API_KEY=mototrack-baol-express-2026
SUPABASE_BUCKET=media
```

En local, `DATABASE_URL` vide ou avec placeholder Supabase non remplace utilise SQLite. En production Render/Supabase, definir une URL PostgreSQL valide.

## Taches restantes

1. Creer des donnees de demonstration locales si necessaire.
2. Tester le flux complet dans le navigateur avec un responsable et un livreur reels.
3. Verifier le deploiement Render avec `DEBUG=False`.
4. Configurer une vraie base Supabase PostgreSQL et executer les migrations.
5. Ajouter plus tard des contraintes metier sur les affectations actives si le besoin est confirme.
