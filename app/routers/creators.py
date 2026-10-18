from typing import Optional, List
import math
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.core.database import get_db, utc_now
from app.core.dependencies import (
    get_current_user_optional,
    get_current_user,
    require_admin,
    require_moderator_or_admin,
)
from app.core.security import generate_csrf_token, validate_csrf_token
from app.core.social_validator import (
    validate_social_url,
    validate_portfolio_url,
    clean_social_url,
    clean_portfolio_url,
    clean_social_payload,
)
from app.models.creator import CreatorProfile, BusinessCollaboration, VERIFICATION_BADGES
from app.models.user import User, UserFollow
from app.models.business import Business
from app.models.community import CommunityPost
from app.models.notification import Notification
from app.schemas.creator import (
    CreatorProfileCreate,
    CreatorProfileUpdate,
    CreatorProfileOut,
    CreatorVerificationUpdate,
    BusinessCollaborationCreate,
    BusinessCollaborationStatusUpdate,
    BusinessCollaborationOut,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

CREATOR_CATEGORIES = [
    "Handloom & Textiles",
    "Digital Art & Code",
    "Literature & Poetry",
    "Music & Folk",
    "Photography",
    "Crafts & Pottery",
    "Food & Culinary",
]

BARABANKI_LOCALITIES = [
    "Nawabganj",
    "Zaidpur",
    "Fatehpur",
    "Ramnagar",
    "Haidergarh",
    "Rudauli",
    "Dariyabad",
    "Sirauli Ghauspur",
]


# ==============================================================================
# 1. WEB HTML ROUTES — CREATOR DIRECTORY & DISCOVERY
# ==============================================================================

@router.get("/creators", response_class=HTMLResponse)
def creators_list_view(
    request: Request,
    q: Optional[str] = None,
    category: Optional[str] = None,
    locality: Optional[str] = None,
    verified_only: Optional[bool] = False,
    page: int = 1,
    per_page: int = 12,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    """
    Creator Discovery & Hub.
    Supports keyword search (q), category, locality, verified badge filters,
    featured highlight sorting, pagination, and empty states.
    """
    query = db.query(CreatorProfile).join(User, CreatorProfile.user_id == User.id)

    # 1. Keyword search across name, title, bio, skills, craft_category, and locality
    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(term),
                CreatorProfile.title.ilike(term),
                CreatorProfile.bio.ilike(term),
                CreatorProfile.skills.ilike(term),
                CreatorProfile.craft_category.ilike(term),
                CreatorProfile.locality.ilike(term),
            )
        )

    # 2. Filter by craft category
    if category and category.strip() and category != "all":
        query = query.filter(CreatorProfile.craft_category == category.strip())

    # 3. Filter by locality
    if locality and locality.strip() and locality != "all":
        query = query.filter(CreatorProfile.locality == locality.strip())

    # 4. Verified creators only
    if verified_only:
        query = query.filter(CreatorProfile.is_verified.is_(True))

    # Total matching records
    total_count = query.count()
    page = max(1, page)
    total_pages = max(1, math.ceil(total_count / per_page)) if total_count > 0 else 1
    offset = (page - 1) * per_page

    # Order: Featured first, then Verified, then newest
    creators = (
        query.order_by(
            CreatorProfile.is_featured.desc(),
            CreatorProfile.is_verified.desc(),
            CreatorProfile.created_at.desc(),
        )
        .offset(offset)
        .limit(per_page)
        .all()
    )

    # Sidebar: Featured & Top Creators
    featured_creators = (
        db.query(CreatorProfile)
        .filter(CreatorProfile.is_featured.is_(True))
        .limit(4)
        .all()
    )
    if not featured_creators:
        featured_creators = (
            db.query(CreatorProfile)
            .filter(CreatorProfile.is_verified.is_(True))
            .limit(4)
            .all()
        )

    # Following status mapping for current user
    following_creator_user_ids = set()
    if current_user:
        follows = db.query(UserFollow.following_id).filter(UserFollow.follower_id == current_user.id).all()
        following_creator_user_ids = {f[0] for f in follows}

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")

    return templates.TemplateResponse(
        request=request,
        name="creators/list.html",
        context={
            "request": request,
            "active_page": "creators",
            "current_user": current_user,
            "creators": creators,
            "featured_creators": featured_creators,
            "categories": CREATOR_CATEGORIES,
            "localities": BARABANKI_LOCALITIES,
            "selected_category": category or "",
            "selected_locality": locality or "",
            "verified_only": verified_only,
            "q": q or "",
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "following_ids": following_creator_user_ids,
            "verification_badges": VERIFICATION_BADGES,
            "csrf_token": csrf_token,
        },
    )


@router.get("/creators/edit", response_class=HTMLResponse)
def creator_edit_view(
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Profile management page for creators.
    Allows creators to update biography, locality, languages, content categories,
    and public social links safely without storing passwords.
    """
    profile = db.query(CreatorProfile).filter(CreatorProfile.user_id == current_user.id).first()
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")

    return templates.TemplateResponse(
        request=request,
        name="creators/edit.html",
        context={
            "request": request,
            "active_page": "creators",
            "current_user": current_user,
            "profile": profile,
            "categories": CREATOR_CATEGORIES,
            "localities": BARABANKI_LOCALITIES,
            "csrf_token": csrf_token,
            "error": None,
            "success": None,
        },
    )


@router.post("/creators/edit", response_class=HTMLResponse)
def creator_edit_submit(
    request: Request,
    title: str = Form(...),
    craft_category: str = Form(...),
    bio: str = Form(...),
    skills: Optional[str] = Form(None),
    locality: str = Form("Barabanki"),
    languages: Optional[str] = Form("Hindi, Awadhi"),
    content_categories: Optional[str] = Form(None),
    portfolio_url: Optional[str] = Form(None),
    profile_photo: Optional[str] = Form(None),
    instagram: Optional[str] = Form(None),
    youtube: Optional[str] = Form(None),
    facebook: Optional[str] = Form(None),
    linkedin: Optional[str] = Form(None),
    twitter_x: Optional[str] = Form(None),
    github: Optional[str] = Form(None),
    csrf_token: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Save creator profile updates.
    Validates CSRF, length requirements, and strictly checks social links
    against the allowlist of legitimate domains.
    """
    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        raise HTTPException(status_code=400, detail="Invalid or expired CSRF security token.")

    # Validate Social Links via Domain Allowlist
    social_map = {
        "instagram": instagram,
        "youtube": youtube,
        "facebook": facebook,
        "linkedin": linkedin,
        "twitter_x": twitter_x,
        "github": github,
    }
    validated_socials = {}
    validation_errors = []

    for platform, raw_val in social_map.items():
        if raw_val and raw_val.strip():
            val, err = clean_social_url(platform, raw_val)
            if err:
                validation_errors.append(f"{platform.capitalize()}: {err}")
            else:
                validated_socials[platform] = val
        else:
            validated_socials[platform] = None

    if portfolio_url and portfolio_url.strip():
        p_val, p_err = clean_portfolio_url(portfolio_url)
        if p_err:
            validation_errors.append(f"Portfolio: {p_err}")
        else:
            portfolio_url = p_val
    else:
        portfolio_url = None

    # If any link failed allowlist verification, return user-friendly form with error
    if validation_errors:
        profile = db.query(CreatorProfile).filter(CreatorProfile.user_id == current_user.id).first()
        return templates.TemplateResponse(
            request=request,
            name="creators/edit.html",
            context={
                "request": request,
                "active_page": "creators",
                "current_user": current_user,
                "profile": profile,
                "categories": CREATOR_CATEGORIES,
                "localities": BARABANKI_LOCALITIES,
                "csrf_token": generate_csrf_token(session_id),
                "error": " ; ".join(validation_errors),
                "success": None,
            },
            status_code=400,
        )

    # Retrieve or create profile
    profile = db.query(CreatorProfile).filter(CreatorProfile.user_id == current_user.id).first()
    if not profile:
        profile = CreatorProfile(user_id=current_user.id)
        db.add(profile)

    profile.title = title.strip()
    profile.craft_category = craft_category.strip()
    profile.bio = bio.strip()
    profile.skills = skills.strip() if skills else None
    profile.locality = locality.strip()
    profile.languages = languages.strip() if languages else "Hindi, Awadhi"
    profile.content_categories = content_categories.strip() if content_categories else None
    profile.portfolio_url = portfolio_url
    profile.profile_photo = profile_photo.strip() if profile_photo else None

    # Assign validated social handles
    profile.instagram = validated_socials["instagram"]
    profile.youtube = validated_socials["youtube"]
    profile.facebook = validated_socials["facebook"]
    profile.linkedin = validated_socials["linkedin"]
    profile.twitter_x = validated_socials["twitter_x"]
    profile.github = validated_socials["github"]

    # Promote user role to creator if resident
    if current_user.role == "resident":
        current_user.role = "creator"

    db.commit()
    db.refresh(profile)

    return RedirectResponse(url=f"/creators/{profile.id}?updated=1", status_code=303)


@router.get("/creators/{creator_id}", response_class=HTMLResponse)
def creator_detail_view(
    creator_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    """
    Public creator profile detail page.
    Tracks internal profile views, verifies authentic local metrics (followers, discussions),
    shows clear verification badge definition, safe external social links,
    and a direct collaboration action for verified business accounts.
    """
    creator = db.query(CreatorProfile).filter(CreatorProfile.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator profile not found.")

    # Increment internal profile views (never fake external analytics)
    creator.profile_views = (creator.profile_views or 0) + 1
    db.commit()

    # Engagement and community metrics
    followers_count = db.query(UserFollow).filter(UserFollow.following_id == creator.user_id).count()
    posts_count = db.query(CommunityPost).filter(
        CommunityPost.author_id == creator.user_id,
        CommunityPost.status == "published",
    ).count()

    is_following = False
    is_owner = False
    user_businesses = []

    if current_user:
        is_owner = (current_user.id == creator.user_id)
        is_following = db.query(UserFollow).filter(
            UserFollow.follower_id == current_user.id,
            UserFollow.following_id == creator.user_id,
        ).first() is not None

        # Fetch businesses owned by current user or if admin
        if current_user.role == "admin":
            user_businesses = db.query(Business).filter(Business.is_approved.is_(True)).all()
        else:
            user_businesses = db.query(Business).filter(
                Business.created_by_id == current_user.id,
                Business.is_approved.is_(True),
            ).all()

    # Recent community posts by this creator
    recent_posts = (
        db.query(CommunityPost)
        .filter(CommunityPost.author_id == creator.user_id, CommunityPost.status == "published")
        .order_by(CommunityPost.created_at.desc())
        .limit(4)
        .all()
    )

    badge_description = VERIFICATION_BADGES.get(creator.verification_badge) if creator.verification_badge else None
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")

    return templates.TemplateResponse(
        request=request,
        name="creators/detail.html",
        context={
            "request": request,
            "active_page": "creators",
            "current_user": current_user,
            "creator": creator,
            "followers_count": followers_count,
            "posts_count": posts_count,
            "is_following": is_following,
            "is_owner": is_owner,
            "user_businesses": user_businesses,
            "recent_posts": recent_posts,
            "badge_description": badge_description,
            "verification_badges": VERIFICATION_BADGES,
            "csrf_token": csrf_token,
        },
    )


@router.post("/creators/{creator_id}/follow")
def creator_toggle_follow(
    creator_id: int,
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Follow or unfollow a creator.
    Prevents self-follow, avoids duplicate entries, and dispatches a notification.
    """
    creator = db.query(CreatorProfile).filter(CreatorProfile.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found.")

    if creator.user_id == current_user.id:
        if request.headers.get("accept") == "application/json":
            raise HTTPException(status_code=400, detail="You cannot follow yourself.")
        return RedirectResponse(url=f"/creators/{creator_id}?err=self_follow", status_code=303)

    existing = db.query(UserFollow).filter(
        UserFollow.follower_id == current_user.id,
        UserFollow.following_id == creator.user_id,
    ).first()

    if existing:
        db.delete(existing)
        following = False
    else:
        new_follow = UserFollow(follower_id=current_user.id, following_id=creator.user_id)
        db.add(new_follow)
        following = True

        notif = Notification(
            recipient_id=creator.user_id,
            sender_id=current_user.id,
            notification_type="follow",
            title="New Follower",
            message=f"{current_user.full_name} started following your creator profile.",
            link=f"/creators/{creator.id}",
        )
        db.add(notif)

    db.commit()

    followers_count = db.query(UserFollow).filter(UserFollow.following_id == creator.user_id).count()

    if request.headers.get("accept") == "application/json" or request.url.path.startswith("/api/"):
        return {"following": following, "followers_count": followers_count}

    return RedirectResponse(url=f"/creators/{creator_id}", status_code=303)


# ==============================================================================
# 2. WEB HTML ROUTES — BUSINESS COLLABORATION WORKFLOW
# ==============================================================================

@router.get("/creators/{creator_id}/collaborate", response_class=HTMLResponse)
def collaborate_form_view(
    creator_id: int,
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Collaboration proposal submission form.
    Only allows authorized business accounts (or admins) with registered businesses to submit.
    """
    creator = db.query(CreatorProfile).filter(CreatorProfile.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found.")

    if creator.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot send a collaboration proposal to yourself.")

    # Look up registered businesses
    if current_user.role == "admin":
        user_businesses = db.query(Business).filter(Business.is_approved.is_(True)).all()
    else:
        user_businesses = db.query(Business).filter(
            Business.created_by_id == current_user.id,
            Business.is_approved.is_(True),
        ).all()

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")

    return templates.TemplateResponse(
        request=request,
        name="creators/collaborate.html",
        context={
            "request": request,
            "active_page": "creators",
            "current_user": current_user,
            "creator": creator,
            "user_businesses": user_businesses,
            "csrf_token": csrf_token,
            "error": None,
        },
    )


@router.post("/creators/{creator_id}/collaborate", response_class=HTMLResponse)
def collaborate_form_submit(
    creator_id: int,
    request: Request,
    business_id: int = Form(...),
    campaign_title: str = Form(...),
    campaign_description: str = Form(...),
    proposed_deliverables: str = Form(...),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    budget_range: Optional[str] = Form(None),
    contact_preference: str = Form("email"),
    contact_details: str = Form(...),
    csrf_token: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Handle web collaboration proposal submission.
    Prevents duplicate pending requests and restricts details to authorized parties.
    """
    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        raise HTTPException(status_code=400, detail="Invalid CSRF token.")

    creator = db.query(CreatorProfile).filter(CreatorProfile.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found.")

    if creator.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot collaborate with yourself.")

    # Verify business ownership or administrative authority
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Selected business was not found.")

    if business.created_by_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You do not own or represent this business.")

    # Anti-Spam: Prevent duplicate active pending proposal
    existing_pending = db.query(BusinessCollaboration).filter(
        BusinessCollaboration.business_id == business_id,
        BusinessCollaboration.creator_id == creator_id,
        BusinessCollaboration.status == "pending",
    ).first()

    if existing_pending:
        # Re-render form with error message
        if current_user.role == "admin":
            user_businesses = db.query(Business).filter(Business.is_approved.is_(True)).all()
        else:
            user_businesses = db.query(Business).filter(Business.created_by_id == current_user.id).all()

        return templates.TemplateResponse(
            request=request,
            name="creators/collaborate.html",
            context={
                "request": request,
                "active_page": "creators",
                "current_user": current_user,
                "creator": creator,
                "user_businesses": user_businesses,
                "csrf_token": generate_csrf_token(session_id),
                "error": "A pending collaboration request from this business to this creator is already active.",
            },
            status_code=400,
        )

    # Input validations
    if len(campaign_title.strip()) < 5:
        raise HTTPException(status_code=400, detail="Campaign title must be at least 5 characters.")
    if len(campaign_description.strip()) < 20:
        raise HTTPException(status_code=400, detail="Campaign description must be at least 20 characters.")
    if len(proposed_deliverables.strip()) < 10:
        raise HTTPException(status_code=400, detail="Deliverables must be at least 10 characters.")

    collab = BusinessCollaboration(
        business_id=business.id,
        creator_id=creator.id,
        sender_user_id=current_user.id,
        campaign_title=campaign_title.strip(),
        campaign_description=campaign_description.strip(),
        proposed_deliverables=proposed_deliverables.strip(),
        start_date=start_date.strip() if start_date else None,
        end_date=end_date.strip() if end_date else None,
        budget_range=budget_range.strip() if budget_range else None,
        contact_preference=contact_preference.strip(),
        contact_details=contact_details.strip(),
        status="pending",
    )
    db.add(collab)

    # Notify creator
    notif = Notification(
        recipient_id=creator.user_id,
        sender_id=current_user.id,
        notification_type="collaboration",
        title="New Business Collaboration Request",
        message=f"{business.name} submitted a collaboration proposal: '{campaign_title.strip()}'",
        link="/collaborations",
    )
    db.add(notif)
    db.commit()

    return RedirectResponse(url="/collaborations?sent=1", status_code=303)


@router.get("/collaborations", response_class=HTMLResponse)
def collaborations_dashboard_view(
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Collaborations inbox and status management dashboard.
    Shows incoming collaboration proposals for creators,
    and outgoing proposals for businesses.
    """
    # 1. Incoming Proposals (if user has a creator profile)
    incoming = []
    if current_user.creator_profile:
        incoming = (
            db.query(BusinessCollaboration)
            .filter(BusinessCollaboration.creator_id == current_user.creator_profile.id)
            .order_by(BusinessCollaboration.created_at.desc())
            .all()
        )

    # 2. Outgoing Proposals (sent by this user or their businesses)
    outgoing = (
        db.query(BusinessCollaboration)
        .filter(BusinessCollaboration.sender_user_id == current_user.id)
        .order_by(BusinessCollaboration.created_at.desc())
        .all()
    )

    # If admin, can also view all collaborations for system auditing
    all_collaborations = []
    if current_user.role == "admin":
        all_collaborations = (
            db.query(BusinessCollaboration)
            .order_by(BusinessCollaboration.created_at.desc())
            .limit(50)
            .all()
        )

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")

    return templates.TemplateResponse(
        request=request,
        name="creators/collaborations.html",
        context={
            "request": request,
            "active_page": "collaborations",
            "current_user": current_user,
            "incoming": incoming,
            "outgoing": outgoing,
            "all_collaborations": all_collaborations,
            "csrf_token": csrf_token,
        },
    )


@router.post("/collaborations/{collab_id}/status")
def collaboration_update_status(
    collab_id: int,
    request: Request,
    action: str = Form(...),  # accept, decline, cancel
    notes: Optional[str] = Form(None),
    csrf_token: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update collaboration status:
    - Creator can accept or decline.
    - Business sender can cancel while pending.
    - Admin can perform any transition.
    """
    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        raise HTTPException(status_code=400, detail="Invalid CSRF token.")

    collab = db.query(BusinessCollaboration).filter(BusinessCollaboration.id == collab_id).first()
    if not collab:
        raise HTTPException(status_code=404, detail="Collaboration request not found.")

    action = action.strip().lower()

    # Permissions check
    is_recipient = (current_user.creator_profile and current_user.creator_profile.id == collab.creator_id)
    is_sender = (current_user.id == collab.sender_user_id or (collab.business and collab.business.created_by_id == current_user.id))
    is_admin = (current_user.role == "admin")

    if action in ["accept", "decline"]:
        if not is_recipient and not is_admin:
            raise HTTPException(status_code=403, detail="Only the targeted creator can accept or decline this request.")

        collab.status = "accepted" if action == "accept" else "declined"
        if notes:
            collab.creator_response_notes = notes.strip()

        # Send notification to sender
        notif = Notification(
            recipient_id=collab.sender_user_id,
            sender_id=current_user.id,
            notification_type="collaboration",
            title=f"Collaboration Request {action.capitalize()}ed",
            message=f"{collab.creator.title} has {action}ed your proposal for '{collab.campaign_title}'.",
            link="/collaborations",
        )
        db.add(notif)

    elif action == "cancel":
        if not is_sender and not is_admin:
            raise HTTPException(status_code=403, detail="Only the business sender can cancel this request.")
        if collab.status != "pending":
            raise HTTPException(status_code=400, detail="Only pending collaboration requests can be cancelled.")

        collab.status = "cancelled"
        if notes:
            collab.creator_response_notes = f"Cancelled by sender: {notes.strip()}"

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported collaboration action '{action}'.")

    collab.updated_at = utc_now()
    db.commit()

    return RedirectResponse(url="/collaborations?msg=status_updated", status_code=303)


# ==============================================================================
# 3. REST API ENDPOINTS — CREATORS, BADGES & COLLABORATIONS
# ==============================================================================

@router.get("/api/v1/creators", response_model=List[CreatorProfileOut])
def api_get_creators(
    q: Optional[str] = None,
    category: Optional[str] = None,
    locality: Optional[str] = None,
    verified_only: bool = False,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
):
    """
    Public REST API for querying creator profiles with filters and pagination.
    """
    query = db.query(CreatorProfile).join(User, CreatorProfile.user_id == User.id)

    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(term),
                CreatorProfile.title.ilike(term),
                CreatorProfile.bio.ilike(term),
                CreatorProfile.skills.ilike(term),
                CreatorProfile.craft_category.ilike(term),
                CreatorProfile.locality.ilike(term),
            )
        )

    if category and category != "all":
        query = query.filter(CreatorProfile.craft_category == category.strip())

    if locality and locality != "all":
        query = query.filter(CreatorProfile.locality == locality.strip())

    if verified_only:
        query = query.filter(CreatorProfile.is_verified.is_(True))

    page = max(1, page)
    offset = (page - 1) * per_page

    creators = (
        query.order_by(
            CreatorProfile.is_featured.desc(),
            CreatorProfile.is_verified.desc(),
            CreatorProfile.created_at.desc(),
        )
        .offset(offset)
        .limit(per_page)
        .all()
    )

    out = []
    for c in creators:
        followers_count = db.query(UserFollow).filter(UserFollow.following_id == c.user_id).count()
        posts_count = db.query(CommunityPost).filter(
            CommunityPost.author_id == c.user_id,
            CommunityPost.status == "published",
        ).count()
        item = CreatorProfileOut.from_orm_with_metrics(c, followers_count=followers_count, posts_count=posts_count)
        out.append(item)

    return out


@router.get("/api/v1/creators/{creator_id}", response_model=CreatorProfileOut)
def api_get_creator_detail(
    creator_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve full creator profile details and update internal view count."""
    creator = db.query(CreatorProfile).filter(CreatorProfile.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found.")

    creator.profile_views = (creator.profile_views or 0) + 1
    db.commit()

    followers_count = db.query(UserFollow).filter(UserFollow.following_id == creator.user_id).count()
    posts_count = db.query(CommunityPost).filter(
        CommunityPost.author_id == creator.user_id,
        CommunityPost.status == "published",
    ).count()

    return CreatorProfileOut.from_orm_with_metrics(creator, followers_count=followers_count, posts_count=posts_count)


@router.post("/api/v1/creators/profile", response_model=CreatorProfileOut)
@router.put("/api/v1/creators/profile", response_model=CreatorProfileOut)
def api_save_creator_profile(
    payload: CreatorProfileCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create or update current authenticated user's creator profile.
    Automatically validates social URLs and cleans input.
    """
    profile = db.query(CreatorProfile).filter(CreatorProfile.user_id == current_user.id).first()
    if not profile:
        profile = CreatorProfile(user_id=current_user.id)
        db.add(profile)

    profile.title = payload.title.strip()
    profile.craft_category = payload.craft_category.strip()
    profile.bio = payload.bio.strip()
    profile.skills = payload.skills.strip() if payload.skills else None
    profile.locality = payload.locality.strip() if payload.locality else "Barabanki"
    profile.languages = payload.languages.strip() if payload.languages else "Hindi, Awadhi"
    profile.content_categories = payload.content_categories.strip() if payload.content_categories else None
    profile.portfolio_url = str(payload.portfolio_url) if payload.portfolio_url else None
    profile.profile_photo = str(payload.profile_photo) if payload.profile_photo else None

    # Public social URLs (validated by schema)
    profile.instagram = str(payload.instagram) if payload.instagram else None
    profile.youtube = str(payload.youtube) if payload.youtube else None
    profile.facebook = str(payload.facebook) if payload.facebook else None
    profile.linkedin = str(payload.linkedin) if payload.linkedin else None
    profile.twitter_x = str(payload.twitter_x) if payload.twitter_x else None
    profile.github = str(payload.github) if payload.github else None

    if current_user.role == "resident":
        current_user.role = "creator"

    db.commit()
    db.refresh(profile)

    followers_count = db.query(UserFollow).filter(UserFollow.following_id == profile.user_id).count()
    posts_count = db.query(CommunityPost).filter(
        CommunityPost.author_id == profile.user_id,
        CommunityPost.status == "published",
    ).count()

    return CreatorProfileOut.from_orm_with_metrics(profile, followers_count=followers_count, posts_count=posts_count)


@router.post("/api/v1/creators/{creator_id}/collaborations", response_model=BusinessCollaborationOut, status_code=status.HTTP_201_CREATED)
def api_create_collaboration(
    creator_id: int,
    payload: BusinessCollaborationCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit a business collaboration proposal via REST API.
    Enforces business ownership and prevents duplicate pending proposals.
    """
    creator = db.query(CreatorProfile).filter(CreatorProfile.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found.")

    if creator.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot collaborate with yourself.")

    business = db.query(Business).filter(Business.id == payload.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")

    if business.created_by_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You do not own this business.")

    # Duplicate pending check
    existing = db.query(BusinessCollaboration).filter(
        BusinessCollaboration.business_id == payload.business_id,
        BusinessCollaboration.creator_id == creator_id,
        BusinessCollaboration.status == "pending",
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="A pending collaboration proposal is already active between this business and creator.",
        )

    collab = BusinessCollaboration(
        business_id=payload.business_id,
        creator_id=creator.id,
        sender_user_id=current_user.id,
        campaign_title=payload.campaign_title.strip(),
        campaign_description=payload.campaign_description.strip(),
        proposed_deliverables=payload.proposed_deliverables.strip(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        budget_range=payload.budget_range,
        contact_preference=payload.contact_preference,
        contact_details=payload.contact_details.strip(),
        status="pending",
    )
    db.add(collab)

    # Notification
    notif = Notification(
        recipient_id=creator.user_id,
        sender_id=current_user.id,
        notification_type="collaboration",
        title="New Business Collaboration Request",
        message=f"{business.name} submitted a collaboration proposal: '{payload.campaign_title}'",
        link="/collaborations",
    )
    db.add(notif)
    db.commit()
    db.refresh(collab)

    return BusinessCollaborationOut.from_orm_with_names(collab)


@router.get("/api/v1/collaborations", response_model=List[BusinessCollaborationOut])
def api_get_collaborations(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve user's incoming and outgoing collaborations.
    Admins can view all platform collaborations.
    """
    if current_user.role == "admin":
        collabs = db.query(BusinessCollaboration).order_by(BusinessCollaboration.created_at.desc()).all()
    else:
        creator_id = current_user.creator_profile.id if current_user.creator_profile else -1
        collabs = (
            db.query(BusinessCollaboration)
            .filter(
                or_(
                    BusinessCollaboration.creator_id == creator_id,
                    BusinessCollaboration.sender_user_id == current_user.id,
                )
            )
            .order_by(BusinessCollaboration.created_at.desc())
            .all()
        )

    return [BusinessCollaborationOut.from_orm_with_names(c) for c in collabs]


@router.patch("/api/v1/collaborations/{collab_id}/status", response_model=BusinessCollaborationOut)
def api_update_collaboration_status(
    collab_id: int,
    payload: BusinessCollaborationStatusUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update collaboration proposal status (accept, decline, cancel).
    Restricted to authorized parties only.
    """
    collab = db.query(BusinessCollaboration).filter(BusinessCollaboration.id == collab_id).first()
    if not collab:
        raise HTTPException(status_code=404, detail="Collaboration request not found.")

    creator_obj = db.query(CreatorProfile).filter(CreatorProfile.id == collab.creator_id).first()
    is_recipient = (
        (current_user.creator_profile and current_user.creator_profile.id == collab.creator_id)
        or (creator_obj and creator_obj.user_id == current_user.id)
    )
    is_sender = (
        current_user.id == collab.sender_user_id
        or (collab.business and collab.business.created_by_id == current_user.id)
    )
    is_admin = (current_user.role == "admin")

    target_status = payload.status.lower()

    if target_status in ["accepted", "declined"]:
        if not is_recipient and not is_admin:
            raise HTTPException(status_code=403, detail="Only recipient creator can accept or decline.")
    elif target_status == "cancelled":
        if not is_sender and not is_admin:
            raise HTTPException(status_code=403, detail="Only sender business can cancel.")
        if collab.status != "pending":
            raise HTTPException(status_code=400, detail="Only pending requests can be cancelled.")
    else:
        raise HTTPException(status_code=400, detail=f"Invalid status '{payload.status}'.")

    collab.status = target_status
    notes = payload.creator_response_notes or payload.response_notes
    if notes:
        collab.creator_response_notes = notes.strip()
    collab.updated_at = utc_now()

    # Notify sender or creator
    notif_target = collab.sender_user_id if is_recipient else (creator_obj.user_id if creator_obj else collab.creator_id)
    notif = Notification(
        recipient_id=notif_target,
        sender_id=current_user.id,
        notification_type="collaboration",
        title=f"Collaboration Status: {target_status.capitalize()}",
        message=f"Proposal for '{collab.campaign_title}' status changed to {target_status}.",
        link="/collaborations",
    )
    db.add(notif)
    db.commit()
    db.refresh(collab)

    return BusinessCollaborationOut.from_orm_with_names(collab)


# ==============================================================================
# 4. ADMIN VERIFICATION & BADGE WORKFLOW
# ==============================================================================

@router.post("/api/v1/admin/creators/{creator_id}/verify", response_model=CreatorProfileOut)
def api_admin_verify_creator(
    creator_id: int,
    payload: CreatorVerificationUpdate,
    current_admin = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Admin endpoint to grant or revoke verification badges for local creators.
    Permitted badges: Verified Creator, Master Artisan, Community Voice, Official Partner.
    """
    creator = db.query(CreatorProfile).filter(CreatorProfile.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found.")

    if payload.is_verified and payload.verification_badge:
        if payload.verification_badge not in VERIFICATION_BADGES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid badge. Permitted badges: {list(VERIFICATION_BADGES.keys())}",
            )

    creator.is_verified = payload.is_verified
    creator.verification_badge = payload.verification_badge if payload.is_verified else None
    if payload.verification_notes is not None:
        creator.verification_notes = payload.verification_notes.strip()

    creator.updated_at = utc_now()
    db.commit()
    db.refresh(creator)

    # Notify creator of badge update
    notif = Notification(
        recipient_id=creator.user_id,
        sender_id=current_admin.id,
        notification_type="system",
        title="Creator Verification Status Updated",
        message=(
            f"Congratulations! You were awarded the '{creator.verification_badge}' badge."
            if creator.is_verified
            else "Your creator verification status was updated by administration."
        ),
        link=f"/creators/{creator.id}",
    )
    db.add(notif)
    db.commit()

    followers_count = db.query(UserFollow).filter(UserFollow.following_id == creator.user_id).count()
    posts_count = db.query(CommunityPost).filter(
        CommunityPost.author_id == creator.user_id,
        CommunityPost.status == "published",
    ).count()

    return CreatorProfileOut.from_orm_with_metrics(creator, followers_count=followers_count, posts_count=posts_count)


@router.post("/api/v1/admin/creators/{creator_id}/feature")
def api_admin_feature_creator(
    creator_id: int,
    current_admin = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin endpoint to toggle featured showcase spotlight for a creator."""
    creator = db.query(CreatorProfile).filter(CreatorProfile.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found.")

    creator.is_featured = not creator.is_featured
    creator.updated_at = utc_now()
    db.commit()

    return {"id": creator.id, "is_featured": creator.is_featured}


@router.post("/admin/creators/{creator_id}/verify")
def admin_web_verify_creator(
    creator_id: int,
    request: Request,
    is_verified: bool = Form(False),
    verification_badge: Optional[str] = Form(None),
    verification_notes: Optional[str] = Form(None),
    csrf_token: Optional[str] = Form(None),
    current_admin = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin web action for granting/revoking creator verification badges."""
    session_id = request.client.host if request.client else "bbk_admin"
    if not validate_csrf_token(csrf_token, session_id):
        raise HTTPException(status_code=400, detail="Invalid CSRF token.")

    creator = db.query(CreatorProfile).filter(CreatorProfile.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found.")

    if is_verified and verification_badge and verification_badge not in VERIFICATION_BADGES:
        raise HTTPException(status_code=400, detail="Invalid badge type.")

    creator.is_verified = is_verified
    creator.verification_badge = verification_badge if is_verified else None
    creator.verification_notes = verification_notes.strip() if verification_notes else None
    creator.updated_at = utc_now()
    db.commit()

    return RedirectResponse(url="/admin/listings?creator_updated=1", status_code=303)


@router.post("/admin/creators/{creator_id}/toggle-feature")
def admin_web_toggle_feature(
    creator_id: int,
    request: Request,
    csrf_token: Optional[str] = Form(None),
    current_admin = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin web action for toggling featured status."""
    session_id = request.client.host if request.client else "bbk_admin"
    if not validate_csrf_token(csrf_token, session_id):
        raise HTTPException(status_code=400, detail="Invalid CSRF token.")

    creator = db.query(CreatorProfile).filter(CreatorProfile.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found.")

    creator.is_featured = not creator.is_featured
    creator.updated_at = utc_now()
    db.commit()

    return RedirectResponse(url="/admin/listings?featured_toggled=1", status_code=303)
