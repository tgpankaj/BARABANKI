import math
from typing import Optional, List
from fastapi import APIRouter, Request, Depends, HTTPException, status, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, utc_now
from app.core.dependencies import get_current_user_optional, get_current_user, require_moderator_or_admin
from app.core.security import generate_csrf_token, validate_csrf_token
from app.models.civic_issue import CivicIssue, CivicIssueUpvote, IssueStatusHistory
from app.models.notification import Notification
from app.models.report import ModerationAudit
from app.schemas.civic_issue import (
    CivicIssueCreate,
    IssueStatusUpdate,
    IssueStatusHistoryOut,
    CivicIssueOut,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

CIVIC_CATEGORIES = [
    "Roads & Potholes",
    "Sanitation & Garbage",
    "Water Supply",
    "Electricity",
    "Drainage & Sewage",
    "Streetlights",
    "Public Health",
    "Other",
]

CIVIC_LOCALITIES = [
    "Barabanki City",
    "Nawabganj",
    "Deva Sharif",
    "Fatehpur",
    "Ramnagar",
    "Haidergarh",
    "Rudauli",
    "Zaidpur",
    "Sirauli Ghauspur",
    "Ram Sanehi Ghat",
    "Banki",
]


# --- WEB HTML ROUTES ---

@router.get("/issues", response_class=HTMLResponse)
def issues_list_view(
    request: Request,
    page: int = Query(1, ge=1),
    category: Optional[str] = None,
    locality: Optional[str] = None,
    issue_status: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    page_size = settings.DEFAULT_PAGE_SIZE
    query = db.query(CivicIssue)

    if category and category != "All":
        query = query.filter(CivicIssue.category == category)
    if locality and locality != "All":
        query = query.filter(CivicIssue.locality == locality)
    if issue_status and issue_status != "All":
        query = query.filter(CivicIssue.status == issue_status)
    if q:
        query = query.filter(CivicIssue.title.ilike(f"%{q.strip()}%") | CivicIssue.description.ilike(f"%{q.strip()}%"))

    total_issues = query.count()
    total_pages = math.ceil(total_issues / page_size) or 1
    offset = (page - 1) * page_size

    issues = query.order_by(CivicIssue.created_at.desc()).offset(offset).limit(page_size).all()

    user_upvoted_ids = set()
    if current_user:
        upvotes = db.query(CivicIssueUpvote.issue_id).filter(CivicIssueUpvote.user_id == current_user.id).all()
        user_upvoted_ids = {u[0] for u in upvotes}

    # Summary stats
    stats = {
        "total": db.query(CivicIssue).count(),
        "resolved": db.query(CivicIssue).filter(CivicIssue.status == "Resolved").count(),
        "in_progress": db.query(CivicIssue).filter(CivicIssue.status == "In Progress").count(),
        "under_review": db.query(CivicIssue).filter(CivicIssue.status.in_(["Submitted", "Under Review"])).count(),
    }

    return templates.TemplateResponse(
        request=request,
        name="issues/list.html",
        context={
            "active_page": "community",
            "current_user": current_user,
            "issues": issues,
            "current_page": page,
            "total_pages": total_pages,
            "current_category": category or "All",
            "current_locality": locality or "All",
            "current_status": issue_status or "All",
            "search_query": q or "",
            "categories": CIVIC_CATEGORIES,
            "localities": CIVIC_LOCALITIES,
            "user_upvoted_ids": user_upvoted_ids,
            "stats": stats,
        },
    )


@router.get("/issues/new", response_class=HTMLResponse)
def issue_create_view(
    request: Request,
    current_user = Depends(get_current_user_optional),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    return templates.TemplateResponse(
        request=request,
        name="issues/create.html",
        context={
            "active_page": "community",
            "current_user": current_user,
            "categories": CIVIC_CATEGORIES,
            "localities": CIVIC_LOCALITIES,
            "csrf_token": csrf_token,
        },
    )


@router.post("/issues/new")
def issue_create_action(
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    locality: str = Form("Barabanki City"),
    landmark: Optional[str] = Form(None),
    description: str = Form(...),
    image_url: Optional[str] = Form(None),
    csrf_token: Optional[str] = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        return RedirectResponse(url="/issues/new", status_code=303)

    from app.seeds.seed_data import slugify
    base_slug = slugify(title) or "issue"
    slug = base_slug
    counter = 1
    while db.query(CivicIssue).filter(CivicIssue.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    issue = CivicIssue(
        title=title.strip(),
        slug=slug,
        category=category.strip(),
        locality=locality.strip() if locality else "Barabanki City",
        landmark=landmark.strip() if landmark else None,
        description=description.strip(),
        image_url=image_url.strip() if image_url else None,
        reported_by_id=current_user.id,
        status="Submitted",
        upvotes=1,
    )
    db.add(issue)
    db.flush()

    # Initial status history record
    history = IssueStatusHistory(
        issue_id=issue.id,
        old_status="None",
        new_status="Submitted",
        notes="Civic issue reported by citizen.",
        changed_by_id=current_user.id,
    )
    db.add(history)

    # Initial upvote by reporter
    upvote = CivicIssueUpvote(
        issue_id=issue.id,
        user_id=current_user.id,
    )
    db.add(upvote)

    db.commit()
    return RedirectResponse(url=f"/issues/{slug}?msg=Issue+reported+successfully!", status_code=303)


@router.get("/issues/{slug}", response_class=HTMLResponse)
def issue_detail_view(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    issue = db.query(CivicIssue).filter(CivicIssue.slug == slug).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Civic issue not found.")

    has_upvoted = False
    if current_user:
        has_upvoted = bool(
            db.query(CivicIssueUpvote)
            .filter(CivicIssueUpvote.issue_id == issue.id, CivicIssueUpvote.user_id == current_user.id)
            .first()
        )

    is_admin = bool(current_user and current_user.role in ["admin", "moderator"])
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    msg = request.query_params.get("msg")

    return templates.TemplateResponse(
        request=request,
        name="issues/detail.html",
        context={
            "active_page": "community",
            "current_user": current_user,
            "issue": issue,
            "has_upvoted": has_upvoted,
            "is_admin": is_admin,
            "csrf_token": csrf_token,
            "message": msg,
        },
    )


@router.post("/issues/{slug}/upvote")
def issue_toggle_upvote(
    slug: str,
    request: Request,
    csrf_token: Optional[str] = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        if request.headers.get("accept") == "application/json":
            raise HTTPException(status_code=401, detail="Authentication required to upvote issues.")
        return RedirectResponse(url="/auth/login", status_code=303)

    issue = db.query(CivicIssue).filter(CivicIssue.slug == slug).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Civic issue not found.")

    existing = db.query(CivicIssueUpvote).filter(
        CivicIssueUpvote.issue_id == issue.id,
        CivicIssueUpvote.user_id == current_user.id,
    ).first()

    if existing:
        db.delete(existing)
        issue.upvotes = max(0, issue.upvotes - 1)
        upvoted = False
    else:
        new_upvote = CivicIssueUpvote(issue_id=issue.id, user_id=current_user.id)
        db.add(new_upvote)
        issue.upvotes += 1
        upvoted = True

        if issue.reported_by_id != current_user.id:
            notif = Notification(
                recipient_id=issue.reported_by_id,
                sender_id=current_user.id,
                notification_type="issue_status",
                title="Citizen supported your issue",
                message=f"{current_user.full_name} said 'Me Too' on '{issue.title[:30]}'",
                link=f"/issues/{issue.slug}",
            )
            db.add(notif)

    db.commit()

    if request.headers.get("accept") == "application/json":
        return JSONResponse({"issue_id": issue.id, "upvotes": issue.upvotes, "upvoted": upvoted})
    return RedirectResponse(url=f"/issues/{slug}", status_code=303)


@router.post("/issues/{slug}/status")
def issue_update_status(
    slug: str,
    request: Request,
    new_status: str = Form(...),
    admin_notes: Optional[str] = Form(None),
    csrf_token: Optional[str] = Form(None),
    current_user = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    issue = db.query(CivicIssue).filter(CivicIssue.slug == slug).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Civic issue not found.")

    old_status = issue.status
    cleaned_status = new_status.strip()

    if cleaned_status not in ["Submitted", "Under Review", "In Progress", "Resolved", "Rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status.")

    issue.status = cleaned_status
    issue.admin_notes = admin_notes.strip() if admin_notes else issue.admin_notes
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

    return RedirectResponse(url=f"/issues/{slug}?msg=Status+updated+to+{cleaned_status}", status_code=303)


# --- REST API ROUTES ---

@router.get("/api/v1/issues", response_model=List[CivicIssueOut])
def api_get_issues(
    category: Optional[str] = None,
    locality: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    query = db.query(CivicIssue)
    if category and category != "All":
        query = query.filter(CivicIssue.category == category)
    if locality and locality != "All":
        query = query.filter(CivicIssue.locality == locality)
    if status_filter and status_filter != "All":
        query = query.filter(CivicIssue.status == status_filter)
    if q:
        query = query.filter(CivicIssue.title.ilike(f"%{q.strip()}%") | CivicIssue.description.ilike(f"%{q.strip()}%"))

    issues = query.order_by(CivicIssue.created_at.desc()).offset(offset).limit(limit).all()

    user_upvoted_ids = set()
    if current_user:
        upvotes = db.query(CivicIssueUpvote.issue_id).filter(CivicIssueUpvote.user_id == current_user.id).all()
        user_upvoted_ids = {u[0] for u in upvotes}

    result = []
    for iss in issues:
        out = CivicIssueOut.model_validate(iss)
        out.reporter_name = iss.reporter.full_name if iss.reporter else "Barabanki Resident"
        out.has_upvoted = iss.id in user_upvoted_ids
        out.status_history = [
            IssueStatusHistoryOut(
                id=h.id,
                issue_id=h.issue_id,
                old_status=h.old_status,
                new_status=h.new_status,
                notes=h.notes,
                changed_by_id=h.changed_by_id,
                changed_by_name=h.changed_by.full_name if h.changed_by else "System",
                created_at=h.created_at,
            )
            for h in iss.status_history
        ]
        result.append(out)

    return result


@router.get("/api/v1/issues/{slug}", response_model=CivicIssueOut)
def api_get_issue(
    slug: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    issue = db.query(CivicIssue).filter(CivicIssue.slug == slug).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Civic issue not found.")

    out = CivicIssueOut.model_validate(issue)
    out.reporter_name = issue.reporter.full_name if issue.reporter else "Barabanki Resident"
    if current_user:
        out.has_upvoted = bool(
            db.query(CivicIssueUpvote)
            .filter(CivicIssueUpvote.issue_id == issue.id, CivicIssueUpvote.user_id == current_user.id)
            .first()
        )
    else:
        out.has_upvoted = False

    out.status_history = [
        IssueStatusHistoryOut(
            id=h.id,
            issue_id=h.issue_id,
            old_status=h.old_status,
            new_status=h.new_status,
            notes=h.notes,
            changed_by_id=h.changed_by_id,
            changed_by_name=h.changed_by.full_name if h.changed_by else "System",
            created_at=h.created_at,
        )
        for h in issue.status_history
    ]
    return out


@router.post("/api/v1/issues", response_model=CivicIssueOut, status_code=status.HTTP_201_CREATED)
def api_create_issue(
    payload: CivicIssueCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.seeds.seed_data import slugify
    base_slug = slugify(payload.title) or "issue"
    slug = base_slug
    counter = 1
    while db.query(CivicIssue).filter(CivicIssue.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    issue = CivicIssue(
        title=payload.title.strip(),
        slug=slug,
        category=payload.category.strip(),
        locality=payload.locality.strip() if payload.locality else "Barabanki City",
        landmark=payload.landmark.strip() if payload.landmark else None,
        latitude=payload.latitude,
        longitude=payload.longitude,
        description=payload.description.strip(),
        image_url=payload.image_url.strip() if payload.image_url else None,
        reported_by_id=current_user.id,
        status="Submitted",
        upvotes=1,
    )
    db.add(issue)
    db.flush()

    history = IssueStatusHistory(
        issue_id=issue.id,
        old_status="None",
        new_status="Submitted",
        notes="Civic issue reported by citizen.",
        changed_by_id=current_user.id,
    )
    db.add(history)

    upvote = CivicIssueUpvote(
        issue_id=issue.id,
        user_id=current_user.id,
    )
    db.add(upvote)
    db.commit()
    db.refresh(issue)

    out = CivicIssueOut.model_validate(issue)
    out.reporter_name = current_user.full_name
    out.has_upvoted = True
    out.status_history = [
        IssueStatusHistoryOut(
            id=history.id,
            issue_id=issue.id,
            old_status="None",
            new_status="Submitted",
            notes="Civic issue reported by citizen.",
            changed_by_id=current_user.id,
            changed_by_name=current_user.full_name,
            created_at=history.created_at,
        )
    ]
    return out


@router.post("/api/v1/issues/{slug}/upvote")
def api_toggle_issue_upvote(
    slug: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    issue = db.query(CivicIssue).filter(CivicIssue.slug == slug).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Civic issue not found.")

    existing = db.query(CivicIssueUpvote).filter(
        CivicIssueUpvote.issue_id == issue.id,
        CivicIssueUpvote.user_id == current_user.id,
    ).first()

    if existing:
        db.delete(existing)
        issue.upvotes = max(0, issue.upvotes - 1)
        upvoted = False
    else:
        new_upvote = CivicIssueUpvote(issue_id=issue.id, user_id=current_user.id)
        db.add(new_upvote)
        issue.upvotes += 1
        upvoted = True

        if issue.reported_by_id != current_user.id:
            notif = Notification(
                recipient_id=issue.reported_by_id,
                sender_id=current_user.id,
                notification_type="issue_status",
                title="Citizen supported your issue",
                message=f"{current_user.full_name} said 'Me Too' on '{issue.title[:30]}'",
                link=f"/issues/{issue.slug}",
            )
            db.add(notif)

    db.commit()
    return {"issue_id": issue.id, "upvotes": issue.upvotes, "upvoted": upvoted}


@router.post("/api/v1/issues/{slug}/status", response_model=CivicIssueOut)
def api_update_issue_status(
    slug: str,
    payload: IssueStatusUpdate,
    current_user = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    issue = db.query(CivicIssue).filter(CivicIssue.slug == slug).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Civic issue not found.")

    old_status = issue.status
    issue.status = payload.status
    if payload.notes:
        issue.admin_notes = payload.notes
    issue.updated_at = utc_now()

    history = IssueStatusHistory(
        issue_id=issue.id,
        old_status=old_status,
        new_status=payload.status,
        notes=payload.notes or f"Status changed to {payload.status}",
        changed_by_id=current_user.id,
    )
    db.add(history)

    audit = ModerationAudit(
        entity_type="civic_issue",
        entity_id=issue.id,
        moderator_id=current_user.id,
        action=f"status_{payload.status.lower().replace(' ', '_')}",
        reason=f"Status update: {old_status} -> {payload.status}",
        details=payload.notes,
    )
    db.add(audit)

    notif = Notification(
        recipient_id=issue.reported_by_id,
        sender_id=current_user.id,
        notification_type="issue_status",
        title=f"Civic Issue: {payload.status}",
        message=f"Status for '{issue.title[:30]}' is now {payload.status}." + (f" Note: {payload.notes}" if payload.notes else ""),
        link=f"/issues/{issue.slug}",
    )
    db.add(notif)
    db.commit()
    db.refresh(issue)

    out = CivicIssueOut.model_validate(issue)
    out.reporter_name = issue.reporter.full_name if issue.reporter else "Barabanki Resident"
    out.status_history = [
        IssueStatusHistoryOut(
            id=h.id,
            issue_id=h.issue_id,
            old_status=h.old_status,
            new_status=h.new_status,
            notes=h.notes,
            changed_by_id=h.changed_by_id,
            changed_by_name=h.changed_by.full_name if h.changed_by else "System",
            created_at=h.created_at,
        )
        for h in issue.status_history
    ]
    return out
