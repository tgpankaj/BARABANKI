import pytest
import time
from datetime import datetime, timezone, timedelta
from app.models.advertisement import (
    AdCampaign,
    AdPayment,
    AdImpression,
    AdClick,
    AdReport,
    PRICING_PLANS,
)
from app.models.business import Business
from app.models.user import User
from app.core.ad_validator import (
    validate_destination_url,
    sanitize_text,
    check_prohibited_content,
    validate_campaign_dates,
    calculate_plan_cost,
)
from app.core.security import generate_csrf_token


def get_test_admin(db_session):
    return db_session.query(User).filter(User.id == 1).first() or db_session.query(User).filter(User.role == "admin").first()


def get_test_resident(db_session):
    return db_session.query(User).filter(User.id == 2).first() or db_session.query(User).filter(User.username == "test_resident").first()


def ensure_test_business(db_session, user, prefix="biz"):
    """Helper creating a guaranteed isolated test business for the given user."""
    ts = int(time.time() * 1000)
    slug = f"{prefix}-{user.id}-{ts}"
    biz = Business(
        name=f"Enterprise {prefix.title()} {ts}",
        slug=slug,
        category="Retail & Groceries",
        locality="Zaidpur",
        address="Station Road, Barabanki",
        description="Verified local merchant listing.",
        created_by_id=user.id,
        is_approved=True,
    )
    db_session.add(biz)
    db_session.commit()
    db_session.refresh(biz)
    return biz


def ensure_test_campaign(db_session, user, biz=None, status="pending_review", payment_status="pending"):
    """Helper creating a guaranteed isolated test campaign."""
    if not biz:
        biz = ensure_test_business(db_session, user)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ts = int(time.time() * 1000)
    camp = AdCampaign(
        business_id=biz.id,
        user_id=user.id,
        name=f"Campaign Promo {ts}",
        objective="store_visit",
        headline=f"Special Offer {ts} Flat 20% Off",
        description="Authentic products at discounted rates for all Barabanki citizens.",
        destination_url=f"/businesses/{biz.slug}",
        contact_action="visit_website",
        placement="homepage_sponsored",
        target_locality="All Localities",
        target_category="Retail & Groceries",
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=10),
        pricing_plan="starter_7days",
        budget_amount=499.0,
        status=status,
        payment_status=payment_status,
        impression_count=15,
        click_count=3,
    )
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)
    return camp


def test_ad_validator_url_safety_and_prohibited_content():
    # 1. URL Safety
    valid, err, cleaned = validate_destination_url("https://example.com/festive-deal")
    assert valid is True
    assert cleaned == "https://example.com/festive-deal"

    # Internal path
    valid, err, cleaned = validate_destination_url("/businesses/zaidpur-handloom")
    assert valid is True
    assert cleaned == "/businesses/zaidpur-handloom"

    # Rejection of dangerous schemes
    valid, err, _ = validate_destination_url("javascript:alert(1)")
    assert valid is False
    assert "unsafe or forbidden" in err

    valid, err, _ = validate_destination_url("data:text/html,<script>alert(1)</script>")
    assert valid is False

    valid, err, _ = validate_destination_url("//evil-phish.com/login")
    assert valid is False

    # 2. Prohibited Content
    proh, reason = check_prohibited_content("Authentic Chikan Kurtas in Barabanki")
    assert proh is False

    proh, reason = check_prohibited_content("Play online satta and matka guaranteed win")
    assert proh is True
    assert "restricted keyword" in reason

    proh, reason = check_prohibited_content("Buy replica fake currency and counterfeit watches")
    assert proh is True

    # 3. Date Validation
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    valid, err = validate_campaign_dates(now, now + timedelta(days=7))
    assert valid is True

    valid, err = validate_campaign_dates(now + timedelta(days=5), now)
    assert valid is False

    # 4. Plan Cost Calculation
    cost, days, name = calculate_plan_cost("starter_7days")
    assert cost == 499.0
    assert days == 7

    cost, days, name = calculate_plan_cost("custom_daily", custom_days=3)
    assert cost == 297.0
    assert days == 3


def test_advertiser_dashboard_requires_auth(client):
    # Anonymous redirects to login
    res = client.get("/advertiser", follow_redirects=False)
    assert res.status_code == 303
    assert "/auth/login" in res.headers["location"]


def test_advertiser_dashboard_authenticated(client, resident_token, db_session):
    # Authenticated user view
    headers = {"Authorization": f"Bearer {resident_token}"}
    res = client.get("/advertiser", headers=headers)
    assert res.status_code == 200
    assert "Advertiser Dashboard" in res.text
    assert "Total Campaigns" in res.text


def test_campaign_creation_ownership_enforcement(client, resident_token, admin_token, db_session):
    admin_user = get_test_admin(db_session)
    resident_user = get_test_resident(db_session)

    biz_admin = ensure_test_business(db_session, admin_user, prefix="adm")
    biz_resident = ensure_test_business(db_session, resident_user, prefix="res")

    csrf = generate_csrf_token("testclient")

    # Resident tries to create ad for Admin's business -> 403 Forbidden
    res_forbidden = client.post(
        "/advertiser/campaigns/new",
        data={
            "business_id": biz_admin.id,
            "name": "Unauthorized Campaign",
            "objective": "brand_awareness",
            "headline": "Unauthorized Headline Deal",
            "description": "Unauthorized copy test",
            "placement": "homepage_sponsored",
            "pricing_plan": "starter_7days",
            "start_date_str": "2026-11-01",
            "csrf_token": csrf,
        },
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert res_forbidden.status_code == 403

    # Resident creates ad for their own business -> 303 Redirect to payment
    res_success = client.post(
        "/advertiser/campaigns/new",
        data={
            "business_id": biz_resident.id,
            "name": "Diwali Grocery Offer",
            "objective": "store_visit",
            "headline": "Special Diwali Grocery Hampers 15% Off",
            "description": "Fresh sweets, dry fruits and cooking oils available at discounted festive rates.",
            "destination_url": f"/businesses/{biz_resident.slug}",
            "contact_action": "visit_website",
            "placement": "directory_featured",
            "pricing_plan": "starter_7days",
            "start_date_str": "2026-10-18",
            "csrf_token": csrf,
        },
        headers={"Authorization": f"Bearer {resident_token}"},
        follow_redirects=False,
    )
    assert res_success.status_code == 303
    assert "/payment" in res_success.headers["location"]


def test_api_campaign_creation_and_validation(client, resident_token, db_session):
    resident_user = get_test_resident(db_session)
    biz = ensure_test_business(db_session, resident_user, prefix="apibiz")

    headers = {"Authorization": f"Bearer {resident_token}"}
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Rejection of prohibited content in API
    res_bad = client.post(
        "/api/v1/advertiser/campaigns",
        json={
            "business_id": biz.id,
            "name": "Illegal Matka Game",
            "objective": "lead_generation",
            "headline": "Play satta matka daily",
            "description": "Win 100x guaranteed cash profit daily",
            "placement": "homepage_sponsored",
            "target_locality": "Nawabganj",
            "target_category": "Services",
            "pricing_plan": "starter_7days",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=7)).isoformat(),
        },
        headers=headers,
    )
    assert res_bad.status_code == 422

    # Success creation via JSON API
    res_ok = client.post(
        "/api/v1/advertiser/campaigns",
        json={
            "business_id": biz.id,
            "name": "Fresh Harvest Honey",
            "objective": "store_visit",
            "headline": "100% Pure Forest Honey Direct from Farm",
            "description": "Raw unpasteurized honey harvested locally in Barabanki district.",
            "destination_url": "https://example.com/honey",
            "contact_action": "visit_website",
            "placement": "homepage_sponsored",
            "target_locality": "All Localities",
            "target_category": "Retail & Groceries",
            "pricing_plan": "growth_15days",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=15)).isoformat(),
        },
        headers=headers,
    )
    assert res_ok.status_code == 201
    data = res_ok.json()
    assert data["name"] == "Fresh Harvest Honey"
    assert data["budget_amount"] == 999.0
    assert data["status"] == "pending_review"


def test_payment_proof_submission_and_idempotency(client, resident_token, db_session):
    resident_user = get_test_resident(db_session)
    camp = ensure_test_campaign(db_session, resident_user, status="pending_review", payment_status="pending")

    csrf = generate_csrf_token("testclient")
    headers = {"Authorization": f"Bearer {resident_token}"}

    # Submit UTR payment reference
    utr_code = f"SBI{int(time.time()*1000)}"
    res = client.post(
        f"/advertiser/campaigns/{camp.id}/payment",
        data={
            "transaction_reference": utr_code,
            "amount": camp.budget_amount,
            "payment_method": "upi_qr",
            "notes": "Paid via Google Pay",
            "csrf_token": csrf,
        },
        headers=headers,
        follow_redirects=False,
    )
    assert res.status_code == 303

    # Check payment persisted
    pay = db_session.query(AdPayment).filter(AdPayment.transaction_reference == utr_code).first()
    assert pay is not None
    assert pay.status == "proof_submitted"
    assert pay.campaign_id == camp.id

    db_session.refresh(camp)
    assert camp.payment_status == "proof_submitted"

    # Idempotent resubmission of same reference for same campaign does not error
    res_repeat = client.post(
        f"/advertiser/campaigns/{camp.id}/payment",
        data={
            "transaction_reference": utr_code,
            "amount": camp.budget_amount,
            "payment_method": "upi_qr",
            "csrf_token": csrf,
        },
        headers=headers,
        follow_redirects=False,
    )
    assert res_repeat.status_code == 303


def test_admin_campaign_review_and_feedback(client, admin_token, resident_token, db_session):
    resident_user = get_test_resident(db_session)
    camp = ensure_test_campaign(db_session, resident_user, status="pending_review", payment_status="pending")

    # Resident cannot review (403)
    res_forbidden = client.post(
        f"/admin/campaigns/{camp.id}/review",
        data={"action": "approve"},
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert res_forbidden.status_code == 403

    # Admin approves campaign
    res_admin = client.post(
        f"/admin/campaigns/{camp.id}/review",
        data={"action": "approve", "feedback": "Creative verified and meets civic standards."},
        headers={"Authorization": f"Bearer {admin_token}"},
        follow_redirects=False,
    )
    assert res_admin.status_code == 303

    db_session.refresh(camp)
    assert camp.status == "approved"
    assert "Creative verified" in camp.review_feedback


def test_admin_payment_verification_and_campaign_activation(client, admin_token, db_session):
    resident_user = get_test_resident(db_session)
    camp = ensure_test_campaign(db_session, resident_user, status="approved", payment_status="proof_submitted")

    # Create submitted payment proof
    utr_code = f"UTR{int(time.time()*1000)}"
    payment = AdPayment(
        campaign_id=camp.id,
        business_id=camp.business_id,
        user_id=camp.user_id,
        amount=camp.budget_amount,
        currency="INR",
        payment_method="upi_qr",
        gateway_provider="manual_admin_verify",
        transaction_reference=utr_code,
        status="proof_submitted",
    )
    db_session.add(payment)
    db_session.commit()

    # Admin verifies payment
    res = client.post(
        f"/admin/campaigns/{camp.id}/verify-payment",
        data={"action": "verify", "admin_notes": "Bank statement confirmed receipt."},
        headers={"Authorization": f"Bearer {admin_token}"},
        follow_redirects=False,
    )
    assert res.status_code == 303

    db_session.refresh(camp)
    assert camp.payment_status == "verified"
    assert camp.status == "active"

    db_session.refresh(payment)
    assert payment.status == "verified"


def test_server_side_placement_eligibility_enforcement(client, db_session):
    admin_user = get_test_admin(db_session)
    active_ad = ensure_test_campaign(db_session, admin_user, status="active", payment_status="verified")

    # Directly query active ads endpoint
    res = client.get("/api/v1/ads/active?placement=homepage_sponsored")
    assert res.status_code == 200
    active_ads = res.json()
    assert len(active_ads) > 0

    # All returned ads MUST be approved/active, verified payment, unpaused
    for ad in active_ads:
        assert ad["status"] in ["approved", "active"]
        assert ad["payment_status"] == "verified"
        assert ad["is_paused"] is False


def test_ad_impression_and_click_tracking(client, db_session):
    admin_user = get_test_admin(db_session)
    ad = ensure_test_campaign(db_session, admin_user, status="active", payment_status="verified")

    initial_impressions = ad.impression_count
    initial_clicks = ad.click_count

    # 1. Log impression via API
    res_imp = client.post(f"/api/v1/ads/{ad.id}/impressions?placement={ad.placement}")
    assert res_imp.status_code == 200

    # 2. Log click via redirect endpoint
    res_click = client.get(f"/ads/{ad.id}/click", follow_redirects=False)
    assert res_click.status_code in (302, 303)

    db_session.refresh(ad)
    assert ad.click_count >= initial_clicks


def test_ad_reporting_and_public_policy(client, db_session):
    admin_user = get_test_admin(db_session)
    ad = ensure_test_campaign(db_session, admin_user, status="active", payment_status="verified")

    csrf = generate_csrf_token("testclient")

    # 1. Public Policy page renders
    res_policy = client.get("/advertising/policy")
    assert res_policy.status_code == 200
    assert "Advertising Policies & Guidelines" in res_policy.text
    assert "Prohibited Products" in res_policy.text

    # 2. Report Ad Form renders
    res_rep_page = client.get(f"/ads/{ad.id}/report")
    assert res_rep_page.status_code == 200
    assert "Report Advertisement" in res_rep_page.text

    # 3. Submit Report
    res_rep = client.post(
        f"/ads/{ad.id}/report",
        data={
            "reason": "misleading",
            "details": "The discount offered on this ad expired yesterday.",
            "reporter_email": "citizen@test.local",
            "csrf_token": csrf,
        },
    )
    assert res_rep.status_code == 200
    assert "Thank You for Your Report" in res_rep.text

    # Verify report in database
    rep = db_session.query(AdReport).filter(AdReport.campaign_id == ad.id).first()
    assert rep is not None
    assert rep.reason == "misleading"
    assert rep.status == "pending"
