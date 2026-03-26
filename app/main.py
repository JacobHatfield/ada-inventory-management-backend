"""FastAPI application entry point."""

import os
from alembic.config import Config
from alembic import command
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import auth, categories, email, inventory, users
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
)

# Run database migrations on startup to ensure tables exist
# This is more robust than relying on shell commands in Render
try:
    # Path to alembic.ini (it's in the project root, one level up from app/)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(base_dir, "alembic.ini")
    
    if os.path.exists(ini_path):
        alembic_cfg = Config(ini_path)
        # Ensure script_location is absolute to avoid relative path issues
        alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
        command.upgrade(alembic_cfg, "head")
        print("Successfully applied database migrations on startup.")
    else:
        print(f"Warning: alembic.ini not found at {ini_path}. Skipping startup migrations.")
except Exception as e:
    print(f"Startup migration error: {e}")
    # In production, we might want to log this properly

# Configure CORS
origins = settings.cors_origins_list
# IMPORTANT: If allow_credentials is True, allow_origins cannot be ["*"]
allow_credentials = True
if "*" in origins:
    allow_credentials = False # Or we could explicitly check for "*" and handle it

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler to debug 500 errors in production."""
    import traceback
    error_detail = str(exc)
    stack_trace = traceback.format_exc()
    
    # In production, we should log this instead of returning it,
    # but for debugging the current issue, we'll return it if DEBUG is True.
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "error": error_detail if settings.DEBUG else None,
            "traceback": stack_trace if settings.DEBUG else None,
            "path": request.url.path
        },
        # Ensure CORS headers are included even in the error response
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true" if allow_credentials else "false"
        }
    )

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(email.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")

@app.get("/")
def read_root():
    """Root endpoint for health check and welcome message."""
    return {
        "message": "Welcome to the Ada Inventory Management API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
