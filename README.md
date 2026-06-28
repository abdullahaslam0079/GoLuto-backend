# GoLuto-backend

Django REST API for categories, offers, map businesses, JWT auth, and user preferences.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # optional: set SECRET_KEY / DEBUG
python manage.py migrate
python manage.py runserver
```

## API docs

- **Production Swagger:** https://goluto-backend.onrender.com/api/docs/
- **Production OpenAPI:** https://goluto-backend.onrender.com/api/schema/
- Local OpenAPI: `http://127.0.0.1:8000/api/schema/`
- Local Swagger: `http://127.0.0.1:8000/api/docs/`

## Postman

Share these files with anyone testing the API:

| File | Purpose |
|------|---------|
| [`postman/GoLuto-API.postman_collection.json`](postman/GoLuto-API.postman_collection.json) | All endpoints, sample bodies, auto-save JWT on login |
| [`postman/GoLuto-Production.postman_environment.json`](postman/GoLuto-Production.postman_environment.json) | `base_url` → production |
| [`postman/GoLuto-Local.postman_environment.json`](postman/GoLuto-Local.postman_environment.json) | `base_url` → local dev server |

**Import in Postman**

1. **Import** → drag the collection + environment JSON files (or **Link** → `https://goluto-backend.onrender.com/api/schema/` to import from OpenAPI only).
2. Select **GoLuto — Production** (top-right environment dropdown).
3. Run **Auth — Consumer → Login** or **Auth — Business → Login** — the access token is saved automatically.
4. Call endpoints in **Public**, **Consumer**, or **Business** folders.

Regenerate the collection after endpoint changes: `python3 postman/generate_collection.py`

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
**Start command:** `python manage.py migrate --noinput && python manage.py ensure_superuser && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

### Django admin without Shell (Render free tier)

Render’s **Shell** often requires a paid plan. To create an admin user, set these on the **Web Service** → **Environment** (not in git):

| Variable | Example |
|----------|---------|
| `ADMIN_EMAIL` | `you@example.com` |
| `ADMIN_PASSWORD` | A strong one-time password |

Redeploy or restart. Then open `https://<your-service>.onrender.com/admin/` and sign in with that email and password (type the password in the form—it is not filled from env automatically). **Remove `ADMIN_PASSWORD` from the environment afterward** (or change the password in admin) so it is not stored in the dashboard long term.

If that email was already used for a normal signup via the API, the command **promotes** that account to superuser instead of skipping.

Locally you can always run: `python manage.py createsuperuser`

**Render:** In the web service **Settings**, check **Start Command**. If it was set manually, it overrides `render.yaml` and must be:

`python manage.py migrate --noinput && python manage.py ensure_superuser && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

Do **not** rely on `seed_test_data` for data — it is a deprecated no-op kept only so older start commands do not fail deploys. Prefer updating Start Command to remove it entirely:

`python manage.py migrate --noinput && python manage.py ensure_superuser && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

If deploy fails with `Unknown command: 'seed_test_data'`, push the latest code (includes the no-op command) or update Start Command in the Render dashboard, then redeploy.

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
