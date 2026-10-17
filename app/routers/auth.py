from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user_optional, get_current_user
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    generate_csrf_token,
    validate_csrf_token,
)
from app.models.user import User
from app.schemas.auth import UserRegister, UserOut, TokenResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- WEB HTML VIEWS ---

@router.get("/auth/login", response_class=HTMLResponse)
def login_view(
    request: Request,
    current_user = Depends(get_current_user_optional),
):
    if current_user:
        return RedirectResponse(url="/profile", status_code=303)
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"active_page": "login", "csrf_token": csrf_token},
    )


@router.post("/auth/login")
def login_action(
    request: Request,
    email_or_username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(None),
    db: Session = Depends(get_db),
):
    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"error": "Invalid CSRF security token. Please try again.", "csrf_token": generate_csrf_token(session_id)},
            status_code=400,
        )

    # Find user by email or username
    user = db.query(User).filter(
        or_(
            User.email == email_or_username.strip().lower(),
            User.username == email_or_username.strip().lower(),
        )
    ).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"error": "Invalid email/username or password.", "csrf_token": generate_csrf_token(session_id)},
            status_code=400,
        )

    if not user.is_active:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"error": "Your account has been deactivated. Please contact support.", "csrf_token": generate_csrf_token(session_id)},
            status_code=403,
        )

    # Generate JWT token
    token = create_access_token(data={"sub": str(user.id), "role": user.role})

    # Redirect to admin if admin, else profile
    target_url = "/admin" if user.role in ["admin", "moderator"] else "/profile"
    response = RedirectResponse(url=target_url, status_code=303)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )
    return response


@router.get("/auth/register", response_class=HTMLResponse)
def register_view(
    request: Request,
    current_user = Depends(get_current_user_optional),
):
    if current_user:
        return RedirectResponse(url="/profile", status_code=303)
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    return templates.TemplateResponse(
        request=request,
        name="auth/register.html",
        context={"active_page": "register", "csrf_token": csrf_token},
    )


@router.post("/auth/register")
def register_action(
    request: Request,
    full_name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: Optional[str] = Form(None),
    role: str = Form("resident"),
    csrf_token: str = Form(None),
    db: Session = Depends(get_db),
):
    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "Invalid security token. Please try again.", "csrf_token": generate_csrf_token(session_id)},
            status_code=400,
        )

    # Validation
    cleaned_username = username.strip().lower()
    cleaned_email = email.strip().lower()

    if len(password) < 6:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "Password must be at least 6 characters long.", "csrf_token": generate_csrf_token(session_id)},
            status_code=400,
        )

    # Check for existing email/username
    if db.query(User).filter(User.username == cleaned_username).first():
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "This username is already taken. Please choose another.", "csrf_token": generate_csrf_token(session_id)},
            status_code=400,
        )

    if db.query(User).filter(User.email == cleaned_email).first():
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "An account with this email already exists.", "csrf_token": generate_csrf_token(session_id)},
            status_code=400,
        )

    allowed_roles = ["resident", "business_owner", "creator"]
    user_role = role if role in allowed_roles else "resident"

    new_user = User(
        username=cleaned_username,
        email=cleaned_email,
        full_name=full_name.strip(),
        phone=phone.strip() if phone else None,
        hashed_password=get_password_hash(password),
        role=user_role,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(data={"sub": str(new_user.id), "role": new_user.role})
    response = RedirectResponse(url="/profile", status_code=303)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )
    return response


@router.get("/auth/logout")
def logout_action():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return response


@router.get("/profile", response_class=HTMLResponse)
def profile_view(
    request: Request,
    current_user = Depends(get_current_user_optional),
    msg: str = None,
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    return templates.TemplateResponse(
        request=request,
        name="auth/profile.html",
        context={"active_page": "profile", "current_user": current_user, "csrf_token": csrf_token, "message": msg},
    )


@router.post("/profile")
def update_profile(
    request: Request,
    full_name: str = Form(...),
    phone: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    csrf_token: str = Form(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        return RedirectResponse(url="/profile?msg=CSRF+error", status_code=303)

    current_user.full_name = full_name.strip()
    current_user.phone = phone.strip() if phone else None
    current_user.bio = bio.strip() if bio else None
    db.commit()

    return RedirectResponse(url="/profile?msg=Profile+updated+successfully!", status_code=303)


@router.post("/profile/password")
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    csrf_token: str = Form(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        return RedirectResponse(url="/profile?msg=CSRF+validation+failed", status_code=303)

    if not verify_password(current_password, current_user.hashed_password):
        return RedirectResponse(url="/profile?msg=Current+password+is+incorrect", status_code=303)

    if len(new_password) < 6:
        return RedirectResponse(url="/profile?msg=New+password+must+be+at+least+6+characters", status_code=303)

    current_user.hashed_password = get_password_hash(new_password)
    db.commit()

    return RedirectResponse(url="/profile?msg=Password+updated+successfully!", status_code=303)


# --- REST API ENDPOINTS ---

@router.post("/api/v1/auth/token", response_model=TokenResponse)
def api_token_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        or_(
            User.username == form_data.username.strip().lower(),
            User.email == form_data.username.strip().lower(),
        )
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive account.")

    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/api/v1/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def api_register(
    payload: UserRegister,
    db: Session = Depends(get_db),
):
    cleaned_username = payload.username.strip().lower()
    cleaned_email = payload.email.strip().lower()

    if db.query(User).filter(User.username == cleaned_username).first():
        raise HTTPException(status_code=400, detail="Username is already taken.")

    if db.query(User).filter(User.email == cleaned_email).first():
        raise HTTPException(status_code=400, detail="Email is already registered.")

    new_user = User(
        username=cleaned_username,
        email=cleaned_email,
        full_name=payload.full_name.strip(),
        phone=payload.phone,
        hashed_password=get_password_hash(payload.password),
        role=payload.role or "resident",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/api/v1/auth/me", response_model=UserOut)
def api_get_current_user(
    current_user = Depends(get_current_user),
):
    return current_user
