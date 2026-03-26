"""FastAPI application entry point."""

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


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
