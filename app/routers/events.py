import math
from typing import Optional, List
from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user_optional, get_current_user
from app.models.event import Event
from app.schemas.event import EventCreate, EventOut

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- WEB HTML ROUTES ---

@router.get("/events", response_class=HTMLResponse)
def events_list_view(
    request: Request,
    page: int = Query(1, ge=1),
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    page_size = settings.DEFAULT_PAGE_SIZE
    query = db.query(Event).filter(Event.is_approved == True)

    if category:
        query = query.filter(Event.category == category)

    total_events = query.count()
    total_pages = math.ceil(total_events / page_size) or 1
    offset = (page - 1) * page_size

    events = query.order_by(Event.start_date.asc()).offset(offset).limit(page_size).all()

    return templates.TemplateResponse(
        request=request,
        name="events/list.html",
        context={
            "active_page": "events",
            "current_user": current_user,
            "events": events,
            "current_page": page,
            "total_pages": total_pages,
            "current_category": category,
        },
    )


@router.get("/events/{slug}", response_class=HTMLResponse)
def event_detail_view(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    event = db.query(Event).filter(Event.slug == slug, Event.is_approved == True).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    return templates.TemplateResponse(
        request=request,
        name="events/detail.html",
        context={
            "active_page": "events",
            "current_user": current_user,
            "event": event,
        },
    )


# --- REST API ROUTES ---

@router.get("/api/v1/events", response_model=List[EventOut])
def api_get_events(
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Event).filter(Event.is_approved == True)
    if category:
        query = query.filter(Event.category == category)
    return query.order_by(Event.start_date.asc()).offset(offset).limit(limit).all()


@router.get("/api/v1/events/{slug}", response_model=EventOut)
def api_get_event(
    slug: str,
    db: Session = Depends(get_db),
):
    event = db.query(Event).filter(Event.slug == slug, Event.is_approved == True).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    return event


@router.post("/api/v1/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def api_create_event(
    payload: EventCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.seeds.seed_data import slugify
    slug = slugify(payload.title)

    event = Event(
        title=payload.title,
        slug=slug,
        description=payload.description,
        category=payload.category,
        start_date=payload.start_date,
        end_date=payload.end_date,
        venue_name=payload.venue_name,
        address=payload.address,
        locality=payload.locality,
        latitude=payload.latitude,
        longitude=payload.longitude,
        is_approximate_coords=payload.is_approximate_coords,
        organizer_name=payload.organizer_name,
        organizer_contact=payload.organizer_contact,
        registration_link=payload.registration_link,
        image_url=payload.image_url,
        is_approved=True,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
