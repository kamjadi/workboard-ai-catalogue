from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .database import init_db, seed_sample_data, create_initial_admin, DATABASE_PATH
from .routes import config_router, responses_router, export_import_router, auth_router
from . import crud

# Initialize FastAPI app
app = FastAPI(
    title="AI Usage Tracker",
    description="WorkBoard Internal AI Usage and Impact Catalog",
    version="2.0.0"
)

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"

SESSION_COOKIE_NAME = "session_token"

# Public paths that don't require authentication
PUBLIC_PATHS = {
    "/login",
    "/health",
    "/api/auth/login",
    "/api/version",
}

# Paths that start with these prefixes are public
PUBLIC_PREFIXES = [
    "/static/",
]

# Admin-only paths (user role cannot access)
ADMIN_PATHS = {
    "/users",
    "/config",
}

ADMIN_API_PREFIXES = [
    "/api/auth/users",
]


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Check if path is public
        if path in PUBLIC_PATHS:
            return await call_next(request)

        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Check for session cookie
        token = request.cookies.get(SESSION_COOKIE_NAME)
        session = crud.get_session(token) if token else None

        if not session:
            # For API requests, return 401
            if path.startswith("/api/"):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Not authenticated"}
                )
            # For page requests, redirect to login
            return RedirectResponse(url="/login", status_code=302)

        # Check admin-only paths
        if path in ADMIN_PATHS:
            if session.get('role') != 'admin':
                return RedirectResponse(url="/", status_code=302)

        for prefix in ADMIN_API_PREFIXES:
            if path.startswith(prefix):
                if session.get('role') != 'admin':
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Admin access required"}
                    )

        # Extend session on activity
        crud.extend_session(token)

        # Add session info to request state for use in routes
        request.state.session = session

        return await call_next(request)


# Add auth middleware
app.add_middleware(AuthMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (export_import_router first to ensure /responses/export matches before /responses/{id})
app.include_router(auth_router)
app.include_router(config_router)
app.include_router(export_import_router)
app.include_router(responses_router)


# Mount static files (after middleware so it's protected by default, but we whitelist /static/ in PUBLIC_PREFIXES)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Login page (public)
@app.get("/login")
async def login_page():
    """Serve the login page."""
    return FileResponse(STATIC_DIR / "login.html")


# Protected page routes
@app.get("/")
async def overview_page():
    """Serve the overview/preview dashboard."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/form")
async def form_page():
    """Serve the intake form."""
    return FileResponse(STATIC_DIR / "form.html")


@app.get("/instructions")
async def instructions_page():
    """Serve the instructions preview form."""
    return FileResponse(STATIC_DIR / "instructions.html")


@app.get("/dashboard")
async def dashboard_page():
    """Serve the live dashboard."""
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/admin")
async def admin_page():
    """Serve the admin page for managing entries."""
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/config")
async def config_page():
    """Serve the configuration management page (admin only)."""
    return FileResponse(STATIC_DIR / "admin-config.html")


@app.get("/users")
async def users_page():
    """Serve the user management page (admin only)."""
    return FileResponse(STATIC_DIR / "users.html")


# Health check (public)
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "database": str(DATABASE_PATH)}


# Version endpoint (public for deployment verification)
@app.get("/api/version")
async def get_version():
    """Return version info to verify deployment."""
    return {
        "version": "2.0.0",
        "build": "2025-01-08-authentication",
        "features": [
            "User authentication",
            "Admin user management",
            "Session-based security",
            "JSON export/import"
        ]
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()

    # Seed with sample data if database is empty
    from .database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM functions")
    count = cursor.fetchone()[0]
    conn.close()

    if count == 0:
        seed_sample_data()
        print("Database seeded with sample data")

    # Create initial admin user if no users exist
    create_initial_admin()

    # Cleanup expired sessions
    crud.cleanup_expired_sessions()

    print("Database initialized")
