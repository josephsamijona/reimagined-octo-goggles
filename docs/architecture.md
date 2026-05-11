# JHBridge Architecture (Post-Split)

## Repository Topology

The platform is now organized as separate sibling repositories:

- `jhbridge-backend-django` (this repository): core business backend
- `jhbridge-backend-fastapi`: AI, Gmail, Calendar sync, realtime endpoints
- `jhbridge-web-admin`: internal admin SPA
- `jhbridge-web-customer`: customer web app (scaffold)
- `jhbridge-web-interpreters`: interpreter web app (scaffold)
- `jhbridge-mobile-customer`: customer mobile app (scaffold)
- `jhbridge-mobile-interpreters`: interpreter mobile app (scaffold)

## This Repository Scope (`jhbridge-backend-django`)

Primary Django assets kept in this repository:

- `app/`: models, API, services, views, admin
- `config/`: Django settings, URL routing, WSGI/ASGI, Celery config
- `templates/`: server-rendered templates
- `static/` and `staticfiles/`: Django static assets
- `scripts/` and `tests/`: support scripts and tests
- `shared/`: shared Python constants/enums (source of truth)

Removed from this repository:

- FastAPI service code (`services/`) -> `jhbridge-backend-fastapi`
- Admin frontend (`adminfrontend/`) -> `jhbridge-web-admin`
- FastAPI/frontend/nginx docker images from this repo

## Runtime Integration

- Django calls FastAPI over HTTP using `FASTAPI_BASE_URL`.
- Frontends call Django API for business operations.
- Frontends call FastAPI only for agent/realtime/integration features.
- `shared/` is copied into FastAPI repo as a controlled snapshot.

## Local Containers (This Repo)

`docker/docker-compose.yml` now runs only:

- `db` (MySQL)
- `redis`
- `django`

FastAPI and frontend containers are managed in their own repositories.
