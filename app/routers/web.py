import math
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.dependencies import get_current_user_optional
from app.core.security import generate_csrf_token, validate_csrf_token
from app.models import (
    Business,
    JobListing,
    NewsArticle,
    Event,
    EducationInstitute,
    CommunityPost,
    TourismSpot,
    ContactMessage,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def home_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    """Home page displaying highlights across all modules."""
    news_articles = db.query(NewsArticle).filter(NewsArticle.is_published == True).order_by(NewsArticle.created_at.desc()).limit(3).all()
    events = db.query(Event).filter(Event.is_approved == True).order_by(Event.start_date.asc()).limit(3).all()
    businesses = db.query(Business).filter(Business.is_approved == True).order_by(Business.is_verified.desc(), Business.rating.desc()).limit(4).all()
    jobs = db.query(JobListing).filter(JobListing.is_active == True, JobListing.is_approved == True).order_by(JobListing.created_at.desc()).limit(3).all()
    tourism_spots = db.query(TourismSpot).limit(4).all()

    stats = {
        "businesses": db.query(Business).count(),
        "news": db.query(NewsArticle).count(),
        "jobs": db.query(JobListing).filter(JobListing.is_active == True).count(),
        "institutes": db.query(EducationInstitute).count(),
    }

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")

    return templates.TemplateResponse(
        request=request,
        name="pages/index.html",
        context={
            "active_page": "home",
            "current_user": current_user,
            "news_articles": news_articles,
            "events": events,
            "businesses": businesses,
            "jobs": jobs,
            "tourism_spots": tourism_spots,
            "stats": stats,
            "csrf_token": csrf_token,
        },
    )


@router.get("/about", response_class=HTMLResponse)
def about_page(
    request: Request,
    current_user = Depends(get_current_user_optional),
):
    """About Barabanki and platform mission page."""
    return templates.TemplateResponse(
        request=request,
        name="pages/about.html",
        context={
            "active_page": "about",
            "current_user": current_user,
        },
    )


@router.get("/contact", response_class=HTMLResponse)
def contact_page(
    request: Request,
    current_user = Depends(get_current_user_optional),
    msg: str = None,
    alert_type: str = "info",
):
    """Civic inquiries and emergency directory page."""
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    return templates.TemplateResponse(
        request=request,
        name="pages/contact.html",
        context={
            "active_page": "contact",
            "current_user": current_user,
            "csrf_token": csrf_token,
            "message": msg,
            "alert_type": alert_type,
        },
    )


@router.post("/contact")
def submit_contact_message(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
    phone: str = Form(None),
    csrf_token: str = Form(None),
    db: Session = Depends(get_db),
):
    """Handle contact inquiry form submission."""
    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        return RedirectResponse(
            url="/contact?msg=Security+token+validation+failed.+Please+try+again.&alert_type=danger",
            status_code=303,
        )

    contact_entry = ContactMessage(
        name=name.strip(),
        email=email.strip(),
        phone=phone.strip() if phone else None,
        subject=subject.strip(),
        message=message.strip(),
    )
    db.add(contact_entry)
    db.commit()

    return RedirectResponse(
        url="/contact?msg=Thank+you!+Your+inquiry+has+been+received+by+district+support.&alert_type=success",
        status_code=303,
    )


@router.get("/search", response_class=HTMLResponse)
def search_page(
    request: Request,
    q: str = "",
    type: str = "all",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    """Universal multi-entity search across all modules."""
    query_str = q.strip()
    results = []

    if query_str:
        pattern = f"%{query_str}%"

        # Search Businesses
        if type in ["all", "businesses"]:
            biz_matches = db.query(Business).filter(
                or_(
                    Business.name.ilike(pattern),
                    Business.description.ilike(pattern),
                    Business.category.ilike(pattern),
                    Business.locality.ilike(pattern),
                )
            ).limit(10).all()
            for b in biz_matches:
                results.append({
                    "entity_type": "Business",
                    "title": b.name,
                    "description": b.description,
                    "subtext": f"{b.category} • {b.locality}",
                    "url": f"/businesses/{b.slug}",
                })

        # Search Jobs
        if type in ["all", "jobs"]:
            job_matches = db.query(JobListing).filter(
                or_(
                    JobListing.title.ilike(pattern),
                    JobListing.description.ilike(pattern),
                    JobListing.company_name.ilike(pattern),
                )
            ).limit(10).all()
            for j in job_matches:
                results.append({
                    "entity_type": "Job",
                    "title": j.title,
                    "description": j.description,
                    "subtext": f"{j.company_name} • {j.job_type}",
                    "url": f"/jobs/{j.slug}",
                })

        # Search News
        if type in ["all", "news"]:
            news_matches = db.query(NewsArticle).filter(
                or_(
                    NewsArticle.title.ilike(pattern),
                    NewsArticle.summary.ilike(pattern),
                    NewsArticle.content.ilike(pattern),
                )
            ).limit(10).all()
            for n in news_matches:
                results.append({
                    "entity_type": "News",
                    "title": n.title,
                    "description": n.summary,
                    "subtext": f"Category: {n.category}",
                    "url": f"/news/{n.slug}",
                })

        # Search Events
        if type in ["all", "events"]:
            event_matches = db.query(Event).filter(
                or_(
                    Event.title.ilike(pattern),
                    Event.description.ilike(pattern),
                    Event.venue_name.ilike(pattern),
                )
            ).limit(10).all()
            for e in event_matches:
                results.append({
                    "entity_type": "Event",
                    "title": e.title,
                    "description": e.description,
                    "subtext": f"Venue: {e.venue_name} ({e.locality})",
                    "url": f"/events/{e.slug}",
                })

        # Search Education
        if type in ["all", "education"]:
            edu_matches = db.query(EducationInstitute).filter(
                or_(
                    EducationInstitute.name.ilike(pattern),
                    EducationInstitute.description.ilike(pattern),
                    EducationInstitute.courses_offered.ilike(pattern),
                )
            ).limit(10).all()
            for edu in edu_matches:
                results.append({
                    "entity_type": "Education",
                    "title": edu.name,
                    "description": edu.description,
                    "subtext": f"{edu.category} • {edu.locality}",
                    "url": f"/education/{edu.slug}",
                })

        # Search Tourism
        if type in ["all", "tourism"]:
            tour_matches = db.query(TourismSpot).filter(
                or_(
                    TourismSpot.name.ilike(pattern),
                    TourismSpot.short_description.ilike(pattern),
                    TourismSpot.historical_background.ilike(pattern),
                )
            ).limit(10).all()
            for t in tour_matches:
                results.append({
                    "entity_type": "Heritage",
                    "title": t.name,
                    "description": t.short_description,
                    "subtext": f"Category: {t.category}",
                    "url": f"/tourism/{t.slug}",
                })

    return templates.TemplateResponse(
        request=request,
        name="pages/search.html",
        context={
            "active_page": "search",
            "current_user": current_user,
            "q": query_str,
            "search_type": type,
            "results": results,
            "results_count": len(results),
        },
    )


@router.get("/privacy", response_class=HTMLResponse)
def privacy_page(
    request: Request,
    current_user = Depends(get_current_user_optional),
):
    """Privacy policy page."""
    return templates.TemplateResponse(
        request=request,
        name="pages/privacy.html",
        context={
            "current_user": current_user,
        },
    )


@router.get("/terms", response_class=HTMLResponse)
def terms_page(
    request: Request,
    current_user = Depends(get_current_user_optional),
):
    """Terms of service page."""
    return templates.TemplateResponse(
        request=request,
        name="pages/terms.html",
        context={
            "current_user": current_user,
        },
    )
