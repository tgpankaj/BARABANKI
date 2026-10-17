from typing import List
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user_optional
from app.models.tourism import TourismSpot
from app.schemas.tourism import TourismSpotOut

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- WEB HTML ROUTES ---

@router.get("/tourism", response_class=HTMLResponse)
def tourism_list_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    spots = db.query(TourismSpot).all()
    return templates.TemplateResponse(
        request=request,
        name="tourism/list.html",
        context={
            "active_page": "tourism",
            "current_user": current_user,
            "spots": spots,
        },
    )


@router.get("/tourism/{slug}", response_class=HTMLResponse)
def tourism_detail_view(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    spot = db.query(TourismSpot).filter(TourismSpot.slug == slug).first()
    if not spot:
        raise HTTPException(status_code=404, detail="Heritage landmark not found.")

    return templates.TemplateResponse(
        request=request,
        name="tourism/detail.html",
        context={
            "active_page": "tourism",
            "current_user": current_user,
            "spot": spot,
        },
    )


# --- REST API ROUTES ---

@router.get("/api/v1/tourism", response_model=List[TourismSpotOut])
def api_get_tourism_spots(
    db: Session = Depends(get_db),
):
    return db.query(TourismSpot).all()


@router.get("/api/v1/tourism/{slug}", response_model=TourismSpotOut)
def api_get_tourism_spot(
    slug: str,
    db: Session = Depends(get_db),
):
    spot = db.query(TourismSpot).filter(TourismSpot.slug == slug).first()
    if not spot:
        raise HTTPException(status_code=404, detail="Spot not found.")
    return spot
