# Local Setup (Django Backend Repo)

This guide is for `jhbridge-backend-django` only.

## Prerequisites

- Python 3.11+
- Docker + Docker Compose
- MySQL 8 and Redis 7 (if running without Docker)

## Option A: Docker (recommended)

1. Create your backend `.env` file at repo root.
2. Start stack:

```bash
docker compose -f docker/docker-compose.yml up --build
```

3. Run migrations:

```bash
docker compose -f docker/docker-compose.yml exec django python manage.py migrate
```

4. Access:
- Django: `http://localhost:8000`

## Option B: Local Python

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables (`.env`).
4. Run migrations and server:

```bash
python manage.py migrate
python manage.py runserver
```

## Notes About Split Repositories

- FastAPI now lives in `jhbridge-backend-fastapi`.
- Admin frontend now lives in `jhbridge-web-admin`.
- Customer/interpreter web/mobile apps each have dedicated repositories.
- Django keeps templates/static and the core data model/API.
