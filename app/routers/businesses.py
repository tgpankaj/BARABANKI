import math
from typing import Optional, List
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user_optional, get_current_user
from app.core.security import generate_csrf_token, validate_csrf_token
from app.models.business import Business
from app.schemas.business import BusinessCreate, BusinessOut

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- WEB HTML ROUTES ---

@router.get("/businesses", response_class=HTMLResponse)
def businesses_list_view(
    request: Request,
    page: int = Query(1, ge=1),
    category: Optional[str] = None,
    locality: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    page_size = settings.DEFAULT_PAGE_SIZE
    query = db.query(Business).filter(Business.is_approved == True)

    if category:
        query = query.filter(Business.category == category)
    if locality:
        query = query.filter(Business.locality == locality)
    if q:
        query = query.filter(
            or_(
                Business.name.ilike(f"%{q.strip()}%"),
                Business.description.ilike(f"%{q.strip()}%"),
            )
        )

    total_businesses = query.count()
    total_pages = math.ceil(total_businesses / page_size) or 1
    offset = (page - 1) * page_size

    businesses = query.order_by(Business.is_verified.desc(), Business.rating.desc()).offset(offset).limit(page_size).all()

    return templates.TemplateResponse(
        request=request,
        name="businesses/list.html",
        context={
            "active_page": "businesses",
            "current_user": current_user,
            "businesses": businesses,
            "current_page": page,
            "total_pages": total_pages,
            "current_category": category,
            "current_locality": locality,
            "q": q,
        },
    )


@router.get("/businesses/new", response_class=HTMLResponse)
def business_create_view(
    request: Request,
    current_user = Depends(get_current_user_optional),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    return templates.TemplateResponse(
        request=request,
        name="businesses/create.html",
        context={
            "active_page": "businesses",
            "current_user": current_user,
            "csrf_token": csrf_token,
        },
    )


@router.post("/businesses/new")
def business_create_action(
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    locality: str = Form(...),
    address: str = Form(...),
    description: str = Form(...),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    opening_hours: Optional[str] = Form("10:00 AM - 08:00 PM"),
    csrf_token: str = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        return RedirectResponse(url="/businesses/new", status_code=303)

    from app.seeds.seed_data import slugify
    base_slug = slugify(name)
    slug = base_slug
    counter = 1
    while db.query(Business).filter(Business.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    biz = Business(
        name=name.strip(),
        slug=slug,
        category=category.strip(),
        locality=locality.strip(),
        address=address.strip(),
        description=description.strip(),
        phone=phone.strip() if phone else None,
        email=email.strip() if email else None,
        website=website.strip() if website else None,
        opening_hours=opening_hours.strip() if opening_hours else "10:00 AM - 08:00 PM",
        created_by_id=current_user.id,
        is_verified=False,
        is_approved=True,
        is_demo=False,
    )
    db.add(biz)
    db.commit()
    return RedirectResponse(url=f"/businesses/{slug}", status_code=303)


@router.get("/businesses/{slug}", response_class=HTMLResponse)
def business_detail_view(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    biz = db.query(Business).filter(Business.slug == slug, Business.is_approved == True).first()
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found.")

    return templates.TemplateResponse(
        request=request,
        name="businesses/detail.html",
        context={
            "active_page": "businesses",
            "current_user": current_user,
            "business": biz,
        },
    )


# --- REST API ROUTES ---

@router.get("/api/v1/businesses", response_model=List[BusinessOut])
def api_get_businesses(
    category: Optional[str] = None,
    locality: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Business).filter(Business.is_approved == True)
    if category:
        query = query.filter(Business.category == category)
    if locality:
        query = query.filter(Business.locality == locality)
    return query.order_by(Business.is_verified.desc(), Business.rating.desc()).offset(offset).limit(limit).all()


@router.get("/api/v1/businesses/{slug}", response_model=BusinessOut)
def api_get_business(
    slug: str,
    db: Session = Depends(get_db),
):
    biz = db.query(Business).filter(Business.slug == slug, Business.is_approved == True).first()
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found.")
    return biz


@router.post("/api/v1/businesses", response_model=BusinessOut, status_code=status.HTTP_201_CREATED)
def api_create_business(
    payload: BusinessCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.seeds.seed_data import slugify
    base_slug = slugify(payload.name)
    slug = base_slug
    counter = 1
    while db.query(Business).filter(Business.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    biz = Business(
        name=payload.name,
        slug=slug,
        category=payload.category,
        description=payload.description,
        address=payload.address,
        locality=payload.locality,
        phone=payload.phone,
        email=payload.email,
        website=payload.website,
        opening_hours=payload.opening_hours,
        latitude=payload.latitude,
        longitude=payload.longitude,
        is_approximate_coords=payload.is_approximate_coords,
        image_url=payload.image_url,
        is_demo=payload.is_demo,
        created_by_id=current_user.id,
        is_verified=False,
        is_approved=True,
    )
    db.add(biz)
    db.commit()
    db.refresh(biz)
    return biz
