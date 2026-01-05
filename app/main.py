from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .database import init_db, seed_sample_data, DATABASE_PATH
from .routes import config_router, responses_router

# Initialize FastAPI app
app = FastAPI(
    title="AI Usage Tracker",
    description="WorkBoard Internal AI Usage and Impact Catalogue",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(config_router)
app.include_router(responses_router)

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"


# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Static page routes
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
    """Serve the configuration management page."""
    return FileResponse(STATIC_DIR / "admin-config.html")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "database": str(DATABASE_PATH)}


# Version endpoint
@app.get("/api/version")
async def get_version():
    """Return version info to verify deployment."""
    return {
        "version": "1.1.0",
        "build": "2024-01-04-capabilities-checkboxes",
        "features": [
            "AI Capabilities as checkboxes",
            "Auto-create capabilities from Other",
            "Auto-create tools from Other"
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
    print("Database initialized")
