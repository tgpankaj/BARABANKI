from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user_optional
from app.models.creator import CreatorProfile

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/creators", response_class=HTMLResponse)
def creators_list_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    creators = db.query(CreatorProfile).all()
    return templates.TemplateResponse(
        request=request,
        name="creators/list.html",
        context={
            "active_page": "creators",
            "current_user": current_user,
            "creators": creators,
        },
    )


@router.get("/api/v1/creators")
def api_get_creators(
    db: Session = Depends(get_db),
):
    creators = db.query(CreatorProfile).all()
    results = []
    for c in creators:
        results.append({
            "id": c.id,
            "name": c.user.full_name if c.user else "Artisan",
            "title": c.title,
            "craft_category": c.craft_category,
            "bio": c.bio,
            "skills": c.skills,
            "portfolio_url": c.portfolio_url,
            "is_featured": c.is_featured,
        })
    return results
