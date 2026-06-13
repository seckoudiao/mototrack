# MotoTrack

MotoTrack est un prototype Django + Django REST Framework pour gerer des motos de livraison, livreurs, missions, positions GPS ESP32, alertes internes et preuves de livraison par OTP.

## Installation locale

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Sur macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration `.env`

Copier `.env.example` vers `.env`, puis adapter les valeurs.

```text
SECRET_KEY=change-moi
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=
ESP32_API_KEY=mototrack-baol-express-2026
SUPABASE_BUCKET=media
```

En local, laisser `DATABASE_URL` vide ou avec le placeholder Supabase non remplace utilise SQLite automatiquement.

## Migrations

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py check
python manage.py test
```

La base locale par defaut est `db.sqlite3`. Les migrations restent compatibles avec PostgreSQL/Supabase pour un deploiement ulterieur.

## Creation du superuser responsable

```powershell
python manage.py createsuperuser
```

Le dashboard responsable est reserve aux comptes `is_staff` ou `is_superuser`.

## Creation d'un livreur

1. Creer un utilisateur Django pour le livreur depuis `/admin/`.
2. Creer un objet `Livreur` et lier son champ `user` a ce compte.
3. Affecter une moto au livreur via `Affectation`.
4. Creer une mission pour ce livreur et cette moto.

Le livreur se connecte avec son compte et accede a `/espace-livreur/`.

## Lancement serveur

```powershell
python manage.py runserver 0.0.0.0:8000
```

URLs utiles:

- Application web: `http://127.0.0.1:8000/`
- Admin Django: `http://127.0.0.1:8000/admin/`
- Login: `http://127.0.0.1:8000/accounts/login/`
- Espace livreur: `http://127.0.0.1:8000/espace-livreur/`

## Test API ESP32

Creer d'abord une moto dans l'interface web ou dans l'admin. Si son ID est `1`, tester:

```powershell
curl -X POST http://127.0.0.1:8000/api/positions/ `
  -H "Content-Type: application/json" `
  -H "X-API-KEY: mototrack-baol-express-2026" `
  -d "{\"moto_id\":1,\"latitude\":14.7886,\"longitude\":-16.9260,\"vitesse\":35.5}"
```

Tester une alerte vitesse:

```powershell
curl -X POST http://127.0.0.1:8000/api/positions/ `
  -H "Content-Type: application/json" `
  -H "X-API-KEY: mototrack-baol-express-2026" `
  -d "{\"moto_id\":1,\"latitude\":14.7886,\"longitude\":-16.9260,\"vitesse\":95.0}"
```

Endpoints disponibles:

- `POST /api/positions/` avec header obligatoire `X-API-KEY`
- `GET /api/positions/latest/`
- `GET /api/motos/`
- `GET /api/alertes/`

## Test avec Postman

1. Methode: `POST`
2. URL: `http://127.0.0.1:8000/api/positions/`
3. Headers:
   - `Content-Type: application/json`
   - `X-API-KEY: mototrack-baol-express-2026`
4. Body: `raw`, format `JSON`

```json
{
  "moto_id": 1,
  "latitude": 14.7886,
  "longitude": -16.9260,
  "vitesse": 35.5
}
```

Reponse attendue:

```json
{
  "status": "success",
  "message": "Position enregistree"
}
```

## ESP32

Un exemple complet est fourni dans:

```text
outputs/esp32_post_position.ino
```

Le PC et l'ESP32 doivent etre sur le meme reseau. Remplacer:

```cpp
const char* serverUrl = "http://ADRESSE_IP_DU_PC:8000/api/positions/";
```

par l'adresse IP locale du PC, par exemple:

```cpp
const char* serverUrl = "http://192.168.1.20:8000/api/positions/";
```

Le sketch envoie le header `X-API-KEY`.

## Livraison et OTP

La validation de livraison se fait uniquement par OTP:

1. Le responsable cree une mission.
2. MotoTrack genere une reference et un OTP.
3. Le livreur demarre la mission.
4. A la livraison, le client donne l'OTP au livreur.
5. Le livreur valide la livraison dans son espace.

Aucun SMS ni signature n'est utilise dans cette version.

## Deploiement Render

Fichiers deja presents:

- `Procfile`
- `build.sh`
- `requirements.txt`
- configuration Whitenoise dans `backend/settings.py`

Variables Render recommandees:

```text
SECRET_KEY=une-cle-secrete-forte
DEBUG=False
ALLOWED_HOSTS=votre-app.onrender.com
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
ESP32_API_KEY=une-cle-api-forte
SUPABASE_BUCKET=media
```

`build.sh` installe les dependances, collecte les fichiers statiques et applique les migrations.

## Configuration Supabase

Pour utiliser PostgreSQL Supabase, definir `DATABASE_URL` avec l'URL PostgreSQL complete fournie par Supabase.

Exemple:

```text
DATABASE_URL=postgresql://postgres:MOT_DE_PASSE@db.xxxxx.supabase.co:5432/postgres
```

Si le mot de passe contient des caracteres speciaux, il doit etre encode pour une URL.
