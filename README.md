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
3. If you use the included `render.yaml`, Render creates a **PostgreSQL** database and sets `DATABASE_URL`; the web service runs migrations (`preDeployCommand`) and starts Gunicorn.
4. In the web service, set environment variables if not using Blueprint:
   - `DEBUG=False`
   - `SECRET_KEY` (long random string)
   - `DATABASE_URL` (from Render Postgres **Internal Database URL**)
   - `ALLOWED_HOSTS` optional — if unset on Render, `RENDER_EXTERNAL_HOSTNAME` is used when `RENDER` is set (see `config/settings.py`).

**Build command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`  
**Start command:** `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

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
