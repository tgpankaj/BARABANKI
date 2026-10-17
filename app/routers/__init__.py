from app.routers.web import router as web_router
from app.routers.auth import router as auth_router
from app.routers.news import router as news_router
from app.routers.events import router as events_router
from app.routers.businesses import router as businesses_router
from app.routers.jobs import router as jobs_router
from app.routers.education import router as education_router
from app.routers.community import router as community_router
from app.routers.tourism import router as tourism_router
from app.routers.creators import router as creators_router
from app.routers.admin import router as admin_router

__all__ = [
    "web_router",
    "auth_router",
    "news_router",
    "events_router",
    "businesses_router",
    "jobs_router",
    "education_router",
    "community_router",
    "tourism_router",
    "creators_router",
    "admin_router",
]
