# GoLuto-backend

Django REST API for categories, offers, map businesses, JWT auth, and user preferences.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # optional: set SECRET_KEY / DEBUG
python manage.py migrate
python manage.py seed_test_data   # optional: loads sample categories, businesses, offers
python manage.py runserver
```

## API docs

- OpenAPI: `http://127.0.0.1:8000/api/schema/`
- Swagger: `http://127.0.0.1:8000/api/docs/`

## Auth (JWT)

- `POST /api/auth/register` — `email`, `password`, `password_confirm`
- `POST /api/auth/token` — `email`, `password` → `access`, `refresh`
- `POST /api/auth/token/refresh` — `refresh`
- Protected routes: `Authorization: Bearer <access>`

## Deploy on Render

1. Push this repo to GitHub (see below).
2. In [Render](https://dashboard.render.com): **New** → **Blueprint** → connect the repo, or **Web Service** + **PostgreSQL** manually.
3. If you use the included `render.yaml`, Render creates a **PostgreSQL** database and sets `DATABASE_URL`; the web service runs migrations then Gunicorn on each start (free tier does not support `preDeployCommand`, so migrate is in `startCommand`).
4. In the web service, set environment variables if not using Blueprint:
   - `DEBUG=False`
   - `SECRET_KEY` (long random string)
   - `DATABASE_URL` (from Render Postgres **Internal Database URL**)
   - `ALLOWED_HOSTS` optional — if unset on Render, `RENDER_EXTERNAL_HOSTNAME` is used when `RENDER` is set (see `config/settings.py`).

**Build command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`  
**Start command:** `python manage.py migrate --noinput && python manage.py ensure_superuser && python manage.py seed_test_data && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

### Test / sample data

Run locally:

```bash
python manage.py seed_test_data
```

On Render, set **`SEED_TEST_DATA=True`** on the web service (included in `render.yaml`). Each deploy runs seed after migrate (idempotent — safe to re-run).

| Item | Details |
|------|---------|
| Categories | Food, Fashion, Electronics |
| Businesses | Burger Hub, Style Corner, Gadget Point (Karachi-area coords) |
| Offers | Lunch Deal (30%), Weekend Fashion Sale (25%, active), Flash Electronics (40%, expired) |
| Test app user | `testuser@example.com` / `testpass123` (JWT login, not admin) |

Remove **`SEED_TEST_DATA`** from production when you no longer want sample data re-applied on restart.

### Django admin without Shell (Render free tier)

Render’s **Shell** often requires a paid plan. To create an admin user, set these on the **Web Service** → **Environment** (not in git):

| Variable | Example |
|----------|---------|
| `ADMIN_EMAIL` | `you@example.com` |
| `ADMIN_PASSWORD` | A strong one-time password |

Redeploy or restart. Then open `https://<your-service>.onrender.com/admin/` and sign in with that email and password (type the password in the form—it is not filled from env automatically). **Remove `ADMIN_PASSWORD` from the environment afterward** (or change the password in admin) so it is not stored in the dashboard long term.

If that email was already used for a normal signup via the API, the command **promotes** that account to superuser instead of skipping.

Locally you can always run: `python manage.py createsuperuser`

**Render:** In the web service **Settings**, check **Start Command**. If it was set manually, it overrides `render.yaml` and must include:

`python manage.py migrate --noinput && python manage.py ensure_superuser && python manage.py seed_test_data && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

After deploy, **Logs** should mention `Created superuser`, `Promoted`, or `Synced password`. If you only see Gunicorn lines, the command above is not running.

## GitHub

```bash
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/abdullahaslam0079/GoLuto-backend.git
git push -u origin main
```

Use a [Personal Access Token](https://github.com/settings/tokens) or SSH if HTTPS asks for credentials.
