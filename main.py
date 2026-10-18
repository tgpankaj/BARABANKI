import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.database import init_db, SessionLocal, get_db
from sqlalchemy.orm import Session
from app.models.user import User
from app.seeds.seed_data import seed
from app.routers import (
    web_router,
    auth_router,
    news_router,
    events_router,
    businesses_router,
    jobs_router,
    education_router,
    community_router,
    tourism_router,
    creators_router,
    admin_router,
    civic_issues_router,
    notifications_router,
    advertising_router,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("barabanki_connect")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database schema exists & seed if initial run
    logger.info("Initializing database schema...")
    init_db()

    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.email == "admin@barabanki.local").first()
        if not admin_exists:
            logger.info("Empty database detected. Seeding authentic Barabanki baseline data...")
            seed()
    finally:
        db.close()

    yield
    logger.info("Application shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Barabanki Connect: Modern Civic, Business, Education, Jobs, Community & Heritage Platform for District Barabanki, UP.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Response Compression for Mobile / Slow Connections
app.add_middleware(GZipMiddleware, minimum_size=500)

# Security Headers & Static Caching Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(self), camera=(), microphone=()"

    # Static Assets Cache-Control
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = f"public, max-age={settings.STATIC_CACHE_MAX_AGE}"

    # Content-Security-Policy
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https: blob:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'self';"
    )
    response.headers["Content-Security-Policy"] = csp
    return response


# Mount Static Assets
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")


# Include All Web & API Routers
app.include_router(web_router)
app.include_router(auth_router)
app.include_router(news_router)
app.include_router(events_router)
app.include_router(businesses_router)
app.include_router(jobs_router)
app.include_router(education_router)
app.include_router(community_router)
app.include_router(civic_issues_router)
app.include_router(notifications_router)
app.include_router(tourism_router)
app.include_router(creators_router)
app.include_router(admin_router)
app.include_router(advertising_router)



# Global Custom 404 Exception Handler
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "API endpoint not found."})
    return templates.TemplateResponse(
        request=request,
        name="errors/404.html",
        context={"request": request},
        status_code=404,
    )


# Global Custom 500 Exception Handler
@app.exception_handler(500)
async def custom_500_handler(request: Request, exc):
    logger.error(f"Internal server error: {exc}", exc_info=True)
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please contact the administrator."},
        )
    return templates.TemplateResponse(
        request=request,
        name="errors/500.html",
        context={"request": request},
        status_code=500,
    )


# Health Check with Active Database Probe
@app.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unreachable: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "environment": settings.ENVIRONMENT,
        "district": "Barabanki, Uttar Pradesh",
        "pin_code": "225001",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
