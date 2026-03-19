# JHBridge Architecture

## Services Overview

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Frontend   │   │    Django     │   │   FastAPI    │
│  React/CRA   │   │   (Legacy)   │   │  (Services)  │
│  port 3000   │   │   port 8000  │   │  port 8001   │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                   │
       │           ┌──────┴───────┐           │
       │           │    Celery    │           │
       │           │   (Worker)   │           │
       │           └──────┬───────┘           │
       │                  │                   │
       ▼                  ▼                   ▼
  ┌──────────┐    ┌──────────────┐    ┌──────────┐
  │  Nginx   │    │    MySQL     │    │  Redis   │
  │ (prod)   │    │    8.0       │    │  7.x     │
  └──────────┘    └──────────────┘    └──────────┘
```

## Django Application (`app/`)

The main application handling the full business lifecycle:

- **Models** (`app/models/`) — User, Client, Interpreter, Assignment, Quote, Contract, Finance
- **Views** (`app/views/`) — Server-rendered pages for clients, interpreters, and public users
- **API** (`app/api/`) — DRF REST API with JWT auth for the admin frontend
- **Signals** (`app/signals.py`) — Event-driven email notifications via Celery
- **Tasks** (`app/tasks.py`) — Async Celery tasks (emails, reminders)

### Model Organization

| File | Models |
|------|--------|
| `users.py` | User, Client, Interpreter, InterpreterLocation |
| `services.py` | ServiceType, QuoteRequest, Quote, Assignment, PublicQuoteRequest |
| `finance.py` | FinancialTransaction, ClientPayment, InterpreterPayment, Expense, etc. |
| `documents.py` | Document, SignedDocument, InterpreterContractSignature |
| `contracts.py` | ContractInvitation, ContractTrackingEvent |
| `communication.py` | ContactMessage, Notification, NotificationPreference |
| `security.py` | AuditLog, APIKey, PGPKey |

### Authentication

- **Web sessions**: Django session auth with role-based mixins
- **API**: SimpleJWT access/refresh tokens
- **API Keys**: Custom `APIKey` model for service-to-service auth
- **Token links**: Stateless token URLs for interpreter assignment accept/decline via email

## FastAPI Microservice (`services/`)

Handles integrations and real-time features:

- **Gmail** (`services/gmail/`) — Inbox sync, classification, filters
- **Calendar** (`services/calendar_sync/`) — Google Calendar integration
- **AI Agent** (`services/ai_agent/`) — AI-powered assistance
- **Realtime** (`services/realtime/`) — WebSocket connections
- **DB** (`services/db/`) — SQLAlchemy mirrors of Django models (read-only)

## Admin Frontend (`adminfrontend/`)

React SPA (Create React App + Craco) for internal administration:

- **UI**: Radix UI + Tailwind CSS + shadcn/ui components
- **State**: React Hook Form + Zod validation
- **API**: Axios → Django REST API (JWT auth)

## Shared Code (`shared/`)

Pure Python constants and enums shared between Django and FastAPI:

- `constants.py` — Role strings, status strings, timezone mappings
- `enums.py` — Type-safe Enum wrappers

## Storage (S3/Backblaze B2)

| Bucket | Purpose |
|--------|---------|
| `jhbridge-documents-prod` | General media uploads |
| `jhbridge-contracts-prod` | Signed contract PDFs (versioned) |
| `jhbridge-signatures-prod` | Signature images |
| `jhbridge-assets` | Public assets (no auth) |
| `jhbridge-temp-uploads` | Temporary files (24h lifecycle) |

## Docker Setup

See `docker/docker-compose.yml` for local development and `docker/docker-compose.prod.yml` for production overrides with nginx reverse proxy.
