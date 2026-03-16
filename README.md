# ADA Inventory Management Backend

FastAPI backend for the ADA inventory management system.

## Tech Stack
- FastAPI
- SQLAlchemy + Alembic
- PostgreSQL (Docker)
- JWT authentication

## Prerequisites
- Python 3.11+ (3.13 works with the included dependencies)
- Docker Desktop

## 1) Local Environment Setup
From the project root:

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

The default `.env` values are already set for local development.

If your frontend runs on another origin, add it to `BACKEND_CORS_ORIGINS` in `.env` (comma-separated).

## 2) Start Backend (One Command)
From the project root:

```powershell
.\scripts\start-backend.ps1
```

This script will:
1. Verify Docker Desktop is running.
2. Create `.venv` if needed.
3. Install dependencies.
4. Start PostgreSQL via Docker.
5. Run Alembic migrations.
6. Start FastAPI on `http://localhost:8000`.

To skip dependency installation on later runs:

```powershell
.\scripts\start-backend.ps1 -SkipInstall
```

## 3) Frontend Integration
- Backend base URL: `http://localhost:8000`
- API prefix: `/api/v1`
- Health check: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

Typical frontend env value:

```env
VITE_API_URL=http://localhost:8000
```

## 4) Manual Commands (Alternative)
If you do not want to use the script:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker compose up -d postgres
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Troubleshooting
- Docker error about `dockerDesktopLinuxEngine`: start Docker Desktop first.
- CORS errors in browser: add your frontend origin to `BACKEND_CORS_ORIGINS` in `.env` and restart backend.
- Database connection issues: verify `DATABASE_URL` in `.env` and ensure `docker compose ps` shows `postgres` as running.
