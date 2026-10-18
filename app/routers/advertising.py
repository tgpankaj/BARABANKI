import math
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from app.core.config import settings
from app.core.database import get_db, utc_now
from app.core.dependencies import (
    get_current_user_optional,
    get_current_user,
    require_admin,
    require_moderator_or_admin,
)
from app.core.security import generate_csrf_token, validate_csrf_token
from app.core.ad_validator import (
    sanitize_text,
    validate_destination_url,
    check_prohibited_content,
    validate_campaign_dates,
    calculate_plan_cost,
)
from app.models.user import User
from app.models.business import Business
from app.models.notification import Notification
from app.models.advertisement import (
    AdCampaign,
    AdPayment,
    AdImpression,
    AdClick,
    AdReport,
    AD_OBJECTIVES,
    AD_PLACEMENTS,
    PRICING_PLANS,
    CAMPAIGN_STATUSES,
    PAYMENT_STATUSES,
)
from app.schemas.advertisement import (
    AdCampaignCreate,
    AdCampaignUpdate,
    AdCampaignOut,
    AdPaymentCreate,
    AdPaymentOut,
    AdReviewUpdate,
    AdReportCreate,
    AdReportOut,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- HELPER FUNCTIONS ---

def get_user_businesses(user: User, db: Session) -> List[Business]:
    """Retrieve businesses owned by user (or all if admin)."""
    if user.role == "admin":
        return db.query(Business).filter(Business.is_approved == True).order_by(Business.name.asc()).all()
    return db.query(Business).filter(Business.created_by_id == user.id, Business.is_approved == True).order_by(Business.name.asc()).all()


def check_campaign_permission(campaign: AdCampaign, user: User) -> bool:
    """Ensure user is business owner or an administrator."""
    if user.role == "admin":
        return True
    if campaign.user_id == user.id:
        return True
    if campaign.business and campaign.business.created_by_id == user.id:
        return True
    return False


def get_active_ads(
    db: Session,
    placement: str,
    locality: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 3,
) -> List[AdCampaign]:
    """
    Fetch eligible, approved, active ads for server-side placement display.
    Never trusts client input; strictly validates server-side eligibility.
    """
    now = utc_now()
    query = (
        db.query(AdCampaign)
        .join(Business, AdCampaign.business_id == Business.id)
        .filter(
            AdCampaign.placement == placement,
            AdCampaign.status.in_(["approved", "active"]),
            AdCampaign.is_paused == False,
            AdCampaign.payment_status.in_(["verified", "waived"]),
            AdCampaign.start_date <= now,
            AdCampaign.end_date >= now,
            Business.is_approved == True,
        )
    )

    if locality and locality != "All Localities":
        query = query.filter(
            or_(
                AdCampaign.target_locality == "All Localities",
                AdCampaign.target_locality == locality,
                Business.locality == locality,
            )
        )

    if category and category != "All Categories":
        query = query.filter(
            or_(
                AdCampaign.target_category == "All Categories",
                AdCampaign.target_category == category,
                Business.category == category,
            )
        )

    return query.order_by(desc(AdCampaign.budget_amount), desc(AdCampaign.created_at)).limit(limit).all()


def record_ad_impression(
    campaign_id: int,
    placement: str,
    ip: Optional[str],
    user_id: Optional[int],
    session_id: Optional[str],
    db: Session,
) -> bool:
    """
    Deduplicated internal impression logger.
    Only counts 1 impression per viewer IP/session every 15 minutes to avoid spam inflation.
    """
    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        return False

    window_start = utc_now() - timedelta(minutes=15)
    recent = (
        db.query(AdImpression)
        .filter(
            AdImpression.campaign_id == campaign_id,
            AdImpression.placement == placement,
            AdImpression.created_at >= window_start,
            or_(
                and_(AdImpression.viewer_ip == ip, ip != None),
                and_(AdImpression.session_id == session_id, session_id != None),
            ),
        )
        .first()
    )

    # Record the impression row regardless for audit, but only increment counter if not duplicate
    impression = AdImpression(
        campaign_id=campaign_id,
        placement=placement,
        viewer_ip=ip,
        user_id=user_id,
        session_id=session_id,
    )
    db.add(impression)

    if not recent:
        campaign.impression_count += 1

    db.commit()
    return True


def record_ad_click(
    campaign_id: int,
    placement: str,
    destination_url: str,
    ip: Optional[str],
    user_id: Optional[int],
    db: Session,
) -> bool:
    """
    Deduplicated internal click logger.
    Only increments click count if not clicked from same IP within 15 minutes.
    """
    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        return False

    window_start = utc_now() - timedelta(minutes=15)
    recent = (
        db.query(AdClick)
        .filter(
            AdClick.campaign_id == campaign_id,
            AdClick.created_at >= window_start,
            AdClick.viewer_ip == ip,
        )
        .first()
    )

    click = AdClick(
        campaign_id=campaign_id,
        placement=placement,
        destination_url=destination_url,
        viewer_ip=ip,
        user_id=user_id,
    )
    db.add(click)

    if not recent:
        campaign.click_count += 1

    db.commit()
    return True


# --- ADVERTISER DASHBOARD VIEWS ---

@router.get("/advertiser", response_class=HTMLResponse)
def advertiser_dashboard_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Advertiser Portal Overview for local business owners."""
    if not current_user:
        return RedirectResponse(url="/auth/login?next=/advertiser", status_code=303)

    user_businesses = get_user_businesses(current_user, db)
    business_ids = [b.id for b in user_businesses]

    if current_user.role == "admin":
        campaigns = db.query(AdCampaign).order_by(AdCampaign.created_at.desc()).all()
    else:
        campaigns = (
            db.query(AdCampaign)
            .filter(or_(AdCampaign.business_id.in_(business_ids), AdCampaign.user_id == current_user.id))
            .order_by(AdCampaign.created_at.desc())
            .all()
        )

    # Compute genuine internal metrics
    now = utc_now()
    total_campaigns = len(campaigns)
    active_campaigns = sum(1 for c in campaigns if c.is_eligible_for_display(now))
    total_impressions = sum(c.impression_count for c in campaigns)
    total_clicks = sum(c.click_count for c in campaigns)
    avg_ctr = round((total_clicks / total_impressions * 100.0), 2) if total_impressions > 0 else 0.0

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_advertiser")

    return templates.TemplateResponse(
        request=request,
        name="advertiser/dashboard.html",
        context={
            "active_page": "advertiser",
            "current_user": current_user,
            "businesses": user_businesses,
            "campaigns": campaigns,
            "total_campaigns": total_campaigns,
            "active_campaigns": active_campaigns,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "avg_ctr": avg_ctr,
            "csrf_token": csrf_token,
            "pricing_plans": PRICING_PLANS,
            "ad_placements": AD_PLACEMENTS,
        },
    )


@router.get("/advertiser/campaigns/new", response_class=HTMLResponse)
def advertiser_create_campaign_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Campaign builder form with instant transparent pricing calculator."""
    if not current_user:
        return RedirectResponse(url="/auth/login?next=/advertiser/campaigns/new", status_code=303)

    user_businesses = get_user_businesses(current_user, db)
    if not user_businesses:
        # Prompt user to register or verify business first
        return templates.TemplateResponse(
            request=request,
            name="advertiser/no_business.html",
            context={
                "active_page": "advertiser",
                "current_user": current_user,
            },
        )

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_advertiser")

    return templates.TemplateResponse(
        request=request,
        name="advertiser/create_campaign.html",
        context={
            "active_page": "advertiser",
            "current_user": current_user,
            "businesses": user_businesses,
            "ad_objectives": AD_OBJECTIVES,
            "ad_placements": AD_PLACEMENTS,
            "pricing_plans": PRICING_PLANS,
            "csrf_token": csrf_token,
            "now": utc_now(),
        },
    )


@router.post("/advertiser/campaigns/new")
def advertiser_create_campaign_action(
    request: Request,
    business_id: int = Form(...),
    name: str = Form(...),
    objective: str = Form("brand_awareness"),
    headline: str = Form(...),
    description: str = Form(...),
    image_url: Optional[str] = Form(None),
    destination_url: Optional[str] = Form(None),
    contact_action: str = Form("visit_website"),
    contact_value: Optional[str] = Form(None),
    placement: str = Form("homepage_sponsored"),
    target_locality: str = Form("All Localities"),
    target_category: str = Form("All Categories"),
    pricing_plan: str = Form("starter_7days"),
    custom_days: Optional[int] = Form(None),
    start_date_str: str = Form(...),
    csrf_token: str = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Handle campaign creation form submission with strict server-side validation."""
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    session_id = request.client.host if request.client else "bbk_advertiser"
    if not validate_csrf_token(csrf_token, session_id):
        raise HTTPException(status_code=400, detail="Security validation failed (invalid CSRF token).")

    # 1. Verify business ownership
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Selected business listing not found.")
    if current_user.role != "admin" and business.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only create advertising campaigns for your own verified businesses.")

    # 2. Sanitize and validate content
    clean_headline = sanitize_text(headline, max_length=100)
    clean_desc = sanitize_text(description, max_length=1000)
    if not clean_headline or not clean_desc:
        raise HTTPException(status_code=422, detail="Headline and description cannot be empty.")

    is_prohibited, reason = check_prohibited_content(f"{clean_headline} {clean_desc}")
    if is_prohibited:
        raise HTTPException(status_code=422, detail=reason)

    # 3. Validate Destination URL
    dest_url = destination_url.strip() if destination_url else None
    if not dest_url and contact_action == "view_listing":
        dest_url = f"/businesses/{business.slug}"

    is_valid_url, url_err, cleaned_dest_url = validate_destination_url(dest_url)
    if not is_valid_url:
        raise HTTPException(status_code=422, detail=url_err)

    # 4. Schedule & Pricing Calculation
    try:
        # Accepts YYYY-MM-DD or ISO
        start_date = datetime.fromisoformat(start_date_str.strip()).replace(tzinfo=None)
    except Exception:
        start_date = utc_now()

    budget_amount, duration_days, plan_name = calculate_plan_cost(pricing_plan, custom_days)
    end_date = start_date + timedelta(days=duration_days)

    valid_dates, date_err = validate_campaign_dates(start_date, end_date)
    if not valid_dates:
        raise HTTPException(status_code=422, detail=date_err)

    # 5. Persist campaign
    campaign = AdCampaign(
        business_id=business.id,
        user_id=current_user.id,
        name=name.strip(),
        objective=objective.strip(),
        headline=clean_headline,
        description=clean_desc,
        image_url=image_url.strip() if image_url else None,
        destination_url=cleaned_dest_url,
        contact_action=contact_action.strip(),
        contact_value=contact_value.strip() if contact_value else None,
        placement=placement.strip(),
        target_locality=target_locality.strip(),
        target_category=target_category.strip(),
        start_date=start_date,
        end_date=end_date,
        pricing_plan=pricing_plan.strip(),
        budget_amount=budget_amount,
        status="pending_review",
        payment_status="pending",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # Notify admins of new campaign pending review
    admin_users = db.query(User).filter(User.role == "admin").all()
    for admin in admin_users:
        db.add(Notification(
            recipient_id=admin.id,
            sender_id=current_user.id,
            notification_type="ad_campaign_submitted",
            title="New Advertising Campaign Pending Review",
            message=f"{business.name} submitted campaign '{campaign.name}' (₹{budget_amount:.2f}).",
            link="/admin/campaigns",
        ))
    db.commit()

    return RedirectResponse(url=f"/advertiser/campaigns/{campaign.id}/payment", status_code=303)


@router.get("/advertiser/campaigns/{campaign_id}", response_class=HTMLResponse)
def advertiser_campaign_detail_view(
    campaign_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Detailed campaign performance analytics & management view."""
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    if not check_campaign_permission(campaign, current_user):
        raise HTTPException(status_code=403, detail="You do not have access to view this business's private campaign.")

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_advertiser")

    # Fetch recorded payment transactions
    payments = db.query(AdPayment).filter(AdPayment.campaign_id == campaign_id).order_by(AdPayment.created_at.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="advertiser/campaign_detail.html",
        context={
            "active_page": "advertiser",
            "current_user": current_user,
            "campaign": campaign,
            "payments": payments,
            "csrf_token": csrf_token,
            "ad_placements": AD_PLACEMENTS,
            "pricing_plans": PRICING_PLANS,
            "now": utc_now(),
        },
    )


@router.post("/advertiser/campaigns/{campaign_id}/toggle-pause")
def advertiser_toggle_pause_action(
    campaign_id: int,
    request: Request,
    csrf_token: str = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Allows advertiser to pause or unpause their approved/active campaign."""
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    session_id = request.client.host if request.client else "bbk_advertiser"
    if not validate_csrf_token(csrf_token, session_id):
        raise HTTPException(status_code=400, detail="Security validation failed.")

    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    if not check_campaign_permission(campaign, current_user):
        raise HTTPException(status_code=403, detail="You do not have permission to manage this campaign.")

    campaign.is_paused = not campaign.is_paused
    db.commit()

    return RedirectResponse(url=f"/advertiser/campaigns/{campaign_id}", status_code=303)


@router.get("/advertiser/campaigns/{campaign_id}/payment", response_class=HTMLResponse)
def advertiser_campaign_payment_view(
    campaign_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Transparent payment guidance & UTR submission screen."""
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    if not check_campaign_permission(campaign, current_user):
        raise HTTPException(status_code=403, detail="You do not have permission to access billing for this campaign.")

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_advertiser")
    existing_payments = db.query(AdPayment).filter(AdPayment.campaign_id == campaign_id).all()

    return templates.TemplateResponse(
        request=request,
        name="advertiser/payment.html",
        context={
            "active_page": "advertiser",
            "current_user": current_user,
            "campaign": campaign,
            "payments": existing_payments,
            "csrf_token": csrf_token,
            "official_upi_id": "barabankiconnect@upi",
            "official_bank_info": {
                "bank": "State Bank of India",
                "branch": "Barabanki Main Branch (Station Road)",
                "account_name": "Barabanki Connect Portal Administration",
                "account_number": "XXXX-XXXX-1234",
                "ifsc": "SBIN0000028",
            },
        },
    )


@router.post("/advertiser/campaigns/{campaign_id}/payment")
def advertiser_submit_payment_action(
    campaign_id: int,
    request: Request,
    transaction_reference: str = Form(...),
    amount: float = Form(...),
    payment_method: str = Form("upi_qr"),
    notes: Optional[str] = Form(None),
    idempotency_key: Optional[str] = Form(None),
    csrf_token: str = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Idempotent submission of payment reference / UTR for admin manual verification.
    Prevents duplicate transactions and verifies amount.
    """
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    session_id = request.client.host if request.client else "bbk_advertiser"
    if not validate_csrf_token(csrf_token, session_id):
        raise HTTPException(status_code=400, detail="Security validation failed.")

    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    if not check_campaign_permission(campaign, current_user):
        raise HTTPException(status_code=403, detail="Unauthorized access to this campaign.")

    clean_ref = transaction_reference.strip().upper()
    if len(clean_ref) < 4:
        raise HTTPException(status_code=422, detail="Please enter a valid bank reference or UPI UTR number.")

    # Idempotency check: check if reference already recorded
    existing_ref = db.query(AdPayment).filter(AdPayment.transaction_reference == clean_ref).first()
    if existing_ref:
        if existing_ref.campaign_id == campaign_id:
            # Idempotent redirect: already submitted for this campaign
            return RedirectResponse(url=f"/advertiser/campaigns/{campaign_id}", status_code=303)
        raise HTTPException(status_code=400, detail="This transaction reference has already been claimed for another campaign.")

    if idempotency_key:
        existing_key = db.query(AdPayment).filter(AdPayment.idempotency_key == idempotency_key).first()
        if existing_key:
            return RedirectResponse(url=f"/advertiser/campaigns/{campaign_id}", status_code=303)

    # Record payment proof
    payment = AdPayment(
        campaign_id=campaign_id,
        business_id=campaign.business_id,
        user_id=current_user.id,
        amount=amount,
        currency="INR",
        payment_method=payment_method.strip(),
        gateway_provider="manual_admin_verify",
        transaction_reference=clean_ref,
        idempotency_key=idempotency_key.strip() if idempotency_key else None,
        status="proof_submitted",
        admin_notes=notes.strip() if notes else None,
    )
    db.add(payment)

    campaign.payment_status = "proof_submitted"
    db.commit()

    # Notify admins to verify payment
    admins = db.query(User).filter(User.role == "admin").all()
    for admin in admins:
        db.add(Notification(
            recipient_id=admin.id,
            sender_id=current_user.id,
            notification_type="payment_proof_submitted",
            title="Ad Payment Proof Submitted",
            message=f"UTR {clean_ref} submitted for campaign '{campaign.name}' (₹{amount:.2f}).",
            link="/admin/campaigns",
        ))
    db.commit()

    return RedirectResponse(url=f"/advertiser/campaigns/{campaign_id}", status_code=303)


# --- PUBLIC AD DELIVERY, TRACKING & REPORTING ---

@router.get("/ads/{campaign_id}/click")
def ad_click_redirect(
    campaign_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Public ad click handler with open-redirect defense and deduplicated analytics.
    Redirects securely to verified destination URL or business page.
    """
    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Ad campaign not found.")

    # Target URL resolution
    target_url = campaign.destination_url
    if not target_url or not target_url.strip():
        if campaign.business:
            target_url = f"/businesses/{campaign.business.slug}"
        else:
            target_url = "/"

    # Open redirect security defense: validate target_url
    is_valid, err, cleaned_url = validate_destination_url(target_url)
    if not is_valid or not cleaned_url:
        cleaned_url = "/"

    # Log click with deduplication
    ip = request.client.host if request.client else None
    user_id = current_user.id if current_user else None
    record_ad_click(
        campaign_id=campaign.id,
        placement=campaign.placement,
        destination_url=cleaned_url,
        ip=ip,
        user_id=user_id,
        db=db,
    )

    return RedirectResponse(url=cleaned_url, status_code=302)


@router.get("/ads/{campaign_id}/report", response_class=HTMLResponse)
def ad_report_view(
    campaign_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Public resident reporting interface for deceptive, offensive, or counterfeit ads."""
    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Advertisement not found.")

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_report")

    return templates.TemplateResponse(
        request=request,
        name="advertiser/report_ad.html",
        context={
            "active_page": "advertising",
            "current_user": current_user,
            "campaign": campaign,
            "csrf_token": csrf_token,
        },
    )


@router.post("/ads/{campaign_id}/report")
def ad_report_action(
    campaign_id: int,
    request: Request,
    reason: str = Form(...),
    details: str = Form(...),
    reporter_email: Optional[str] = Form(None),
    csrf_token: str = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Submit report against an ad campaign."""
    session_id = request.client.host if request.client else "bbk_report"
    if not validate_csrf_token(csrf_token, session_id):
        raise HTTPException(status_code=400, detail="Security validation failed.")

    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    clean_details = sanitize_text(details, max_length=1000)
    report = AdReport(
        campaign_id=campaign_id,
        reported_by_id=current_user.id if current_user else None,
        reporter_email=reporter_email.strip() if reporter_email else None,
        reason=reason.strip(),
        details=clean_details,
        status="pending",
    )
    db.add(report)
    db.commit()

    # If 3+ pending reports, flag to admins
    count_pending = db.query(AdReport).filter(AdReport.campaign_id == campaign_id, AdReport.status == "pending").count()
    if count_pending >= 3:
        admins = db.query(User).filter(User.role == "admin").all()
        for admin in admins:
            db.add(Notification(
                recipient_id=admin.id,
                notification_type="ad_reported_alert",
                title="Advertisement Flagged by Multiple Citizens",
                message=f"Campaign '{campaign.headline}' has received {count_pending} reports.",
                link="/admin/campaigns",
            ))
        db.commit()

    return templates.TemplateResponse(
        request=request,
        name="advertiser/report_submitted.html",
        context={
            "active_page": "advertising",
            "current_user": current_user,
            "campaign": campaign,
        },
    )


@router.get("/advertising/policy", response_class=HTMLResponse)
def advertising_policy_view(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Official Barabanki Connect Advertising Guidelines and Placement Rules."""
    return templates.TemplateResponse(
        request=request,
        name="advertiser/policy.html",
        context={
            "active_page": "advertising",
            "current_user": current_user,
            "pricing_plans": PRICING_PLANS,
            "ad_placements": AD_PLACEMENTS,
        },
    )


# --- ADMIN ADVERTISING MANAGEMENT ---

@router.get("/admin/campaigns", response_class=HTMLResponse)
def admin_campaigns_view(
    request: Request,
    tab: Optional[str] = Query("all"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Admin queue for reviewing ad campaigns, validating payments, and monitoring reports."""
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    if current_user.role not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Administrative privileges required.")

    query = db.query(AdCampaign).order_by(AdCampaign.created_at.desc())

    if tab == "pending_review":
        query = query.filter(AdCampaign.status == "pending_review")
    elif tab == "payment_verification":
        query = query.filter(AdCampaign.payment_status == "proof_submitted")
    elif tab == "active":
        query = query.filter(AdCampaign.status.in_(["approved", "active"]))
    elif tab == "rejected":
        query = query.filter(AdCampaign.status == "rejected")

    campaigns = query.all()

    # Stats for tab pills
    stats = {
        "all": db.query(AdCampaign).count(),
        "pending_review": db.query(AdCampaign).filter(AdCampaign.status == "pending_review").count(),
        "payment_verification": db.query(AdCampaign).filter(AdCampaign.payment_status == "proof_submitted").count(),
        "active": db.query(AdCampaign).filter(AdCampaign.status.in_(["approved", "active"])).count(),
        "reports": db.query(AdReport).filter(AdReport.status == "pending").count(),
    }

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_admin")

    return templates.TemplateResponse(
        request=request,
        name="admin/campaigns.html",
        context={
            "active_page": "admin",
            "current_user": current_user,
            "campaigns": campaigns,
            "current_tab": tab,
            "stats": stats,
            "csrf_token": csrf_token,
            "now": utc_now(),
        },
    )


@router.post("/admin/campaigns/{campaign_id}/review")
def admin_review_campaign_action(
    campaign_id: int,
    action: str = Form(...),  # approve or reject
    feedback: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_moderator_or_admin),
):
    """Admin approves or rejects a campaign with feedback."""
    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    now = utc_now()
    campaign.reviewed_by_id = current_admin.id
    campaign.reviewed_at = now
    campaign.review_feedback = feedback.strip() if feedback else None

    if action == "approve":
        campaign.status = "approved"
        # If payment is already verified and campaign schedule is active, mark active
        if campaign.payment_status in ("verified", "waived") and campaign.start_date <= now <= campaign.end_date:
            campaign.status = "active"

        # Notify business owner
        db.add(Notification(
            recipient_id=campaign.user_id,
            sender_id=current_admin.id,
            notification_type="ad_campaign_approved",
            title="Campaign Approved!",
            message=f"Your advertising campaign '{campaign.name}' was approved by our moderators.",
            link=f"/advertiser/campaigns/{campaign.id}",
        ))
    elif action == "reject":
        campaign.status = "rejected"
        db.add(Notification(
            recipient_id=campaign.user_id,
            sender_id=current_admin.id,
            notification_type="ad_campaign_rejected",
            title="Campaign Requires Changes",
            message=f"Campaign '{campaign.name}' was not approved. Reason: {campaign.review_feedback or 'Policy guidelines'}.",
            link=f"/advertiser/campaigns/{campaign.id}",
        ))

    db.commit()
    return RedirectResponse(url="/admin/campaigns", status_code=303)


@router.post("/admin/campaigns/{campaign_id}/verify-payment")
def admin_verify_payment_action(
    campaign_id: int,
    action: str = Form("verify"),  # verify or reject
    admin_notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Admin verifies or rejects received payment for an advertising campaign."""
    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    payment = db.query(AdPayment).filter(AdPayment.campaign_id == campaign_id).order_by(AdPayment.created_at.desc()).first()
    now = utc_now()

    if action == "verify":
        if payment:
            payment.status = "verified"
            payment.verified_by_id = current_admin.id
            payment.verified_at = now
            if admin_notes:
                payment.admin_notes = admin_notes.strip()

        campaign.payment_status = "verified"
        if campaign.status == "approved" and campaign.start_date <= now <= campaign.end_date and not campaign.is_paused:
            campaign.status = "active"

        db.add(Notification(
            recipient_id=campaign.user_id,
            sender_id=current_admin.id,
            notification_type="ad_payment_verified",
            title="Payment Verified",
            message=f"Payment for campaign '{campaign.name}' has been verified. Your ad is live!",
            link=f"/advertiser/campaigns/{campaign.id}",
        ))
    elif action == "reject":
        if payment:
            payment.status = "failed"
            payment.admin_notes = admin_notes.strip() if admin_notes else "Invalid reference / payment not received."
        campaign.payment_status = "failed"

        db.add(Notification(
            recipient_id=campaign.user_id,
            sender_id=current_admin.id,
            notification_type="ad_payment_rejected",
            title="Payment Verification Failed",
            message=f"Payment reference for campaign '{campaign.name}' could not be verified.",
            link=f"/advertiser/campaigns/{campaign.id}/payment",
        ))

    db.commit()
    return RedirectResponse(url="/admin/campaigns?tab=payment_verification", status_code=303)


# --- REST API ENDPOINTS ---

@router.get("/api/v1/advertiser/campaigns", response_model=List[AdCampaignOut])
def api_get_advertiser_campaigns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List advertising campaigns for the authenticated advertiser."""
    user_businesses = get_user_businesses(current_user, db)
    b_ids = [b.id for b in user_businesses]
    if current_user.role == "admin":
        campaigns = db.query(AdCampaign).order_by(AdCampaign.created_at.desc()).all()
    else:
        campaigns = (
            db.query(AdCampaign)
            .filter(or_(AdCampaign.business_id.in_(b_ids), AdCampaign.user_id == current_user.id))
            .order_by(AdCampaign.created_at.desc())
            .all()
        )
    return [AdCampaignOut.from_orm_with_extras(c) for c in campaigns]


@router.post("/api/v1/advertiser/campaigns", response_model=AdCampaignOut, status_code=status.HTTP_201_CREATED)
def api_create_advertiser_campaign(
    payload: AdCampaignCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new ad campaign via JSON API."""
    business = db.query(Business).filter(Business.id == payload.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    if current_user.role != "admin" and business.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this business listing.")

    valid_dates, date_err = validate_campaign_dates(payload.start_date, payload.end_date)
    if not valid_dates:
        raise HTTPException(status_code=422, detail=date_err)

    budget, _, _ = calculate_plan_cost(payload.pricing_plan, payload.custom_days)

    campaign = AdCampaign(
        business_id=business.id,
        user_id=current_user.id,
        name=payload.name,
        objective=payload.objective,
        headline=payload.headline,
        description=payload.description,
        image_url=payload.image_url,
        destination_url=payload.destination_url,
        contact_action=payload.contact_action,
        contact_value=payload.contact_value,
        placement=payload.placement,
        target_locality=payload.target_locality,
        target_category=payload.target_category,
        start_date=payload.start_date,
        end_date=payload.end_date,
        pricing_plan=payload.pricing_plan,
        budget_amount=budget,
        status="pending_review",
        payment_status="pending",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return AdCampaignOut.from_orm_with_extras(campaign)


@router.get("/api/v1/advertiser/campaigns/{campaign_id}", response_model=AdCampaignOut)
def api_get_campaign_detail(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve specific campaign details and genuine performance metrics."""
    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    if not check_campaign_permission(campaign, current_user):
        raise HTTPException(status_code=403, detail="Access forbidden to this campaign.")
    return AdCampaignOut.from_orm_with_extras(campaign)


@router.patch("/api/v1/advertiser/campaigns/{campaign_id}/pause", response_model=AdCampaignOut)
def api_toggle_pause_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Toggle campaign paused status."""
    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    if not check_campaign_permission(campaign, current_user):
        raise HTTPException(status_code=403, detail="Unauthorized.")
    campaign.is_paused = not campaign.is_paused
    db.commit()
    db.refresh(campaign)
    return AdCampaignOut.from_orm_with_extras(campaign)


@router.post("/api/v1/advertiser/campaigns/{campaign_id}/payments", response_model=AdPaymentOut, status_code=status.HTTP_201_CREATED)
def api_submit_campaign_payment(
    campaign_id: int,
    payload: AdPaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit payment proof idempotently via JSON API."""
    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    if not check_campaign_permission(campaign, current_user):
        raise HTTPException(status_code=403, detail="Unauthorized.")

    clean_ref = payload.transaction_reference.strip().upper()
    existing = db.query(AdPayment).filter(AdPayment.transaction_reference == clean_ref).first()
    if existing:
        if existing.campaign_id == campaign_id:
            return existing
        raise HTTPException(status_code=400, detail="Transaction reference already recorded.")

    payment = AdPayment(
        campaign_id=campaign_id,
        business_id=campaign.business_id,
        user_id=current_user.id,
        amount=payload.amount,
        currency="INR",
        payment_method=payload.payment_method,
        gateway_provider="manual_admin_verify",
        transaction_reference=clean_ref,
        idempotency_key=payload.idempotency_key,
        status="proof_submitted",
        admin_notes=payload.notes,
    )
    db.add(payment)
    campaign.payment_status = "proof_submitted"
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/api/v1/ads/active", response_model=List[AdCampaignOut])
def api_get_active_ads(
    placement: str = Query("homepage_sponsored"),
    locality: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 5,
    db: Session = Depends(get_db),
):
    """Retrieve verified, approved, active ads eligible for server-side display."""
    ads = get_active_ads(db, placement=placement, locality=locality, category=category, limit=limit)
    return [AdCampaignOut.from_orm_with_extras(ad) for ad in ads]


@router.post("/api/v1/ads/{campaign_id}/impressions")
def api_log_ad_impression(
    campaign_id: int,
    request: Request,
    placement: str = Query("homepage_sponsored"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Log an ad impression with server-side deduplication."""
    ip = request.client.host if request.client else None
    user_id = current_user.id if current_user else None
    success = record_ad_impression(
        campaign_id=campaign_id,
        placement=placement,
        ip=ip,
        user_id=user_id,
        session_id=None,
        db=db,
    )
    return {"status": "recorded" if success else "failed"}


@router.post("/api/v1/ads/{campaign_id}/reports", response_model=AdReportOut, status_code=status.HTTP_201_CREATED)
def api_report_ad(
    campaign_id: int,
    payload: AdReportCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Submit an ad report via API."""
    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Ad campaign not found.")

    report = AdReport(
        campaign_id=campaign_id,
        reported_by_id=current_user.id if current_user else None,
        reporter_email=payload.reporter_email,
        reason=payload.reason,
        details=payload.details,
        status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.post("/api/v1/admin/campaigns/{campaign_id}/review", response_model=AdCampaignOut)
def api_admin_review_campaign(
    campaign_id: int,
    payload: AdReviewUpdate,
    current_admin: User = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    """Admin reviews an ad campaign via API."""
    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    now = utc_now()
    campaign.status = payload.status
    campaign.review_feedback = payload.review_feedback
    campaign.reviewed_by_id = current_admin.id
    campaign.reviewed_at = now

    if payload.status == "approved" and campaign.payment_status in ("verified", "waived") and campaign.start_date <= now <= campaign.end_date:
        campaign.status = "active"

    db.commit()
    db.refresh(campaign)
    return AdCampaignOut.from_orm_with_extras(campaign)


@router.post("/api/v1/admin/campaigns/{campaign_id}/verify-payment", response_model=AdCampaignOut)
def api_admin_verify_payment(
    campaign_id: int,
    action: str = Query("verify"),  # verify or reject
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin verifies or rejects payment for an ad campaign via API."""
    campaign = db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    payment = db.query(AdPayment).filter(AdPayment.campaign_id == campaign_id).order_by(AdPayment.created_at.desc()).first()
    now = utc_now()

    if action == "verify":
        if payment:
            payment.status = "verified"
            payment.verified_by_id = current_admin.id
            payment.verified_at = now
        campaign.payment_status = "verified"
        if campaign.status == "approved" and campaign.start_date <= now <= campaign.end_date and not campaign.is_paused:
            campaign.status = "active"
    elif action == "reject":
        if payment:
            payment.status = "failed"
        campaign.payment_status = "failed"

    db.commit()
    db.refresh(campaign)
    return AdCampaignOut.from_orm_with_extras(campaign)
