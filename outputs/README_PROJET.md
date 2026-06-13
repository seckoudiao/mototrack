# Plateforme IoT low-cost de suivi de motos

Prototype Django + Django REST Framework pour gerer des motos, livreurs, missions, positions GPS ESP32, alertes internes et preuves de livraison.

## 1. Installation

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

## 2. Structure du projet

```text
backend/
  settings.py
  urls.py
  asgi.py
  wsgi.py
parc/
  models.py
  serializers.py
  forms.py
  views.py
  urls.py
  admin.py
  migrations/
templates/
  base.html
  registration/login.html
  parc/
static/
  parc/css/style.css
outputs/
  esp32_post_position.ino
manage.py
requirements.txt
.env.example
```

## 3. Migrations

```powershell
python manage.py makemigrations
python manage.py migrate
```

## 4. Creer le responsable

```powershell
python manage.py createsuperuser
```

Puis saisir un nom d'utilisateur, email optionnel et mot de passe.

## 5. Lancer le serveur

```powershell
python manage.py runserver 0.0.0.0:8000
```

Ouvrir ensuite:

- Application web: http://127.0.0.1:8000/
- Admin Django: http://127.0.0.1:8000/admin/
- Login responsable: http://127.0.0.1:8000/accounts/login/

## 6. Tester l'API avec curl

Creer d'abord une moto dans l'interface web ou dans l'admin. Si son ID est `1`, tester:

```powershell
curl -X POST http://127.0.0.1:8000/api/positions/ `
  -H "Content-Type: application/json" `
  -d "{\"moto_id\":1,\"latitude\":14.7886,\"longitude\":-16.9260,\"vitesse\":35.5}"
```

Tester une alerte vitesse:

```powershell
curl -X POST http://127.0.0.1:8000/api/positions/ `
  -H "Content-Type: application/json" `
  -d "{\"moto_id\":1,\"latitude\":14.7886,\"longitude\":-16.9260,\"vitesse\":95.0}"
```

Endpoints disponibles:

- `POST /api/positions/`
- `GET /api/positions/latest/`
- `GET /api/motos/`
- `GET /api/alertes/`

## 7. Tester avec Postman

1. Methode: `POST`
2. URL: `http://127.0.0.1:8000/api/positions/`
3. Onglet Body: `raw`, format `JSON`
4. Corps:

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

## 8. ESP32

Un exemple complet est fourni dans:

```text
outputs/esp32_post_position.ino
```

Important: pour tester depuis l'ESP32, le PC et l'ESP32 doivent etre sur le meme hotspot mobile. Dans le code ESP32, remplacer:

```cpp
const char* serverUrl = "http://ADRESSE_IP_DU_PC:8000/api/positions/";
```

par l'adresse IP locale du PC, par exemple:

```cpp
const char* serverUrl = "http://192.168.1.20:8000/api/positions/";
```

## 9. Preparation Render et Supabase

Le projet demarre avec SQLite. Pour PostgreSQL/Supabase plus tard, definir `DATABASE_URL` dans les variables d'environnement Render:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
DEBUG=False
ALLOWED_HOSTS=votre-app.onrender.com
SECRET_KEY=une-cle-secrete-forte
```

Le fichier `backend/settings.py` utilise deja `dj-database-url`, donc aucune grosse modification ne sera necessaire.
