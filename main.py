import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.database import init_db, SessionLocal
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
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
app.include_router(tourism_router)
app.include_router(creators_router)
app.include_router(admin_router)


# Global Custom 404 Exception Handler
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "API endpoint not found."})
    return templates.TemplateResponse(
        request=request,
        name="base.html",
        context={
            "content": """
            <div class="container" style="padding: 5rem 1rem; text-align: center;">
              <div style="font-size: 4rem; font-weight: 800; color: var(--primary);">404</div>
              <h1 style="font-size: 1.75rem; margin-bottom: 1rem;">Page Not Found</h1>
              <p style="color: var(--text-muted); max-width: 480px; margin: 0 auto 1.5rem;">
                The page or listing you are looking for may have been moved, renamed, or is currently unavailable.
              </p>
              <a href="/" class="btn btn-primary">&larr; Return to Barabanki Connect Home</a>
            </div>
            """
        },
        status_code=404,
    )


# Health Check
@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "district": "Barabanki, Uttar Pradesh",
        "pin_code": "225001",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
