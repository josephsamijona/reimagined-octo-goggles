# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JHBridge Translation is a Django-based interpretation/translation services platform connecting clients with interpreters. It handles the full lifecycle: quote requests, assignment management, contract e-signing, payroll, and payments.

- **Python 3.11.8**, **Django 5.1.4**
- **MySQL** database (via `dj-database-url`, env var `MYSQL_URL`)
- **Celery + Redis** for async tasks (email notifications)
- **Resend** as email backend (custom backend at `app/backends/resend_backend.py`)
- **S3-compatible storage** (Backblaze B2) via `django-storages` for media, contracts, signatures
- **DRF + SimpleJWT** for API authentication, plus custom API key auth (`app/api_auth/`)
- Deployed on **Railway** with **Gunicorn + WhiteNoise**

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python manage.py runserver

# Run migrations
python manage.py migrate

# Create migrations after model changes
python manage.py makemigrations app

# Collect static files (for production)
python manage.py collectstatic --noinput

# Run tests
python manage.py test app

# Run a single test
python manage.py test app.tests.TestClassName.test_method_name

# Start Celery worker (requires Redis)
celery -A config worker -l info

# Start Celery beat scheduler
celery -A config beat -l info
```

## Architecture

### Django Settings

- Settings module: `config.settings` (single file, no split by environment)
- Environment detection: `RAILWAY_ENVIRONMENT` env var triggers production logging
- All secrets via `.env` file (`python-dotenv`)
- Custom user model: `AUTH_USER_MODEL = 'app.User'`
- App namespace in URLs: `app_name = 'dbdint'`

### Models — Dual Model System

There are **two separate model layers** in `app/`:

1. **`app/models/`** — The primary, **managed** Django models (migrations run against these). Organized into:
   - `users.py` — `User` (extends `AbstractUser` with roles: CLIENT, INTERPRETER, ADMIN), `Client`, `Interpreter`
   - `languages.py` — `Language`, `InterpreterLanguage`
   - `services.py` — `ServiceType`, `QuoteRequest`, `Quote`, `Assignment`, `PublicQuoteRequest`
   - `communication.py` — `ContactMessage`, `Notification`, `NotificationPreference`, `AssignmentNotification`, `AssignmentFeedback`
   - `finance.py` — `FinancialTransaction`, `ClientPayment`, `InterpreterPayment`, `Payment`, `Expense`, `Reimbursement`, `Deduction`, `PayrollDocument`, `Service`
   - `security.py` — `AuditLog`, `APIKey`, `PGPKey`
   - `documents.py` — `Document`, `SignedDocument`, `InterpreterContractSignature`
   - `contracts.py` — `ContractInvitation`, `ContractTrackingEvent`
   - `reminders.py` — `ContractReminder`

2. **`app/models_v2/`** — **Unmanaged** read-only mirror models (`managed = False`). These map directly to the same DB tables with `App`-prefixed class names (e.g., `AppUser`, `AppAssignment`). Used for separate read contexts.

### Views Structure

Views are organized in `app/views/` by domain, all re-exported through `app/views/__init__.py`:

- `public.py` — Public-facing pages (quote request form, contact)
- `auth.py` — Login/authentication
- `client/` — Client registration (multi-step), dashboard, quotes, profile
- `interpreter/` — Interpreter registration (3-step), dashboard, schedule/calendar, settings
- `assignments.py` — Internal assignment management (accept/reject/start/complete)
- `assignment_responses.py` — Token-based public accept/decline (email links)
- `contracts/` — E-signature wizard, tracking pixels, PDF download, verification
- `earnings.py` — Interpreter earnings and payment views
- `payroll.py` — Payroll document creation and export
- `notifications.py` — Notification management

### Key Patterns

- **User roles** drive access: `CLIENT`, `INTERPRETER`, `ADMIN`. Role-based mixins control view access.
- **Multi-step registration** for both clients (2 steps) and interpreters (3 steps).
- **Token-based assignment responses**: Interpreters receive email links with tokens to accept/decline assignments without logging in.
- **Contract e-signing flow**: Wizard-based contract signing with OTP verification, signature capture (typography/manual), email tracking pixels, and PGP-signed documents.
- **Signals** (`app/signals.py`) trigger Celery tasks for email notifications on model changes (user creation, quote status, assignment status).

### Storage Buckets (`custom_storages.py`)

Multiple S3 storage classes for different content types:
- `MediaStorage` — General media (`jhbridge-documents-prod/media`)
- `ContractStorage` — Signed contracts, versioning enabled (`jhbridge-contracts-prod`)
- `SignatureStorage` — Signature images (`jhbridge-signatures-prod`)
- `AssetStorage` — Public assets, no auth (`jhbridge-assets`)
- `TempStorage` — Temporary uploads with 24h lifecycle (`jhbridge-temp-uploads`)

### Templates

Templates are in `templates/` at project root, organized by:
- `client/` — Client-facing pages
- `trad/` — Interpreter-facing pages (trad = traducteur)
- `emails/` and `notifmail/` — Email notification templates
- `contract/` and `signature_app/` — Contract signing flow
- `public/` — Public pages
- Base templates: `base.html`, `base_client.html`, `base_trad.html`, `intbase.html`

### Environment Variables

Key env vars required (see `.env`):
- `SECRET_KEY`, `MYSQL_URL`, `DEBUG`, `ALLOWED_HOSTS`, `SITE_URL`
- `RESEND_API_KEY` — Email sending
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` — Redis URLs
- `AWS_KEY_ID`, `AWS_KEY_SECRET`, `AWS_S3_REGION_NAME` — S3/B2 storage
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY` — Payments
- `ENCRYPTION_KEY`, `MASTER_KEY` — Data encryption
- `JWT_ACCESS_TOKEN_LIFETIME`, `JWT_REFRESH_TOKEN_LIFETIME`, `JWT_SECRET_KEY`
- `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`

## Code Conventions

- Comments and some variable names are in **French** (the original developer's language). Model verbose names and UI strings use English.
- The codebase uses **class-based views** (Django CBVs) predominantly, with some function-based views for AJAX/API endpoints.
- Forms are in `app/forms.py`, using `crispy-bootstrap5` for rendering.
