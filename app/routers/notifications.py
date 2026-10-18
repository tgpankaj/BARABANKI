from typing import List, Optional
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user_optional, get_current_user
from app.core.security import generate_csrf_token
from app.models.notification import Notification
from app.schemas.notification import NotificationOut, NotificationCountOut

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- WEB HTML ROUTES ---

@router.get("/notifications", response_class=HTMLResponse)
def notifications_view(
    request: Request,
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    notifications = (
        db.query(Notification)
        .filter(Notification.recipient_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
        .all()
    )

    unread_count = (
        db.query(Notification)
        .filter(Notification.recipient_id == current_user.id, Notification.is_read == False)
        .count()
    )

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")

    return templates.TemplateResponse(
        request=request,
        name="notifications/list.html",
        context={
            "active_page": "notifications",
            "current_user": current_user,
            "notifications": notifications,
            "unread_count": unread_count,
            "csrf_token": csrf_token,
        },
    )


@router.post("/notifications/{notification_id}/read")
def notification_mark_read_action(
    notification_id: int,
    request: Request,
    csrf_token: Optional[str] = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.recipient_id == current_user.id)
        .first()
    )
    if notif:
        notif.is_read = True
        db.commit()
        if notif.link:
            return RedirectResponse(url=notif.link, status_code=303)

    return RedirectResponse(url="/notifications", status_code=303)


@router.post("/notifications/mark-all-read")
def notification_mark_all_read_action(
    request: Request,
    csrf_token: Optional[str] = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    db.query(Notification).filter(
        Notification.recipient_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()

    return RedirectResponse(url="/notifications", status_code=303)


# --- REST API ROUTES ---

@router.get("/api/v1/notifications", response_model=List[NotificationOut])
def api_get_notifications(
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notifs = (
        db.query(Notification)
        .filter(Notification.recipient_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    result = []
    for n in notifs:
        out = NotificationOut.model_validate(n)
        out.sender_name = n.sender.full_name if n.sender else "System"
        result.append(out)
    return result


@router.get("/api/v1/notifications/unread-count", response_model=NotificationCountOut)
def api_get_unread_count(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = (
        db.query(Notification)
        .filter(Notification.recipient_id == current_user.id, Notification.is_read == False)
        .count()
    )
    return NotificationCountOut(unread_count=count)


@router.post("/api/v1/notifications/{notification_id}/read")
def api_mark_notification_read(
    notification_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.recipient_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")

    notif.is_read = True
    db.commit()
    return {"message": "Notification marked as read.", "id": notification_id}


@router.post("/api/v1/notifications/mark-all-read")
def api_mark_all_notifications_read(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = (
        db.query(Notification)
        .filter(Notification.recipient_id == current_user.id, Notification.is_read == False)
        .update({"is_read": True})
    )
    db.commit()
    return {"message": f"{updated} notifications marked as read."}
