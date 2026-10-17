from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user_optional, require_moderator_or_admin, require_admin
from app.core.security import generate_csrf_token
from app.models.user import User
from app.models.business import Business
from app.models.job import JobListing
from app.models.news import NewsArticle
from app.models.event import Event
from app.models.education import EducationInstitute
from app.models.community import CommunityPost
from app.models.report import Report

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- WEB HTML ADMIN ROUTES ---

@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    if current_user.role not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Administrative privileges required.")

    stats = {
        "total_users": db.query(User).count(),
        "businesses": db.query(Business).count(),
        "jobs": db.query(JobListing).count(),
        "news": db.query(NewsArticle).count(),
        "events": db.query(Event).count(),
        "institutes": db.query(EducationInstitute).count(),
        "posts": db.query(CommunityPost).count(),
        "pending_reports": db.query(Report).filter(Report.status == "pending").count(),
    }

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_admin")

    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "request": request,
            "active_page": "admin",
            "current_user": current_user,
            "stats": stats,
            "csrf_token": csrf_token,
        },
    )


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    if not current_user or current_user.role not in ["admin", "moderator"]:
        return RedirectResponse(url="/auth/login", status_code=303)

    users = db.query(User).order_by(User.created_at.desc()).all()
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_admin")

    return templates.TemplateResponse(
        request=request,
        name="admin/users.html",
        context={
            "request": request,
            "active_page": "admin",
            "current_user": current_user,
            "users": users,
            "csrf_token": csrf_token,
        },
    )


@router.post("/admin/users/{user_id}/role")
def admin_update_user_role(
    user_id: int,
    new_role: str = Form(...),
    current_admin = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.role = new_role
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@router.get("/admin/moderation", response_class=HTMLResponse)
def admin_moderation_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    if not current_user or current_user.role not in ["admin", "moderator"]:
        return RedirectResponse(url="/auth/login", status_code=303)

    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_admin")

    return templates.TemplateResponse(
        request=request,
        name="admin/moderation.html",
        context={
            "request": request,
            "active_page": "admin",
            "current_user": current_user,
            "reports": reports,
            "csrf_token": csrf_token,
        },
    )


@router.post("/admin/moderation/{report_id}/resolve")
def admin_resolve_report(
    report_id: int,
    current_user = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    rep = db.query(Report).filter(Report.id == report_id).first()
    if rep:
        rep.status = "resolved"
        db.commit()
    return RedirectResponse(url="/admin/moderation", status_code=303)


@router.post("/admin/moderation/{report_id}/dismiss")
def admin_dismiss_report(
    report_id: int,
    current_user = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    rep = db.query(Report).filter(Report.id == report_id).first()
    if rep:
        rep.status = "dismissed"
        db.commit()
    return RedirectResponse(url="/admin/moderation", status_code=303)


@router.get("/admin/listings", response_class=HTMLResponse)
def admin_listings_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    if not current_user or current_user.role not in ["admin", "moderator"]:
        return RedirectResponse(url="/auth/login", status_code=303)

    businesses = db.query(Business).order_by(Business.created_at.desc()).all()
    jobs = db.query(JobListing).order_by(JobListing.created_at.desc()).all()
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_admin")

    return templates.TemplateResponse(
        request=request,
        name="admin/listings.html",
        context={
            "request": request,
            "active_page": "admin",
            "current_user": current_user,
            "businesses": businesses,
            "jobs": jobs,
            "csrf_token": csrf_token,
        },
    )


@router.post("/admin/businesses/{business_id}/toggle-verify")
def admin_toggle_verify_business(
    business_id: int,
    current_user = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    biz = db.query(Business).filter(Business.id == business_id).first()
    if biz:
        biz.is_verified = not biz.is_verified
        db.commit()
    return RedirectResponse(url="/admin/listings", status_code=303)


@router.post("/admin/jobs/{job_id}/toggle-active")
def admin_toggle_active_job(
    job_id: int,
    current_user = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if job:
        job.is_active = not job.is_active
        db.commit()
    return RedirectResponse(url="/admin/listings", status_code=303)


# --- REST API ROUTES ---

@router.get("/api/v1/admin/stats")
def api_admin_stats(
    current_admin = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return {
        "users": db.query(User).count(),
        "businesses": db.query(Business).count(),
        "jobs": db.query(JobListing).count(),
        "news": db.query(NewsArticle).count(),
        "events": db.query(Event).count(),
        "institutes": db.query(EducationInstitute).count(),
        "posts": db.query(CommunityPost).count(),
        "pending_reports": db.query(Report).filter(Report.status == "pending").count(),
    }
