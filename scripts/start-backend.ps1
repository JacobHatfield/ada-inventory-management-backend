Param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

function Write-Step {
    Param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

Write-Step "Checking Docker availability"
docker info | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker Desktop is not running. Start Docker Desktop, then run this script again."
    exit 1
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Step "Creating virtual environment"
    python -m venv .venv
}

if (-not $SkipInstall) {
    Write-Step "Installing Python dependencies"
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

Write-Step "Starting PostgreSQL container"
docker compose up -d postgres
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to start PostgreSQL container. Confirm Docker Desktop is running and try again."
    exit 1
}

Write-Step "Running database migrations"
.\.venv\Scripts\python.exe -m alembic upgrade head

Write-Step "Starting FastAPI server at http://localhost:8000"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
