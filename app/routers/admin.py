from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db, utc_now
from app.core.dependencies import get_current_user_optional, require_moderator_or_admin, require_admin
from app.core.security import generate_csrf_token
from app.models.user import User
from app.models.business import Business
from app.models.job import JobListing
from app.models.news import NewsArticle
from app.models.event import Event
from app.models.education import EducationInstitute
from app.models.community import CommunityPost
from app.models.report import Report, ModerationAudit
from app.models.civic_issue import CivicIssue, IssueStatusHistory
from app.models.notification import Notification

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
        "civic_issues": db.query(CivicIssue).count(),
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
        old_role = user.role
        user.role = new_role
        audit = ModerationAudit(
            entity_type="user",
            entity_id=user.id,
            moderator_id=current_admin.id,
            action=f"role_changed_{new_role}",
            reason=f"Role changed from {old_role} to {new_role}",
        )
        db.add(audit)
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
    posts = db.query(CommunityPost).order_by(CommunityPost.created_at.desc()).limit(30).all()
    civic_issues = db.query(CivicIssue).order_by(CivicIssue.created_at.desc()).limit(30).all()
    audits = db.query(ModerationAudit).order_by(ModerationAudit.created_at.desc()).limit(30).all()
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_admin")
    msg = request.query_params.get("msg")

    return templates.TemplateResponse(
        request=request,
        name="admin/moderation.html",
        context={
            "request": request,
            "active_page": "admin",
            "current_user": current_user,
            "reports": reports,
            "posts": posts,
            "civic_issues": civic_issues,
            "audits": audits,
            "csrf_token": csrf_token,
            "message": msg,
        },
    )


@router.post("/admin/moderation/{report_id}/resolve")
def admin_resolve_report(
    report_id: int,
    action_taken: Optional[str] = Form("Resolved by moderator"),
    moderator_notes: Optional[str] = Form(None),
    current_user = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    rep = db.query(Report).filter(Report.id == report_id).first()
    if rep:
        rep.status = "resolved"
        rep.action_taken = action_taken.strip() if action_taken else "Resolved"
        rep.moderator_id = current_user.id
        rep.moderator_notes = moderator_notes.strip() if moderator_notes else None
        rep.updated_at = utc_now()

        audit = ModerationAudit(
            entity_type="report",
            entity_id=rep.id,
            moderator_id=current_user.id,
            action="resolved",
            reason=rep.reason,
            details=moderator_notes.strip() if moderator_notes else f"Target: {rep.target_type} #{rep.target_id}",
        )
        db.add(audit)
        db.commit()
    return RedirectResponse(url="/admin/moderation?msg=Report+marked+resolved", status_code=303)


@router.post("/admin/moderation/{report_id}/dismiss")
def admin_dismiss_report(
    report_id: int,
    moderator_notes: Optional[str] = Form(None),
    current_user = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    rep = db.query(Report).filter(Report.id == report_id).first()
    if rep:
        rep.status = "dismissed"
        rep.action_taken = "Dismissed / No violation"
        rep.moderator_id = current_user.id
        rep.moderator_notes = moderator_notes.strip() if moderator_notes else None
        rep.updated_at = utc_now()

        audit = ModerationAudit(
            entity_type="report",
            entity_id=rep.id,
            moderator_id=current_user.id,
            action="dismissed",
            reason=rep.reason,
            details=moderator_notes.strip() if moderator_notes else "Report dismissed by moderator.",
        )
        db.add(audit)
        db.commit()
    return RedirectResponse(url="/admin/moderation?msg=Report+dismissed", status_code=303)


@router.post("/admin/posts/{post_id}/status")
def admin_update_post_status(
    post_id: int,
    new_status: str = Form(...),
    reason: Optional[str] = Form(None),
    current_user = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    old_status = post.status
    post.status = new_status.strip()
    post.updated_at = utc_now()

    audit = ModerationAudit(
        entity_type="post",
        entity_id=post.id,
        moderator_id=current_user.id,
        action=f"status_{new_status}",
        reason=reason.strip() if reason else f"Post status updated: {old_status} -> {new_status}",
    )
    db.add(audit)

    if new_status in ["hidden", "flagged"] and post.author_id != current_user.id:
        notif = Notification(
            recipient_id=post.author_id,
            sender_id=current_user.id,
            notification_type="moderation",
            title="Post Moderation Notice",
            message=f"Your post '{post.title[:30]}' status has been changed to {new_status}." + (f" Reason: {reason.strip()}" if reason else ""),
            link="/community",
        )
        db.add(notif)

    db.commit()
    return RedirectResponse(url="/admin/moderation?msg=Post+status+updated", status_code=303)


@router.post("/admin/issues/{issue_id}/status")
def admin_update_issue_status_action(
    issue_id: int,
    new_status: str = Form(...),
    admin_notes: Optional[str] = Form(None),
    current_user = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    old_status = issue.status
    cleaned_status = new_status.strip()

    issue.status = cleaned_status
    if admin_notes:
        issue.admin_notes = admin_notes.strip()
    issue.updated_at = utc_now()

    history = IssueStatusHistory(
        issue_id=issue.id,
        old_status=old_status,
        new_status=cleaned_status,
        notes=admin_notes.strip() if admin_notes else f"Status changed to {cleaned_status}",
        changed_by_id=current_user.id,
    )
    db.add(history)

    audit = ModerationAudit(
        entity_type="civic_issue",
        entity_id=issue.id,
        moderator_id=current_user.id,
        action=f"status_{cleaned_status.lower().replace(' ', '_')}",
        reason=f"Status update: {old_status} -> {cleaned_status}",
        details=admin_notes.strip() if admin_notes else None,
    )
    db.add(audit)

    notif = Notification(
        recipient_id=issue.reported_by_id,
        sender_id=current_user.id,
        notification_type="issue_status",
        title=f"Civic Issue: {cleaned_status}",
        message=f"Status for '{issue.title[:30]}' is now {cleaned_status}." + (f" Note: {admin_notes.strip()}" if admin_notes else ""),
        link=f"/issues/{issue.slug}",
    )
    db.add(notif)
    db.commit()

    return RedirectResponse(url="/admin/moderation?msg=Civic+issue+status+updated", status_code=303)


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
    events = db.query(Event).order_by(Event.created_at.desc()).all()
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
            "events": events,
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
        audit = ModerationAudit(
            entity_type="business",
            entity_id=biz.id,
            moderator_id=current_user.id,
            action="verified" if biz.is_verified else "unverified",
            reason="Verification status toggled",
        )
        db.add(audit)
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
        audit = ModerationAudit(
            entity_type="job",
            entity_id=job.id,
            moderator_id=current_user.id,
            action="activated" if job.is_active else "deactivated",
            reason="Active status toggled",
        )
        db.add(audit)
        db.commit()
    return RedirectResponse(url="/admin/listings", status_code=303)


@router.post("/admin/events/{event_id}/toggle-approve")
def admin_toggle_approve_event(
    event_id: int,
    current_user = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    ev = db.query(Event).filter(Event.id == event_id).first()
    if ev:
        ev.is_approved = not ev.is_approved
        audit = ModerationAudit(
            entity_type="event",
            entity_id=ev.id,
            moderator_id=current_user.id,
            action="approved" if ev.is_approved else "unapproved",
            reason="Approval status toggled",
        )
        db.add(audit)
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
        "civic_issues": db.query(CivicIssue).count(),
        "pending_reports": db.query(Report).filter(Report.status == "pending").count(),
    }


@router.get("/api/v1/admin/audits")
def api_admin_audits(
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    audits = db.query(ModerationAudit).order_by(ModerationAudit.created_at.desc()).offset(offset).limit(limit).all()
    return [
        {
            "id": a.id,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "moderator_id": a.moderator_id,
            "moderator_name": a.moderator.full_name if a.moderator else "System",
            "action": a.action,
            "reason": a.reason,
            "details": a.details,
            "created_at": a.created_at,
        }
        for a in audits
    ]
