from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user_optional, get_current_user
from app.core.rate_limiter import check_rate_limit
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    generate_csrf_token,
    validate_csrf_token,
)
from app.models.user import User, UserFollow
from app.models.community import CommunityPost
from app.models.notification import Notification
from app.schemas.auth import (
    UserRegister,
    UserOut,
    TokenResponse,
    UserProfileUpdate,
    UserProfilePublicOut,
)

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

    check_rate_limit(request, scope="auth:login")

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
        secure=settings.COOKIE_SECURE or settings.is_production,
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

    check_rate_limit(request, scope="auth:register")

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
        secure=settings.COOKIE_SECURE or settings.is_production,
    )
    return response


@router.get("/auth/logout")
def logout_action():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/profile", response_class=HTMLResponse)
def profile_view(
    request: Request,
    current_user = Depends(get_current_user_optional),
    msg: str = None,
    demo: Optional[int] = None,
    db: Session = Depends(get_db),
):
    if not current_user:
        if demo or request.query_params.get("preview") == "1":
            demo_user = db.query(User).filter(User.role == "creator").first() or db.query(User).first()
            csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
            return templates.TemplateResponse(
                request=request,
                name="auth/profile.html",
                context={"active_page": "profile", "current_user": demo_user, "is_demo_view": True, "csrf_token": csrf_token, "message": msg},
            )
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
    locality: Optional[str] = Form("Barabanki"),
    bio: Optional[str] = Form(None),
    avatar_url: Optional[str] = Form(None),
    csrf_token: str = Form(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        return RedirectResponse(url="/profile?msg=CSRF+error", status_code=303)

    current_user.full_name = full_name.strip()
    current_user.phone = phone.strip() if phone else None
    current_user.locality = locality.strip() if locality else "Barabanki"
    current_user.bio = bio.strip() if bio else None
    if avatar_url:
        current_user.avatar_url = avatar_url.strip()
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


@router.get("/profile/{username}", response_class=HTMLResponse)
def public_profile_view(
    username: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    target_user = db.query(User).filter(User.username == username.strip().lower()).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User profile not found.")

    followers_count = db.query(UserFollow).filter(UserFollow.following_id == target_user.id).count()
    following_count = db.query(UserFollow).filter(UserFollow.follower_id == target_user.id).count()
    posts = (
        db.query(CommunityPost)
        .filter(CommunityPost.author_id == target_user.id, CommunityPost.status == "published")
        .order_by(CommunityPost.created_at.desc())
        .all()
    )

    is_following = False
    is_own_profile = False
    if current_user:
        is_own_profile = bool(current_user.id == target_user.id)
        if not is_own_profile:
            is_following = bool(
                db.query(UserFollow)
                .filter(UserFollow.follower_id == current_user.id, UserFollow.following_id == target_user.id)
                .first()
            )

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    return templates.TemplateResponse(
        request=request,
        name="auth/public_profile.html",
        context={
            "active_page": "creators",
            "current_user": current_user,
            "target_user": target_user,
            "followers_count": followers_count,
            "following_count": following_count,
            "posts": posts,
            "is_following": is_following,
            "is_own_profile": is_own_profile,
            "csrf_token": csrf_token,
        },
    )


@router.post("/profile/{username}/follow")
def toggle_follow_user(
    username: str,
    request: Request,
    csrf_token: Optional[str] = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        if request.headers.get("accept") == "application/json":
            raise HTTPException(status_code=401, detail="Authentication required to follow users.")
        return RedirectResponse(url="/auth/login", status_code=303)

    target_user = db.query(User).filter(User.username == username.strip().lower()).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    if current_user.id == target_user.id:
        if request.headers.get("accept") == "application/json":
            raise HTTPException(status_code=400, detail="You cannot follow yourself.")
        return RedirectResponse(url=f"/profile/{username}?msg=You+cannot+follow+yourself", status_code=303)

    existing = (
        db.query(UserFollow)
        .filter(UserFollow.follower_id == current_user.id, UserFollow.following_id == target_user.id)
        .first()
    )
    if existing:
        db.delete(existing)
        following = False
    else:
        new_follow = UserFollow(follower_id=current_user.id, following_id=target_user.id)
        db.add(new_follow)
        following = True

        notif = Notification(
            recipient_id=target_user.id,
            sender_id=current_user.id,
            notification_type="follow",
            title="New Follower",
            message=f"{current_user.full_name} started following you.",
            link=f"/profile/{current_user.username}",
        )
        db.add(notif)

    db.commit()

    followers_count = db.query(UserFollow).filter(UserFollow.following_id == target_user.id).count()
    if request.headers.get("accept") == "application/json":
        return JSONResponse({"following": following, "followers_count": followers_count})
    return RedirectResponse(url=f"/profile/{username}", status_code=303)


# --- REST API ENDPOINTS ---

@router.post("/api/v1/auth/token", response_model=TokenResponse)
def api_token_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    check_rate_limit(request, scope="auth:api_token")
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
    request: Request,
    payload: UserRegister,
    db: Session = Depends(get_db),
):
    check_rate_limit(request, scope="auth:api_register")
    cleaned_username = payload.username.strip().lower()
    cleaned_email = payload.email.strip().lower()

    if db.query(User).filter(User.username == cleaned_username).first():
        raise HTTPException(status_code=400, detail="Username is already taken.")

    if db.query(User).filter(User.email == cleaned_email).first():
        raise HTTPException(status_code=400, detail="Email is already registered.")

    allowed_roles = ["resident", "business_owner", "creator"]
    user_role = payload.role if payload.role in allowed_roles else "resident"

    new_user = User(
        username=cleaned_username,
        email=cleaned_email,
        full_name=payload.full_name.strip(),
        phone=payload.phone,
        hashed_password=get_password_hash(payload.password),
        role=user_role,
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


@router.patch("/api/v1/auth/me", response_model=UserOut)
def api_update_me(
    payload: UserProfileUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()
    if payload.phone is not None:
        current_user.phone = payload.phone.strip() if payload.phone else None
    if payload.locality is not None:
        current_user.locality = payload.locality.strip() if payload.locality else "Barabanki"
    if payload.bio is not None:
        current_user.bio = payload.bio.strip() if payload.bio else None
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url.strip() if payload.avatar_url else None
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/api/v1/users/{username}", response_model=UserProfilePublicOut)
def api_get_public_profile(
    username: str,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username.strip().lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    followers_count = db.query(UserFollow).filter(UserFollow.following_id == user.id).count()
    following_count = db.query(UserFollow).filter(UserFollow.follower_id == user.id).count()
    posts_count = db.query(CommunityPost).filter(CommunityPost.author_id == user.id, CommunityPost.status == "published").count()

    return UserProfilePublicOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        locality=user.locality or "Barabanki",
        bio=user.bio,
        avatar_url=user.avatar_url,
        followers_count=followers_count,
        following_count=following_count,
        posts_count=posts_count,
        created_at=user.created_at,
    )


@router.post("/api/v1/users/{username}/follow")
def api_toggle_follow_user(
    username: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_user = db.query(User).filter(User.username == username.strip().lower()).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    if current_user.id == target_user.id:
        raise HTTPException(status_code=400, detail="You cannot follow yourself.")

    existing = (
        db.query(UserFollow)
        .filter(UserFollow.follower_id == current_user.id, UserFollow.following_id == target_user.id)
        .first()
    )
    if existing:
        db.delete(existing)
        following = False
    else:
        new_follow = UserFollow(follower_id=current_user.id, following_id=target_user.id)
        db.add(new_follow)
        following = True

        notif = Notification(
            recipient_id=target_user.id,
            sender_id=current_user.id,
            notification_type="follow",
            title="New Follower",
            message=f"{current_user.full_name} started following you.",
            link=f"/profile/{current_user.username}",
        )
        db.add(notif)

    db.commit()

    followers_count = db.query(UserFollow).filter(UserFollow.following_id == target_user.id).count()
    return {"following": following, "followers_count": followers_count}

