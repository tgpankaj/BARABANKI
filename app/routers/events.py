from datetime import datetime
import math
from typing import Optional, List
from fastapi import APIRouter, Request, Depends, HTTPException, status, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, utc_now
from app.core.dependencies import get_current_user_optional, get_current_user
from app.core.security import generate_csrf_token, validate_csrf_token
from app.models.event import Event, EventRegistration
from app.models.notification import Notification
from app.schemas.event import EventCreate, EventOut, EventRegistrationCreate, EventRegistrationOut

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- WEB HTML ROUTES ---

@router.get("/events", response_class=HTMLResponse)
def events_list_view(
    request: Request,
    page: int = Query(1, ge=1),
    category: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    page_size = settings.DEFAULT_PAGE_SIZE
    query = db.query(Event).filter(Event.is_approved == True)

    if category:
        query = query.filter(Event.category == category)
    if q:
        query = query.filter(Event.title.ilike(f"%{q.strip()}%"))

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
            "search_query": q,
        },
    )


@router.get("/events/create", response_class=HTMLResponse)
def create_event_view(
    request: Request,
    current_user = Depends(get_current_user_optional),
):
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    return templates.TemplateResponse(
        request=request,
        name="events/create.html",
        context={
            "active_page": "events",
            "current_user": current_user,
            "csrf_token": csrf_token,
        },
    )


@router.post("/events/create")
def event_create_action(
    request: Request,
    title: str = Form(...),
    category: str = Form("Cultural"),
    description: str = Form(...),
    start_date: str = Form(...),
    end_date: Optional[str] = Form(None),
    venue_name: str = Form(...),
    address: str = Form(...),
    locality: Optional[str] = Form("Barabanki"),
    organizer_name: Optional[str] = Form(None),
    organizer_contact: Optional[str] = Form(None),
    registration_link: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    capacity: Optional[str] = Form(None),
    csrf_token: Optional[str] = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        return RedirectResponse(url="/events/create", status_code=303)

    parsed_start_date = None
    if start_date:
        try:
            parsed_start_date = datetime.fromisoformat(start_date.replace(" ", "T"))
        except Exception:
            parsed_start_date = utc_now()
    else:
        parsed_start_date = utc_now()

    parsed_end_date = None
    if end_date:
        try:
            parsed_end_date = datetime.fromisoformat(end_date.replace(" ", "T"))
        except Exception:
            parsed_end_date = None

    from app.seeds.seed_data import slugify
    base_slug = slugify(title) or "event"
    slug = base_slug
    counter = 1
    while db.query(Event).filter(Event.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    org_name = (organizer_name.strip() if organizer_name else None) or current_user.full_name or "Barabanki Resident"

    parsed_capacity = None
    if capacity and capacity.strip().isdigit():
        parsed_capacity = int(capacity.strip())

    event = Event(
        title=title.strip(),
        slug=slug,
        description=description.strip(),
        category=category.strip() if category else "Cultural",
        start_date=parsed_start_date,
        end_date=parsed_end_date,
        venue_name=venue_name.strip(),
        address=address.strip(),
        locality=locality.strip() if locality else "Barabanki",
        organizer_name=org_name,
        organizer_contact=organizer_contact.strip() if organizer_contact else None,
        registration_link=registration_link.strip() if registration_link else None,
        image_url=image_url.strip() if image_url else "https://images.unsplash.com/photo-1511578314322-379afb476865?w=800&q=80",
        capacity=parsed_capacity,
        is_approved=True,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return RedirectResponse(url=f"/events/{slug}", status_code=303)


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

    confirmed_count = db.query(EventRegistration).filter(
        EventRegistration.event_id == event.id,
        EventRegistration.status == "confirmed"
    ).count()

    is_registered = False
    if current_user:
        is_registered = bool(
            db.query(EventRegistration)
            .filter(
                EventRegistration.event_id == event.id,
                EventRegistration.user_id == current_user.id,
                EventRegistration.status == "confirmed"
            )
            .first()
        )

    is_full = bool(event.capacity is not None and confirmed_count >= event.capacity)
    spots_left = max(0, event.capacity - confirmed_count) if event.capacity is not None else None

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    msg = request.query_params.get("msg")

    return templates.TemplateResponse(
        request=request,
        name="events/detail.html",
        context={
            "active_page": "events",
            "current_user": current_user,
            "event": event,
            "is_registered": is_registered,
            "registrations_count": confirmed_count,
            "is_full": is_full,
            "spots_left": spots_left,
            "csrf_token": csrf_token,
            "message": msg,
        },
    )


@router.post("/events/{slug}/register")
def event_register_action(
    slug: str,
    request: Request,
    notes: Optional[str] = Form(None),
    csrf_token: Optional[str] = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    event = db.query(Event).filter(Event.slug == slug, Event.is_approved == True).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    existing = db.query(EventRegistration).filter(
        EventRegistration.event_id == event.id,
        EventRegistration.user_id == current_user.id
    ).first()

    if existing and existing.status == "confirmed":
        return RedirectResponse(url=f"/events/{slug}?msg=You+are+already+registered+for+this+event", status_code=303)

    confirmed_count = db.query(EventRegistration).filter(
        EventRegistration.event_id == event.id,
        EventRegistration.status == "confirmed"
    ).count()

    if event.capacity is not None and confirmed_count >= event.capacity:
        return RedirectResponse(url=f"/events/{slug}?msg=Event+is+already+at+full+capacity", status_code=303)

    if existing:
        existing.status = "confirmed"
        existing.notes = notes.strip() if notes else None
        existing.updated_at = utc_now()
    else:
        reg = EventRegistration(
            event_id=event.id,
            user_id=current_user.id,
            status="confirmed",
            notes=notes.strip() if notes else None,
        )
        db.add(reg)

    notif = Notification(
        recipient_id=current_user.id,
        sender_id=None,
        notification_type="event_reg",
        title="Event Registration Confirmed",
        message=f"You have successfully registered for '{event.title}'.",
        link=f"/events/{event.slug}",
    )
    db.add(notif)
    db.commit()

    return RedirectResponse(url=f"/events/{slug}?msg=Registration+successful!", status_code=303)


@router.post("/events/{slug}/cancel-registration")
def event_cancel_registration_action(
    slug: str,
    request: Request,
    csrf_token: Optional[str] = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    event = db.query(Event).filter(Event.slug == slug, Event.is_approved == True).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    reg = db.query(EventRegistration).filter(
        EventRegistration.event_id == event.id,
        EventRegistration.user_id == current_user.id,
        EventRegistration.status == "confirmed"
    ).first()

    if reg:
        reg.status = "cancelled"
        reg.updated_at = utc_now()
        db.commit()

    return RedirectResponse(url=f"/events/{slug}?msg=Registration+cancelled.", status_code=303)


# --- REST API ROUTES ---

@router.get("/api/v1/events", response_model=List[EventOut])
def api_get_events(
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    query = db.query(Event).filter(Event.is_approved == True)
    if category:
        query = query.filter(Event.category == category)
    events = query.order_by(Event.start_date.asc()).offset(offset).limit(limit).all()

    registered_event_ids = set()
    if current_user:
        user_regs = db.query(EventRegistration.event_id).filter(
            EventRegistration.user_id == current_user.id,
            EventRegistration.status == "confirmed"
        ).all()
        registered_event_ids = {r[0] for r in user_regs}

    result = []
    for ev in events:
        out = EventOut.model_validate(ev)
        out.registrations_count = len([r for r in ev.registrations if r.status == "confirmed"])
        out.is_registered = ev.id in registered_event_ids
        result.append(out)

    return result


@router.get("/api/v1/events/{slug}", response_model=EventOut)
def api_get_event(
    slug: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    event = db.query(Event).filter(Event.slug == slug, Event.is_approved == True).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    out = EventOut.model_validate(event)
    confirmed_regs = [r for r in event.registrations if r.status == "confirmed"]
    out.registrations_count = len(confirmed_regs)
    if current_user:
        out.is_registered = any(r.user_id == current_user.id for r in confirmed_regs)
    else:
        out.is_registered = False
    return out


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
        capacity=payload.capacity,
        is_approved=True,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    out = EventOut.model_validate(event)
    out.registrations_count = 0
    out.is_registered = False
    return out


@router.post("/api/v1/events/{slug}/register", response_model=EventRegistrationOut, status_code=status.HTTP_201_CREATED)
def api_register_event(
    slug: str,
    payload: Optional[EventRegistrationCreate] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = db.query(Event).filter(Event.slug == slug, Event.is_approved == True).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    existing = db.query(EventRegistration).filter(
        EventRegistration.event_id == event.id,
        EventRegistration.user_id == current_user.id
    ).first()

    if existing and existing.status == "confirmed":
        raise HTTPException(status_code=400, detail="You are already registered for this event.")

    confirmed_count = db.query(EventRegistration).filter(
        EventRegistration.event_id == event.id,
        EventRegistration.status == "confirmed"
    ).count()

    if event.capacity is not None and confirmed_count >= event.capacity:
        raise HTTPException(status_code=400, detail="Event has reached maximum capacity.")

    notes = payload.notes if payload else None

    if existing:
        existing.status = "confirmed"
        existing.notes = notes
        existing.updated_at = utc_now()
        reg = existing
    else:
        reg = EventRegistration(
            event_id=event.id,
            user_id=current_user.id,
            status="confirmed",
            notes=notes,
        )
        db.add(reg)

    notif = Notification(
        recipient_id=current_user.id,
        sender_id=None,
        notification_type="event_reg",
        title="Event Registration Confirmed",
        message=f"You have successfully registered for '{event.title}'.",
        link=f"/events/{event.slug}",
    )
    db.add(notif)
    db.commit()
    db.refresh(reg)

    return reg


@router.post("/api/v1/events/{slug}/cancel-registration")
def api_cancel_registration(
    slug: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = db.query(Event).filter(Event.slug == slug, Event.is_approved == True).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    reg = db.query(EventRegistration).filter(
        EventRegistration.event_id == event.id,
        EventRegistration.user_id == current_user.id,
        EventRegistration.status == "confirmed"
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Active registration not found.")

    reg.status = "cancelled"
    reg.updated_at = utc_now()
    db.commit()

    return {"message": "Registration cancelled successfully.", "event_slug": slug}
