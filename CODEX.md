# CODEX.md — JHBridge Translation Platform

> Comprehensive technical reference for AI agents working on this codebase.
> Last updated: 2026-05-01

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Backend Features — Django](#3-backend-features--django)
4. [Backend Features — FastAPI Microservice](#4-backend-features--fastapi-microservice)
5. [Admin Frontend — React SPA](#5-admin-frontend--react-spa)
6. [Client-Facing Templates — Django](#6-client-facing-templates--django)
7. [Data Models Reference](#7-data-models-reference)
8. [API Endpoints Reference](#8-api-endpoints-reference)
9. [Key Workflows](#9-key-workflows)
10. [File Map](#10-file-map)

---

## 1. Project Overview

**JHBridge Translation** is a full-stack interpretation/translation services platform connecting clients with interpreters. It handles the complete lifecycle: quote requests, interpreter matching, assignment dispatching, contract e-signing, payroll, payments, and AI-powered email processing.

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend (primary) | Django 5.1.4, Python 3.11.8, DRF + SimpleJWT |
| Backend (microservice) | FastAPI, SQLAlchemy async, Google ADK |
| Admin Frontend | React 19, Vite 8, Tailwind v4, shadcn/ui |
| Client/Interpreter UI | Django templates, vanilla JS, glassmorphism CSS |
| Database | MySQL (shared between Django and FastAPI) |
| Task Queue | Celery + Redis |
| Email | Resend (custom backend), Gmail API (FastAPI) |
| Storage | S3-compatible (Backblaze B2) via django-storages |
| Real-time | WebSocket (FastAPI), Redis pub/sub |
| AI | Google ADK (Gemini) multi-agent orchestration |
| Deployment | Railway, Gunicorn + WhiteNoise |

### Ports

| Service | Port | Purpose |
|---------|------|---------|
| Django | 8000 | Main backend API + template rendering |
| FastAPI | 8001 | AI agent, Gmail, calendar, real-time |
| Vite dev | 3000 | Admin frontend (dev mode) |

---

## 2. Architecture

```
                    ┌──────────────────────────────┐
                    │     Admin Frontend (React)    │
                    │  Vite :3000 → /api proxy      │
                    └──────────┬───────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │  Django :8000 │  │ FastAPI :8001│  │  WebSocket   │
   │  REST API     │  │  AI Agent    │  │  Real-time   │
   │  Templates    │  │  Gmail       │  │  Tracking    │
   │  Celery tasks │  │  Calendar    │  │  Notifications│
   └──────┬───────┘  └──────┬───────┘  └──────────────┘
          │                  │
          ▼                  ▼
   ┌──────────────────────────────┐
   │         MySQL Database       │
   │   (Django writes, both read) │
   └──────────────────────────────┘
          │
   ┌──────┴────────┐
   │  Redis         │  ← Celery broker + WebSocket pub/sub
   └───────────────┘
          │
   ┌──────┴────────┐
   │  S3 (B2)      │  ← Documents, contracts, signatures
   └───────────────┘
```

### Three Client Interfaces

1. **Admin Frontend** (React SPA at `/adminfrontend/`) — Full command center for admin staff
2. **Client Templates** (Django, extends `base_client.html`) — Quote requests, assignment tracking
3. **Interpreter Templates** (Django, extends `intbase.html`) — Mission management, earnings, schedule

---

## 3. Backend Features — Django

### 3.1 Authentication & Security

| Feature | Files | Description |
|---------|-------|-------------|
| JWT Auth | `api/viewsets/auth.py`, `api/services/auth_service.py` | Email+password → JWT tokens (SimpleJWT) |
| MFA (TOTP) | `models/auth_security.py`, `api/viewsets/auth.py` | TOTP setup, QR code, verification, backup codes |
| WebAuthn/Passkeys | `api/services/auth_service.py` | FIDO2 registration/authentication (YubiKey, biometrics) |
| Step-Up Auth | `api/viewsets/auth.py` | Re-verify before sensitive operations |
| Device Trust | `models/auth_security.py` | 30-day trusted device tokens to skip MFA |
| Brute-Force Protection | `models/auth_security.py` (LoginAttempt) | 5 attempts, 15min lockout window |
| API Keys | `models/security.py` | Named API keys with expiration for external integrations |
| PGP Document Signing | `models/security.py` | PGP keys for signed contract PDFs |
| Audit Logging | `models/security.py` (AuditLog) | User, action, model, changes JSON, IP |
| Admin MFA | `admin/mfa.py`, `admin/mfa_urls.py` | Django admin MFA enforcement |

### 3.2 User & Role Management

| Feature | Files | Description |
|---------|-------|-------------|
| Custom User Model | `models/users.py` | Extends AbstractUser with roles: CLIENT, INTERPRETER, ADMIN |
| Client Profiles | `models/users.py` (Client) | Company, address, preferences, notes |
| Interpreter Profiles | `models/users.py` (Interpreter) | Languages, certifications, rates, availability, banking info |
| Multi-Step Registration | `views/client/`, `views/interpreter/` | Client (2-step), Interpreter (3-step) |
| Role-Based Access | `api/permissions.py` | IsAdminUser, IsClientUser, IsInterpreterUser, IsAdminOrReadOnly |

### 3.3 Quote & Assignment Management

| Feature | Files | Description |
|---------|-------|-------------|
| Public Quote Requests | `models/services.py` (PublicQuoteRequest) | Unauthenticated form, admin processing |
| Client Quote Requests | `models/services.py` (QuoteRequest) | PENDING → PROCESSING → QUOTED → ACCEPTED/REJECTED/EXPIRED |
| Formal Quotes | `models/services.py` (Quote) | DRAFT → SENT → ACCEPTED/REJECTED/EXPIRED/CANCELLED |
| Assignment Lifecycle | `models/services.py` (Assignment) | PENDING → CONFIRMED → IN_PROGRESS → COMPLETED/CANCELLED/NO_SHOW |
| Token-Based Responses | `views/assignment_responses.py` | Email links for accept/decline without login |
| Google Calendar Sync | `signals.py`, `api/services/calendar_service.py` | Auto-sync assignments to shared Google Calendar |
| Interpreter Matching | `api/services/matching_service.py` | Match by language, availability, location |

### 3.4 Contract E-Signing

| Feature | Files | Description |
|---------|-------|-------------|
| Contract Invitations | `models/contracts.py` | INV-YEAR-XXXXX numbering, token-based access |
| Signing Wizard | `views/contracts/` | Multi-step: review → sign → OTP verify |
| Signature Methods | `models/documents.py` | Upload image, typed text, manual drawing (canvas) |
| OTP Verification | `contract/otp.html` | Email-based one-time code before signing |
| Tracking Events | `models/contracts.py` (ContractTrackingEvent) | Full audit trail: email sent → opened → clicked → signed |
| Email Tracking Pixels | Templates | Open tracking via pixel images |
| PGP-Signed PDFs | `models/security.py` | Contracts signed with PGP keys |
| Contract Reminders | `models/reminders.py` | 3-level escalation (3d, 7d, 14d+block) |

### 3.5 Finance & Payments

| Feature | Files | Description |
|---------|-------|-------------|
| Client Payments | `models/finance.py` (ClientPayment) | 30+ payment methods, status tracking, proof upload |
| Interpreter Payments | `models/finance.py` (InterpreterPayment) | Scheduled payments, processing, completion |
| Financial Ledger | `models/finance.py` (FinancialTransaction) | INCOME/EXPENSE/INTERNAL transactions |
| Invoices | `models/finance.py` (Invoice) | DRAFT → SENT → PAID/OVERDUE, PDF generation, reminders |
| Expenses | `models/finance.py` (Expense) | OPERATIONAL/ADMIN/MARKETING/SALARY/TAX/OTHER |
| Payroll Documents | `models/finance.py` (PayrollDocument, Service) | Company + interpreter details, line items |
| Reimbursements | `models/finance.py` (Reimbursement) | 10 types (transport, parking, toll, meal, etc.) |
| Deductions | `models/finance.py` (Deduction) | 9 types (advance, equipment, penalties, tax, etc.) |
| Paystub Generator | `admin/paystub.py` | Admin UI for generating paystubs with PDF export |
| Batch Paystubs | `admin/paystub.py` | Generate stubs for multiple interpreters |
| Earnings Reports | `admin/paystub.py` | Summary reports by interpreter/period |
| Invoice Maker | `admin/invoice_maker.py` | Client invoice generation |

### 3.6 Communication & Notifications

| Feature | Files | Description |
|---------|-------|-------------|
| Email Notifications | `tasks.py`, `signals.py` | Celery tasks triggered by model signals |
| In-App Notifications | `models/communication.py` (Notification) | 7 types, read status, optional link |
| Notification Preferences | `models/communication.py` | Per-user email/SMS/in-app toggles, frequency settings |
| Contact Messages | `models/communication.py` | Website contact form processing |
| Assignment Feedback | `models/communication.py` | 1-5 star ratings with comments |
| Email Logging | `models/communication.py` (EmailLog) | Gmail integration with AI classification |

### 3.7 Onboarding Pipeline

| Feature | Files | Description |
|---------|-------|-------------|
| Onboarding Invitations | `models/onboarding.py` | ONB-YEAR-XXXXX numbering, multi-phase lifecycle |
| Phase Tracking | `models/onboarding.py` | INVITED → EMAIL_OPENED → WELCOME → ACCOUNT → PROFILE → CONTRACT → COMPLETED |
| Tracking Events | `models/onboarding.py` | Audit trail for each phase transition |
| Admin Send UI | `admin/onboarding.py` | Send/resend/void invitations |

### 3.8 Marketing & CRM

| Feature | Files | Description |
|---------|-------|-------------|
| Lead Tracking | `models/marketing.py` (Lead) | Source, stage pipeline (NEW → CONTACTED → CONVERTED/LOST) |
| Campaign Management | `models/marketing.py` (Campaign) | Channel, budget/spent, leads/conversions tracking |
| Lead-to-Client Conversion | `models/marketing.py` | Link leads to converted clients |

### 3.9 AI Agent Queue

| Feature | Files | Description |
|---------|-------|-------------|
| Queue Items | `models/agent.py` (AgentQueueItem) | AI-proposed actions awaiting admin approval |
| Action Types | `models/agent.py` | CREATE_ASSIGNMENT, CREATE_QUOTE_REQUEST, SEND_ONBOARDING, RECORD_INVOICE, etc. |
| Approval Workflow | `api/viewsets/agent_queue.py` | Approve → execute, reject with reason |
| Audit Trail | `models/agent.py` (AgentAuditLog) | Full execution logging |

### 3.10 Storage & Infrastructure

| Feature | Files | Description |
|---------|-------|-------------|
| 7 S3 Buckets | `custom_storages.py` | Media, contracts (versioned), signatures, assets, temp (24h lifecycle) |
| Resend Email Backend | `app/backends/resend_backend.py` | Custom Django email backend |
| S3 Backup Command | `management/commands/backup_to_s3.py` | dumpdata → S3 with progress bar |
| Calendar Backfill | `management/commands/backfill_calendar.py` | Retroactive Google Calendar sync |

---

## 4. Backend Features — FastAPI Microservice

Location: `services/` directory. Runs on port 8001.

### 4.1 AI Email Processing

| Feature | Endpoint | Description |
|---------|----------|-------------|
| Email Classification | `POST /ai/classify` | Categorize emails: INTERPRETATION, QUOTE, HIRING, PAYMENT, etc. |
| Batch Classification | `POST /ai/classify-batch` | Retroactively classify unprocessed EmailLog records |
| Interpreter Matching | `POST /ai/match` | AI-powered best-match by language, date, location, service type |
| Quote Estimation | `POST /ai/estimate` | Calculate service quotes based on duration, language, urgency |
| CV Analysis | `POST /ai/analyze-cv` | Parse resumes: extract languages, certifications, experience |
| Action Suggestions | `POST /ai/suggest` | AI-suggested actions for incoming emails |
| Reply Generation | `POST /ai/reply` | Draft professional email responses |
| Conversational Chat | `POST /ai/chat` | Session-based chat with ADK agent |
| Streaming Chat | `POST /ai/chat/stream` | SSE streaming for real-time chat responses |

### 4.2 Agent Queue (Human-in-the-Loop)

| Feature | Endpoint | Description |
|---------|----------|-------------|
| List Queue | `GET /ai/queue` | Paginated queue with status/category filters |
| Pending Count | `GET /ai/queue/count` | Badge count for notification UI |
| Approve Action | `POST /ai/queue/{id}/approve` | Admin approves → system executes |
| Reject Action | `POST /ai/queue/{id}/reject` | Admin rejects with reason |
| Process Email | `POST /ai/process-email` | Full pipeline: classify → extract → match → enqueue |
| Process Unread | `POST /ai/process-unread` | Batch process all unread emails |
| Audit Log | `GET /ai/audit-log` | Execution audit trail |

### 4.3 Gmail Integration

| Feature | Endpoint | Description |
|---------|----------|-------------|
| Auth Status | `GET /gmail/auth-status` | OAuth2 configuration check |
| Inbox | `GET /gmail/inbox` | Emails with filters (category, priority, read, processed) |
| Read/Unread | `PATCH /gmail/messages/{id}/read` | Toggle read status |
| Mark Processed | `PATCH /gmail/messages/{id}/processed` | Mark as processed |
| Get Message | `GET /gmail/messages/{id}` | Full email content from Gmail API |
| Send Email | `POST /gmail/send` | Send from operations inbox |
| Reply | `POST /gmail/reply/{id}` | Reply to existing thread |
| Force Sync | `GET /gmail/sync` | Trigger immediate sync (normally every 2 min) |
| Search | `GET /gmail/search` | Gmail query syntax search |

### 4.4 Google Calendar

| Feature | Endpoint | Description |
|---------|----------|-------------|
| List Events | `GET /calendar/events` | Events in date range |
| Sync Assignment | `POST /calendar/sync-assignment` | Push single assignment to calendar |
| Delete Event | `DELETE /calendar/event/{id}` | Remove calendar event |
| Sync Today | `POST /calendar/sync-all-today` | Batch sync today's assignments |

### 4.5 Real-Time (WebSocket)

| Channel | Endpoint | Description |
|---------|----------|-------------|
| Notifications | `WS /ws/notifications` | General user notifications |
| Live Tracking | `WS /ws/live-tracking` | Interpreter GPS updates |
| Assignments | `WS /ws/assignment-updates` | Assignment status changes |
| Email Updates | `WS /ws/email-updates` | New/classified/replied emails |
| GPS Update | `POST /tracking/update` | Save + broadcast interpreter location |
| Live Positions | `GET /tracking/live` | All active interpreter positions |

### 4.6 ADK Multi-Agent System

8 specialized sub-agents orchestrated by a root agent:

| Agent | Purpose |
|-------|---------|
| `email_classifier` | Categorize incoming emails |
| `interpreter_matcher` | Find best interpreter for requirements |
| `quote_estimator` | Calculate service quotes |
| `cv_analyzer` | Parse candidate resumes |
| `assignment_request_processor` | Extract assignment details from emails |
| `invoice_processor` | Parse invoice data |
| `payslip_extractor` | Extract payslip information |
| `reply_generator` | Draft professional email responses |

---

## 5. Admin Frontend — React SPA

Location: `adminfrontend/src/`. Vite dev server on port 3000.

### 5.1 Modules (Pages)

| Module | Component | Description |
|--------|-----------|-------------|
| Dashboard | `DashboardModule.jsx` | KPIs, alerts, revenue chart (12mo), today's missions, payroll KPIs, quote pipeline |
| AI Agent | `AIAgentModule.jsx` | Gmail inbox, email classification, AI queue review, streaming chat interface |
| Dispatch | `DispatchModule.jsx` | Assignment CRUD, table/kanban/calendar/map views, bulk actions, conflict checking, Google Calendar sync |
| Hiring | `HiringModule.jsx` | Onboarding pipeline (Kanban by phase), invitation CRUD, resend/void/advance |
| Interpreters | `InterpretersModule.jsx` | Grid/table/map views, filters, bulk actions (block/unblock/message), detail modals |
| Clients & Sales | `ClientsModule.jsx` | Client list, detail drawer, finance/history tabs, quote requests, invoicing |
| Finance | `FinanceModule.jsx` | Invoices, expenses, revenue analytics (by service/client/language), P&L |
| Payroll | `PayrollModule.jsx` | Pay stubs, payment processing, earnings summaries, tax documents, batch operations |
| Settings | `SettingsModule.jsx` | WebAuthn credential management, passkey registration, company settings |

### 5.2 Auth Pages

| Page | Component | Description |
|------|-----------|-------------|
| Login | `LoginPage.jsx` | Email/password + passkey option, device trust checkbox |
| MFA Verify | `MFAPage.jsx` | TOTP code entry |
| MFA Setup | `MFASetupPage.jsx` | QR code display, backup codes |

### 5.3 Modal Components

| Modal | File | Description |
|-------|------|-------------|
| Create/Edit Assignment | `MissionFormModal.jsx` | Timezone-aware datetimes, Google Places autocomplete |
| Assignment Detail | `MissionDetailModal.jsx` | View details, timeline, notes |
| Interpreter Detail | `InterpreterDetailModal.jsx` | Profile, performance, banking, payment history |
| Edit Interpreter | `EditInterpreterModal.jsx` | Edit profile fields |
| Client Form | `ClientFormModal.jsx` | Create/edit client |
| Pay Stub | `PaymentStubModal.jsx` | View/download/send individual PDF |
| Batch Stubs | `BatchStubModal.jsx` | Multi-interpreter stub generation |
| Manual Stub | `ManualStubModal.jsx` | Stub for non-registered payee |
| Tax Summary | `TaxSummaryModal.jsx` | Earnings summary PDF for tax filing |
| Reassign | `ReassignModal.jsx` | Reassign interpreter to mission |
| Onboarding Invite | `OnboardingInviteModal.jsx` | Send/resend onboarding invitation |

### 5.4 Services (API Layer)

| Service | File | Key Methods |
|---------|------|-------------|
| Auth | `authService.js` | login, mfaSetup/Verify, webauthn*, stepUp*, deviceTrust, logout |
| Dashboard | `dashboardService.js` | getKPIs, getAlerts, getRevenueChart, getTodayMissions |
| Dispatch | `dispatchService.js` | CRUD, confirm/start/cancel/complete, reassign, conflict check, export CSV |
| Interpreters | `interpreterService.js` | list, block/unblock, performance, banking, bulk actions, map data |
| Clients | `clientsService.js` | CRUD, history, invoices, quote requests/quotes |
| Finance | `financeService.js` | invoices, expenses, revenue analytics, P&L |
| Payroll | `payrollService.js` | stubs, batch stubs, earnings summary, PDF download |
| Hiring | `hiringService.js` | invitations CRUD, resend/void/advance, pipeline view |
| AI Agent | `agentService.js` | Gmail ops, classify, match, estimate, queue review, streaming chat |

### 5.5 State Management

| Context | File | State |
|---------|------|-------|
| AuthContext | `context/AuthContext.jsx` | user, authPhase, mfaSetupData, error |

**Auth Phases:** `loading → login → mfa_setup → mfa_verify → authenticated`

**Custom Hooks with Caching:**
- `useDashboard.js` — 60s TTL, stale-while-revalidate
- `useAssignments.js` — 30s TTL, paginated with filters
- `useInterpreters.js` — 30s TTL, paginated with filters
- `usePayroll.js` — 30s TTL, parallel fetching

### 5.6 Key Frontend Patterns

- **Module switching** via state (not React Router), keyboard shortcuts `1-9`
- **Global search** via Command Palette (Cmd/Ctrl+K)
- **Dark mode** toggle (class-based on `<html>`)
- **Token refresh** on 401 with request queuing in Axios interceptor
- **Bulk actions** via selected rows → action dropdown
- **Google Maps** integration for dispatch map and interpreter locations
- **SSE streaming** for AI chat responses

---

## 6. Client-Facing Templates — Django

167 HTML templates total across the template-based interface.

### 6.1 Client Interface (extends `base_client.html`)

| Template | Feature |
|----------|---------|
| `client/home.html` | Dashboard: stats, upcoming assignments, recent quotes, payments |
| `client/quote_list.html` | Quote listing with filters (status, type, date), grid/list view |
| `client/quote_create.html` | 3-step form: Contact Info → Service Details → Location |
| `client/quote_detail.html` | Single quote with timeline |
| `client/assignment_detail.html` | Assignment details, interpreter info |
| `client/profile.html` | Profile management |
| `client/change_password.html` | Password change |
| `client/setnotifications.html` | Notification preferences |
| `client/auth/step1.html` | Registration step 1 (personal) |
| `client/auth/step2.html` | Registration step 2 (company) |

**Design:** Green (#4CAF50) primary, dark background, glassmorphism, mobile-first bottom nav.

### 6.2 Interpreter Interface (extends `intbase.html`)

| Template | Feature |
|----------|---------|
| `trad/home.html` | Dashboard: stats, today's/upcoming assignments, earnings |
| `trad/assignments.html` | Pending/confirmed/completed assignments |
| `trad/assignment_detail.html` | Full assignment details |
| `trad/schedule.html` | Calendar view |
| `trad/earnings.html` | Payment history, earnings summary |
| `trad/settings.html` | Profile, language prefs, availability |
| `trad/notifications.html` | Notification center |
| `trad/auth/step1-3.html` | 3-step registration (personal → languages → location) |
| `interpreter/int_main.html` | Legacy dashboard (older base template) |
| `interpreter/stats.html` | Performance metrics |
| `interpreter/contract_required.html` | Contract signing required notice |
| `interpreter/account_blocked.html` | Blocked account notice |

**Design:** Blue (#003366, #0066CC) primary, teal accents, dark theme, glassmorphism.

### 6.3 Public Pages (no auth required)

| Template | Feature |
|----------|---------|
| `public/quote_request_form.html` | 3-step multi-step form with validation |
| `public/quote_request_success.html` | Submission confirmation |
| `public/contact.html` | Contact form |
| `public/contact_success.html` | Contact confirmation |

### 6.4 Contract E-Signing Flow

| Template | Step |
|----------|------|
| `signature_app/reviewcontract.html` | Review contract terms |
| `signature_app/signmethode.html` | Choose signature method (type/draw) |
| `signatures/interface.html` | Canvas-based signature drawing |
| `signature_app/confirmationsign.html` | Confirm signature |
| `contract/otp.html` | OTP email verification |
| `contract/wizard.html` | Wizard container |
| `contract/successclickone.html` | Success state |
| `signature_app/expiredlinks.html` | Expired link notice |

### 6.5 Email Templates (44 templates)

**Categories:**
- Assignment lifecycle (new, confirmed, declined, completed, cancelled, no-show)
- Quote request status changes (pending, processing, quoted, accepted, rejected, expired)
- Onboarding invitations (initial + 5 resend variants based on stuck phase)
- Contract notifications (invitation, confirmation, 3 reminder levels, suspension)
- Payroll stubs
- Welcome emails (client + interpreter)

**Base template:** `emails/base_email.html` — Dark blue theme (#0D2557), responsive 2-column grid.

### 6.6 In-App Notification Templates (29 templates)

Organized by domain:
- `notif/assignments/` (10) — Offers, confirmations, cancellations, reminders, proximity checks
- `notif/billing/` (8) — Invoices, payouts, quotes, statements, tax forms
- `notif/compliance/` (3) — Document approved/expiring/rejected
- `notif/auth/` (2) — Welcome, password reset
- `notif/security/` (2) — Login alerts, password changes
- `notif/system/` (2) — New user, general notices

### 6.7 Admin Templates

| Template | Feature |
|----------|---------|
| `admin/mfa/setup.html` | MFA setup with QR + passkey registration |
| `admin/mfa/verify.html` | Code verification |
| `admin/mfa/settings.html` | Manage MFA methods |
| `admin/mfa/backup_codes.html` | Download/print backup codes |
| `admin/paystub/generator.html` | Paystub creator with assignment selection |
| `admin/paystub/batch.html` | Batch paystub generation |
| `admin/paystub/earnings_report.html` | Earnings analytics |
| `admin/invoice/maker.html` | Client invoice generator |
| `admin/onboarding/send_invitation.html` | Send onboarding invitations |

---

## 7. Data Models Reference

### Core Models (40+)

**Users & Roles:**
- `User` — AbstractUser + role (CLIENT/INTERPRETER/ADMIN)
- `Client` — Company, address, preferences
- `Interpreter` — Languages, certs, rates, availability, banking

**Services:**
- `ServiceType` — Translation types
- `Language`, `InterpreterLanguage` — Language proficiency tracking
- `QuoteRequest` — PENDING → PROCESSING → QUOTED → ACCEPTED/REJECTED/EXPIRED
- `Quote` — DRAFT → SENT → ACCEPTED/REJECTED/EXPIRED/CANCELLED
- `Assignment` — PENDING → CONFIRMED → IN_PROGRESS → COMPLETED/CANCELLED/NO_SHOW
- `PublicQuoteRequest` — Unauthenticated submissions

**Finance:**
- `FinancialTransaction` — Master ledger (UUID, type, amount)
- `ClientPayment` — 30+ payment methods, status lifecycle
- `InterpreterPayment` — Scheduled payments to interpreters
- `Invoice` — Client invoices with PDF, reminders, status tracking
- `Expense`, `Reimbursement`, `Deduction` — Cost tracking
- `PayrollDocument`, `Service` — Payroll with line items

**Documents & Contracts:**
- `Document` — Generic doc storage with SHA-256 hash, PGP signature
- `SignedDocument` — Signature metadata (type, position, author)
- `InterpreterContractSignature` — Full e-sign tracking (status, method, banking, OTP)
- `ContractInvitation` — Invitation lifecycle with tokens
- `ContractTrackingEvent` — Audit trail per invitation
- `ContractReminder` — 3-level escalation

**Communication:**
- `Notification` — 7 types, read status
- `NotificationPreference` — Per-user toggles
- `ContactMessage`, `AssignmentFeedback`, `AssignmentNotification`
- `EmailLog` — Gmail sync with AI classification

**Security:**
- `AuditLog` — Action, model, changes JSON, IP
- `APIKey` — Named keys with expiration
- `PGPKey` — Document signing keys
- `MFADevice` — TOTP secrets
- `MFABackupCode` — One-time codes (SHA-256 hashed)
- `WebAuthnCredential` — FIDO2 credentials
- `TrustedDevice` — 30-day device tokens
- `LoginAttempt` — Brute-force tracking

**Marketing:**
- `Lead` — Sales pipeline (NEW → CONTACTED → CONVERTED/LOST)
- `Campaign` — Marketing channels, budget/spend tracking

**AI Agent:**
- `AgentQueueItem` — Proposed actions (9 types), approval workflow
- `AgentAuditLog` — Execution audit trail

**Onboarding:**
- `OnboardingInvitation` — Multi-phase lifecycle (7 phases)
- `OnboardingTrackingEvent` — Phase transition audit

---

## 8. API Endpoints Reference

### Django REST API (`/api/v1/`)

**Authentication:**
```
POST   /auth/login/
POST   /auth/token/refresh/
GET    /auth/me/
POST   /auth/logout/
POST   /auth/mfa/setup/
POST   /auth/mfa/verify/
POST   /auth/mfa/backup-codes/
POST   /auth/step-up/
GET    /auth/step-up/status/
POST   /auth/step-up/passkey/options/
POST   /auth/step-up/passkey/verify/
POST   /auth/webauthn/register/options/
POST   /auth/webauthn/register/verify/
POST   /auth/webauthn/login/options/
POST   /auth/webauthn/login/verify/
GET    /auth/webauthn/credentials/
DELETE /auth/webauthn/credentials/{id}/
POST   /auth/device/trust/
```

**Dashboard:**
```
GET    /dashboard/kpis/
GET    /dashboard/alerts/
GET    /dashboard/revenue-chart/
GET    /dashboard/today-missions/
GET    /dashboard/payroll-kpis/
GET    /dashboard/quote-pipeline-summary/
```

**Core Resources (CRUD via DRF router):**
```
/assignments/          — Full CRUD + confirm, start, cancel, complete, export
/interpreters/         — List, detail, update
/clients/              — Full CRUD
/quote-requests/       — List, detail, create
/quotes/               — List, detail
/public-quotes/        — List
```

**Finance & Payroll:**
```
/finance/              — Client/interpreter payments, summary, reconciliation
/payroll/              — CRUD, PDF export, add service/reimbursement/deduction
```

**Other:**
```
/onboarding/           — Invitation CRUD + workflow actions
/notifications/        — List + mark_as_read
/leads/                — Lead CRUD
/campaigns/            — Campaign CRUD
/marketing-analytics/  — Conversion rates, ROI
/settings/company/     — GET/PUT company info
/service-types/        — CRUD
/languages/            — CRUD
/api-keys/             — CRUD + rotate, disable
/audit-logs/           — Read-only
/agent-queue/          — Queue CRUD + approve, reject, execute
/agent-audit/          — Read-only audit logs
```

### FastAPI Endpoints (port 8001)

```
POST   /ai/classify              — Email classification
POST   /ai/classify-batch        — Batch classify
POST   /ai/match                 — Interpreter matching
POST   /ai/estimate              — Quote estimation
POST   /ai/analyze-cv            — CV parsing
POST   /ai/suggest               — Action suggestions
POST   /ai/reply                 — Reply generation
POST   /ai/chat                  — Conversational chat
POST   /ai/chat/stream           — SSE streaming chat
GET    /ai/queue                 — List queue items
GET    /ai/queue/count           — Pending count
POST   /ai/queue/{id}/approve    — Approve action
POST   /ai/queue/{id}/reject     — Reject action
POST   /ai/process-email         — Full AI pipeline
POST   /ai/process-unread        — Batch process unread
GET    /ai/audit-log             — Agent audit trail

GET    /gmail/auth-status        — OAuth2 check
GET    /gmail/inbox              — Email list with filters
PATCH  /gmail/messages/{id}/read — Toggle read
PATCH  /gmail/messages/{id}/processed — Mark processed
GET    /gmail/messages/{id}      — Full email content
POST   /gmail/send               — Send email
POST   /gmail/reply/{id}         — Reply to thread
GET    /gmail/sync               — Force sync
GET    /gmail/search             — Gmail search

GET    /calendar/events          — List events
POST   /calendar/sync-assignment — Sync single assignment
DELETE /calendar/event/{id}      — Delete event
POST   /calendar/sync-all-today  — Sync today's assignments

WS     /ws/notifications         — General notifications
WS     /ws/live-tracking         — GPS updates
WS     /ws/assignment-updates    — Assignment status changes
WS     /ws/email-updates         — Email inbox events

POST   /tracking/update          — Save GPS location
GET    /tracking/live            — All active positions
GET    /health                   — Health check
```

---

## 9. Key Workflows

### 9.1 Assignment Lifecycle

```
Admin creates assignment
    │
    ▼
PENDING ──── email sent to interpreter (with accept/decline token links)
    │
    ├── Interpreter clicks ACCEPT link ──→ CONFIRMED (payment created)
    │       │
    │       ├── Mission day ──→ IN_PROGRESS
    │       │       │
    │       │       └── Mark complete ──→ COMPLETED (timestamp recorded)
    │       │
    │       └── Client cancels ──→ CANCELLED (payment voided)
    │
    ├── Interpreter clicks DECLINE link ──→ CANCELLED
    │
    └── No response ──→ remains PENDING (reminders sent)
```

### 9.2 Contract E-Signing

```
Admin creates OnboardingInvitation
    │
    ▼
Email sent with token link
    │
    ▼
Interpreter clicks link → review contract
    │
    ▼
Choose signature method (type / draw / upload)
    │
    ▼
Create signature → confirm → OTP email verification
    │
    ▼
InterpreterContractSignature = SIGNED
    │
    ▼
Company rep counter-signs → is_fully_signed = True → COMPLETED
    │
    ▼
PGP-signed PDF generated → stored in S3
```

### 9.3 AI Email Processing Pipeline

```
Gmail sync (every 2 min) → EmailLog table
    │
    ▼
POST /ai/process-email
    │
    ├── Classify (category, priority, confidence)
    ├── Extract structured data
    ├── Match interpreter (if assignment-related)
    │
    ▼
AgentQueueItem created (PENDING)
    │
    ├── Admin APPROVES → action executed (create assignment, send onboarding, etc.)
    │       │
    │       └── AgentAuditLog recorded
    │
    └── Admin REJECTS with reason → logged
```

### 9.4 Quote Request Flow

```
Public form OR client dashboard
    │
    ▼
QuoteRequest created (PENDING)
    │
    ▼
Admin processes → creates Quote (DRAFT → SENT)
    │
    ▼
Client reviews → ACCEPTED / REJECTED / expires
    │
    ▼
If accepted → Assignment created → interpreter matching
```

### 9.5 Onboarding Pipeline

```
Admin creates OnboardingInvitation
    │
    ▼
INVITED → email sent
    │
    ▼
EMAIL_OPENED → link clicked
    │
    ▼
WELCOME_VIEWED → account creation
    │
    ▼
ACCOUNT_CREATED → profile completion
    │
    ▼
PROFILE_COMPLETED → contract signing
    │
    ▼
CONTRACT_STARTED → COMPLETED (or VOIDED/EXPIRED)
```

---

## 10. File Map

```
legacy/
├── config/                          # Django settings & URL config
│   ├── settings.py                  # Single settings file (env-based)
│   ├── urls.py                      # Root URL config (/admin, /api/v1/, /)
│   └── celery.py                    # Celery app configuration
│
├── app/                             # Main Django application
│   ├── models/                      # Managed models (14 files, 40+ models)
│   │   ├── users.py                 # User, Client, Interpreter
│   │   ├── languages.py             # Language, InterpreterLanguage
│   │   ├── services.py              # ServiceType, QuoteRequest, Quote, Assignment
│   │   ├── communication.py         # Notification, Feedback, EmailLog
│   │   ├── finance.py               # Payments, Invoices, Expenses, Payroll
│   │   ├── documents.py             # Document, SignedDocument, ContractSignature
│   │   ├── contracts.py             # ContractInvitation, TrackingEvent
│   │   ├── security.py              # AuditLog, APIKey, PGPKey
│   │   ├── auth_security.py         # MFA, WebAuthn, TrustedDevice, LoginAttempt
│   │   ├── marketing.py             # Lead, Campaign
│   │   ├── onboarding.py            # OnboardingInvitation, TrackingEvent
│   │   ├── agent.py                 # AgentQueueItem, AgentAuditLog
│   │   └── reminders.py             # ContractReminder
│   │
│   ├── models_v2/                   # Unmanaged read-only mirrors (App-prefixed)
│   │
│   ├── views/                       # Django views (CBV + FBV)
│   │   ├── public.py                # Quote request, contact
│   │   ├── auth.py                  # Login, registration routing
│   │   ├── client/                  # Client dashboard, quotes, profile
│   │   ├── assignments.py           # Assignment management
│   │   ├── assignment_responses.py  # Token-based email accept/decline
│   │   ├── contracts/               # E-signature wizard flow
│   │   ├── earnings.py              # Interpreter earnings
│   │   ├── payroll.py               # Payroll generation/export
│   │   ├── notifications.py         # Notification management
│   │   ├── onboarding.py            # Onboarding workflow
│   │   └── errors.py               # Custom error pages
│   │
│   ├── api/                         # DRF REST API
│   │   ├── urls.py                  # API URL routing
│   │   ├── permissions.py           # Role-based permissions
│   │   ├── filters.py               # DRF filter backends
│   │   ├── pagination.py            # Pagination config
│   │   ├── throttling.py            # Rate limiting
│   │   ├── viewsets/                # API viewsets (15+ files)
│   │   │   ├── auth.py              # Auth + MFA + WebAuthn (18 endpoints)
│   │   │   ├── assignments.py       # Assignment CRUD + actions
│   │   │   ├── clients.py           # Client CRUD
│   │   │   ├── interpreters.py      # Interpreter list/detail/update
│   │   │   ├── quotes.py            # Quote/QuoteRequest management
│   │   │   ├── dashboard.py         # KPIs, alerts, charts
│   │   │   ├── finance.py           # Payment management
│   │   │   ├── payroll.py           # Payroll CRUD + PDF
│   │   │   ├── onboarding.py        # Onboarding workflow
│   │   │   ├── notifications.py     # Notification list/read
│   │   │   ├── marketing.py         # Leads, campaigns, analytics
│   │   │   ├── agent_queue.py       # AI queue management
│   │   │   ├── audit.py             # Audit logs
│   │   │   └── settings.py          # Service types, languages, API keys
│   │   │
│   │   ├── serializers/             # DRF serializers (12 files, 40+)
│   │   │   ├── auth.py, assignments.py, users.py, services.py,
│   │   │   ├── finance.py, dashboard.py, onboarding.py,
│   │   │   ├── communication.py, marketing.py, settings.py,
│   │   │   └── contracts.py
│   │   │
│   │   └── services/                # Business logic layer (9 files)
│   │       ├── auth_service.py      # Auth, MFA, WebAuthn, step-up, device trust
│   │       ├── assignment_service.py # Payment creation/cancellation
│   │       ├── analytics_service.py # KPIs, revenue, alerts
│   │       ├── invoice_service.py   # Invoice generation, PDF, reminders
│   │       ├── payroll_service.py   # Payroll docs, line items, PDF
│   │       ├── matching_service.py  # Interpreter matching algorithm
│   │       ├── calendar_service.py  # Google Calendar sync
│   │       └── reference_service.py # Reference data lookups
│   │
│   ├── admin/                       # Django admin customization
│   │   ├── users.py, services.py, finance.py, documents.py,
│   │   ├── contracts.py, communication.py, languages.py,
│   │   ├── security.py, marketing.py, onboarding.py,
│   │   ├── mfa.py, mfa_urls.py, middleware.py,
│   │   ├── paystub.py, invoice_maker.py, utils.py
│   │   └── __init__.py
│   │
│   ├── signals.py                   # post_save triggers (6 signals)
│   ├── tasks.py                     # Celery async tasks (4+ tasks)
│   ├── forms.py                     # Django forms (crispy-bootstrap5)
│   ├── api_auth/                    # Custom API key authentication
│   ├── backends/                    # Custom backends
│   │   └── resend_backend.py        # Resend email backend
│   └── management/commands/         # Management commands
│       ├── backup_to_s3.py          # DB backup to S3
│       └── backfill_calendar.py     # Retroactive calendar sync
│
├── services/                        # FastAPI microservice
│   ├── main.py                      # App factory + lifespan
│   ├── config.py                    # Settings from env vars
│   ├── requirements.txt             # FastAPI dependencies
│   ├── ai_agent/                    # AI endpoints
│   │   ├── router.py               # /ai classify, match, estimate, chat
│   │   └── queue_router.py          # /ai/queue approve, reject, process
│   ├── gmail/                       # Gmail integration
│   │   ├── router.py               # /gmail inbox, send, reply, sync
│   │   ├── client.py               # Gmail API wrapper
│   │   └── sync.py                 # Background sync loop
│   ├── calendar_sync/              # Google Calendar
│   │   ├── router.py               # /calendar endpoints
│   │   ├── client.py               # Calendar API wrapper
│   │   └── mapper.py               # Assignment → Calendar event
│   ├── realtime/                    # WebSocket & tracking
│   │   ├── router.py               # /ws endpoints
│   │   ├── tracking.py             # /tracking GPS endpoints
│   │   ├── manager.py              # Connection management
│   │   ├── broadcaster.py          # Redis pub/sub
│   │   └── events.py               # Channel & event types
│   ├── db/                          # Database layer
│   │   ├── database.py             # Async SQLAlchemy setup
│   │   ├── models.py               # ORM models (read-only mirrors)
│   │   └── queries.py              # Reusable queries
│   ├── adk_agents/                  # Google ADK agents
│   │   ├── jhbridge_agent/         # Root orchestrator
│   │   ├── sub_agents/             # 8 specialized agents
│   │   └── tools/                  # Gmail, calendar, assignment tools
│   └── schemas/                     # Pydantic models
│       ├── ai.py, email.py, queue.py, calendar.py, tracking.py
│
├── adminfrontend/                   # React admin SPA
│   ├── src/
│   │   ├── App.jsx                  # Main shell, module routing
│   │   ├── components/
│   │   │   ├── auth/               # LoginPage, MFAPage, MFASetupPage
│   │   │   ├── modules/            # 9 module components
│   │   │   ├── modals/             # 11 modal components
│   │   │   ├── shared/             # UIComponents, SearchPalette, Toast
│   │   │   └── ui/                 # 60+ shadcn/ui components
│   │   ├── context/AuthContext.jsx  # Auth state management
│   │   ├── hooks/                   # useDashboard, useAssignments, etc.
│   │   ├── services/               # 8 API service files
│   │   ├── lib/                    # utils.js, webauthn.js
│   │   └── data/mockData.js        # Navigation, status config
│   ├── vite.config.js               # Vite + Tailwind v4 + proxy
│   └── package.json                 # React 19, Vite 8, shadcn, Radix
│
├── templates/                       # Django HTML templates (167 files)
│   ├── layouts/                     # Base templates
│   ├── client/                      # Client pages + auth (14 files)
│   ├── trad/                        # Interpreter pages + auth (18 files)
│   ├── interpreter/                 # Legacy interpreter pages
│   ├── public/                      # Public pages (5 files)
│   ├── emails/                      # Email templates (44 files)
│   ├── notif/                       # In-app notifications (29 files)
│   ├── admin/                       # Admin templates (13 files)
│   ├── contract/                    # E-sign wizard
│   ├── signature_app/               # Signature interface
│   ├── accounts/                    # Auth pages
│   ├── pages/                       # Error/success pages
│   ├── payroll/                     # Payroll documents
│   └── onboarding/                  # Onboarding workflow
│
├── static/                          # Static assets
│   ├── css/                         # 19 CSS files
│   ├── js/                          # 9+ JS files
│   └── images/                      # Logos, icons
│
├── custom_storages.py               # 7 S3 storage classes
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Container config
├── entrypoint.sh                    # Startup script
└── manage.py                        # Django management
```

---

## Environment Variables

```bash
# Django Core
SECRET_KEY, DEBUG, ALLOWED_HOSTS, SITE_URL
MYSQL_URL                              # MySQL connection string

# Email
RESEND_API_KEY                         # Resend email service

# Celery
CELERY_BROKER_URL, CELERY_RESULT_BACKEND  # Redis URLs

# S3/B2 Storage
AWS_KEY_ID, AWS_KEY_SECRET, AWS_S3_REGION_NAME

# Payments
STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY

# Security
ENCRYPTION_KEY, MASTER_KEY
JWT_ACCESS_TOKEN_LIFETIME, JWT_REFRESH_TOKEN_LIFETIME, JWT_SECRET_KEY

# CORS
CORS_ALLOWED_ORIGINS, CSRF_TRUSTED_ORIGINS

# FastAPI Service
GOOGLE_API_KEY                         # Gemini AI
DJANGO_API_URL                         # Backend URL for service calls
DJANGO_ADMIN_TOKEN                     # Pre-generated JWT for service-to-service
GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH  # OAuth2 credentials
CALENDAR_ID                            # Google Calendar ID

# Frontend
VITE_API_URL                           # Backend API base URL
VITE_AGENT_URL                         # FastAPI service URL (default: localhost:8001)
VITE_GOOGLE_MAPS_API_KEY               # Google Maps
```

---

## Code Conventions

- Comments and some variable names are in **French** (original developer's language)
- `trad` = "traducteur" (translator/interpreter)
- Model verbose names and UI strings use **English**
- **Class-based views** (CBVs) are predominant, with some FBVs for AJAX
- Forms use **crispy-bootstrap5**
- Frontend uses **shadcn/ui** component library with Tailwind v4
- API follows RESTful conventions with DRF ViewSets
- Service layer pattern separates business logic from views
- Signals + Celery for event-driven async email notifications
