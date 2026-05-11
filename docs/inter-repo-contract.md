# Inter-Repo Integration Contract

This document defines stable runtime contracts between repositories.

## Repositories

- Django backend: `jhbridge-backend-django`
- FastAPI backend: `jhbridge-backend-fastapi`
- Frontends: web/mobile repos

## Base URLs

- Django API base: `https://<django-host>`
- FastAPI base: `https://<fastapi-host>`
- Django -> FastAPI uses `FASTAPI_BASE_URL`

## Authentication

### Frontend -> Django

- Header: `Authorization: Bearer <jwt_access_token>`
- Token source: Django auth endpoints (`/api/auth/...`)

### Django -> FastAPI (service-to-service)

- Transport: HTTPS
- Base URL: `FASTAPI_BASE_URL`
- Current calendar sync call:
  - `POST /calendar/sync-assignment`
  - JSON body: `{ "assignment_id": <int> }`
  - Success payload includes: `event_id`, `html_link`

## Expected Endpoint Groups

### Django

- `/api/auth/*`
- `/api/dashboard/*`
- `/api/clients/*`
- `/api/interpreters/*`
- `/api/assignments/*`
- `/api/finance/*`
- `/api/payroll/*`
- `/api/settings/*`

### FastAPI

- `/ai/*`
- `/gmail/*`
- `/calendar/*`
- `/ws/*`
- `/tracking/*`

## Shared Constants Policy

- `shared/` source of truth starts in Django repo.
- FastAPI repo consumes a snapshot copy of `shared/`.
- Any change to role/status/timezone constants must be copied to FastAPI in the same release window.

## Compatibility Rules

- Do not break payload field names without a versioned migration.
- Keep status enums aligned between Django and FastAPI.
- Update this file when adding cross-repo endpoints or auth requirements.
