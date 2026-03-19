# Local Development Setup

## Prerequisites

- Python 3.11+
- Node.js 20+ and Yarn
- Docker and Docker Compose (or local MySQL 8.0 + Redis 7)

## Option A: Docker (recommended)

1. **Clone and configure environment:**

   ```bash
   git clone <repo-url> && cd legacy
   cp .env.example .env  # Edit with your credentials
   ```

2. **Start all services:**

   ```bash
   docker compose -f docker/docker-compose.yml up --build
   ```

3. **Run migrations (first time):**

   ```bash
   docker compose -f docker/docker-compose.yml exec django python manage.py migrate
   ```

4. **Verify:**
   - Django: http://localhost:8000/admin/
   - FastAPI: http://localhost:8001/docs
   - Frontend: http://localhost:3000

## Option B: Local (without Docker)

1. **Python environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Environment variables:**

   ```bash
   cp .env.example .env
   # Set MYSQL_URL, CELERY_BROKER_URL, etc.
   ```

3. **Database:**

   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. **Run Django:**

   ```bash
   python manage.py runserver
   ```

5. **Run Celery (separate terminal):**

   ```bash
   celery -A config worker -l info
   ```

6. **Run Frontend (separate terminal):**

   ```bash
   cd adminfrontend
   yarn install
   yarn start
   ```

## Required Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `MYSQL_URL` | MySQL connection URL |
| `DEBUG` | `True` for development |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `SITE_URL` | Base URL (e.g., `http://localhost:8000`) |
| `RESEND_API_KEY` | Resend email API key |
| `CELERY_BROKER_URL` | Redis URL for Celery broker |
| `CELERY_RESULT_BACKEND` | Redis URL for Celery results |
| `AWS_KEY_ID` | S3/B2 access key |
| `AWS_KEY_SECRET` | S3/B2 secret key |
| `AWS_S3_REGION_NAME` | S3 region |

## Running Tests

```bash
python manage.py test app
```
