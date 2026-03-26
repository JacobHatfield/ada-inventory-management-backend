# ADA Inventory Management - Backend

Enterprise-grade inventory management backend built with FastAPI, SQLAlchemy, and PostgreSQL. This system provides a robust API for user authentication, core inventory operations, stock management with audit trails, and automated alerts.

## Features

### Core Features
- **User Management**: Secure registration and JWT-based authentication.
- **Inventory CRUD**: Create, Read, Update, and Delete inventory items with full validation.
- **User-Item Association**: Personalised inventory for each authenticated user.

### Intermediate Features
- **Stock Level Management**: Increment and decrement stock with negative value prevention.
- **Search and Filter**: Search by name and filter by category or stock status.
- **High Coverage**: Over 90% test coverage for all core operations and domain logic.

### Advanced Features
- **Password Reset**: Full secure email-based workflow with SendGrid integration.
- **Low-Stock Alerts**: Automatic notification system for items hitting user-defined thresholds.
- **Audit History**: Persistent trail of all stock changes.
- **Categorisation**: Flexible item grouping and filtering.
- **Pagination**: Performance-optimised server-side pagination for large datasets.
- **CI/CD Pipeline**: Automated quality enforcement via GitHub Actions.

## Architecture

The project follows a strict Three-Layer Architecture for clear separation of concerns:

1.  **API Layer (`app/api`)**: FastAPI routers, request/response models, and endpoint handlers.
2.  **Service Layer (`app/services`)**: Business logic, validation rules, and orchestration of domain operations.
3.  **Data Layer (`app/models`)**: SQLAlchemy ORM models and database schema definitions.

### Tech Stack
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL
- **Authentication**: JWT (python-jose)
- **Quality Tools**: Black, isort, Ruff (linting)
- **CI/CD**: GitHub Actions

## Setup and Installation

### Prerequisites
- Python 3.11+ (3.13 recommended)
- Docker Desktop (for PostgreSQL)

### Step-by-Step Installation

1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd ada-inventory-management-backend
    ```

2.  **Environment Configuration**:
    Copy the example environment file and update the values:
    ```bash
    cp .env.example .env
    ```

3.  **Start with the Automation Script (Recommended)**:
    This script handles virtual environment creation, dependency installation, Docker startup, and migrations:
    ```powershell
    .\scripts\start-backend.ps1
    ```

4.  **Manual Start (Alternative)**:
    ```bash
    # Create and activate virtual environment
    python -m venv .venv
    source .venv/bin/activate  # or .\.venv\Scripts\activate on Windows

    # Install dependencies
    pip install -r requirements.txt

    # Start database
    docker-compose up -d postgres

    # Run migrations
    alembic upgrade head

    # Run server
    uvicorn app.main:app --reload
    ```

## Authentication Details

- **Implementation**: JWT (JSON Web Tokens) following OAuth2 password flow with HTTPBearer.
- **Security**:
    - Passwords are hashed using argon2-cffi.
    - Protected routes require a valid Bearer token in the Authorisation header.
    - Token expiration is configurable via ACCESS_TOKEN_EXPIRE_MINUTES.

## Testing

The project maintains a 94% test coverage across 401 test cases.

### Running Tests
```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=app --cov-report=term-missing
```

## CI/CD Pipeline

The GitHub Actions pipeline (`.github/workflows/ci.yml`) automatically runs on every push and pull request to main:
- **Format Check**: Enforces black formatting.
- **Import Check**: Enforces isort organisation.
- **Lint Check**: Enforces ruff standards.
- **Test Enforcement**: Fails the build if any test fails or if coverage drops below 80%.

## Deployment on Render

This project is configured for easy deployment on **Render** using the included `render.yaml` blueprint.

### Automatic Deployment (Blueprint)

1.  Commit and push all changes to your GitHub repository.
2.  Log in to [Render](https://dashboard.render.com/).
3.  Click **New +** and select **Blueprint**.
4.  Connect your GitHub repository.
5.  Render will automatically detect the `render.yaml` file and set up:
    -   A **PostgreSQL database** (free tier).
    -   A **Python Web Service** running the FastAPI backend.
    -   Environment variables (`DATABASE_URL`, `SECRET_KEY`, etc.).
6.  Click **Apply** to start the deployment.

### Manual Deployment (Web Service)

If you prefer to configure the service manually:

1.  Create a new **PostgreSQL** database on Render.
2.  Create a new **Web Service** and connect your repository.
3.  **Language**: `Python`
4.  **Build Command**: `pip install -r requirements.txt`
5.  **Start Command**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`
6.  Add the following **Environment Variables**:
    -   `DATABASE_URL`: Your Render Internal Database URL.
    -   `SECRET_KEY`: A secure random string.
    -   `ALGORITHM`: `HS256`
    -   `ACCESS_TOKEN_EXPIRE_MINUTES`: `60`
    -   `BACKEND_CORS_ORIGINS`: Your frontend URL (e.g., `https://your-app.onrender.com`).

## Generative AI Statement

I have used Generative AI within my work to help with planning, debugging and documentation drafting in my work. Any use for this was critically checked and manually amended by myself. 
