import pytest
from app.core.security import create_access_token, generate_csrf_token, get_password_hash
from app.core.social_validator import (
    validate_social_url,
    validate_portfolio_url,
    clean_social_url,
    clean_portfolio_url,
)
from app.models.user import User, UserFollow
from app.models.business import Business
from app.models.creator import CreatorProfile, BusinessCollaboration, VERIFICATION_BADGES
from app.models.notification import Notification


# ==============================================================================
# Helper fixture for Phase 6 test entities
# ==============================================================================

@pytest.fixture
def phase6_entities(db_session):
    """Ensure authentic test creator and test business exist in database."""
    # Creator User (user id 10)
    creator_user = db_session.query(User).filter(User.username == "test_weaver").first()
    if not creator_user:
        creator_user = User(
            id=10,
            username="test_weaver",
            email="weaver@test.local",
            hashed_password=get_password_hash("Weaver123!"),
            full_name="Master Weaver Zaidpur",
            role="creator",
            locality="Zaidpur",
            is_active=True,
        )
        db_session.add(creator_user)
        db_session.commit()
        db_session.refresh(creator_user)

    # Creator Profile
    creator_profile = db_session.query(CreatorProfile).filter(CreatorProfile.user_id == creator_user.id).first()
    if not creator_profile:
        creator_profile = CreatorProfile(
            user_id=creator_user.id,
            title="Master Jacquard Weaver",
            craft_category="Handloom & Textiles",
            bio="Preserving authentic Zaidpur handloom traditions for over three decades.",
            skills="Jacquard, Linen Weaving, Natural Dyes",
            locality="Zaidpur",
            languages="Hindi, Awadhi",
            content_categories="Handloom Weaving, Loom Shed Stories",
            instagram="https://www.instagram.com/zaidpur_weaves",
            youtube="https://www.youtube.com/@zaidpur_handlooms",
            portfolio_url="https://zaidpurweaves.example.in",
            is_verified=True,
            verification_badge="Master Artisan",
            verification_notes="Master artisan recognized by District Handloom Board.",
            is_featured=True,
            profile_views=10,
        )
        db_session.add(creator_profile)
        db_session.commit()
        db_session.refresh(creator_profile)

    # Business (owned by admin user id 1)
    business = db_session.query(Business).filter(Business.slug == "zaidpur-artisan-cooperative").first()
    if not business:
        business = Business(
            name="Zaidpur Artisan Cooperative",
            slug="zaidpur-artisan-cooperative",
            category="Handloom & Textiles",
            description="Cooperative promoting local weavers and traditional textiles.",
            address="Loom Market, Zaidpur",
            locality="Zaidpur",
            phone="+91-9839001122",
            created_by_id=1,  # Admin owns this business
            is_approved=True,
            is_verified=True,
        )
        db_session.add(business)
        db_session.commit()
        db_session.refresh(business)

    return {
        "creator_user": creator_user,
        "creator_profile": creator_profile,
        "business": business,
    }


# ==============================================================================
# 1. SOCIAL URL VALIDATOR TESTS (Strict Domain Allowlist & Anti-Phishing)
# ==============================================================================

def test_social_validator_accepts_valid_urls_and_handles():
    """Verify that canonical platform URLs, naked handles (@...), and clean paths are validated."""
    # Instagram
    val, err = clean_social_url("instagram", "@zaidpur_weaves")
    assert err is None
    assert val == "https://www.instagram.com/zaidpur_weaves"

    val, err = clean_social_url("instagram", "https://instagram.com/zaidpur_weaves/")
    assert err is None
    assert val == "https://www.instagram.com/zaidpur_weaves"

    # YouTube
    val, err = clean_social_url("youtube", "https://youtube.com/@barabankivlogs")
    assert err is None
    assert val == "https://www.youtube.com/@barabankivlogs"

    val, err = clean_social_url("youtube", "@barabankivlogs")
    assert err is None
    assert val == "https://www.youtube.com/@barabankivlogs"

    # X / Twitter
    val, err = clean_social_url("twitter_x", "https://x.com/barabankivoice")
    assert err is None
    assert val == "https://x.com/barabankivoice"

    val, err = clean_social_url("twitter_x", "@barabankivoice")
    assert err is None
    assert val == "https://x.com/barabankivoice"

    # LinkedIn
    val, err = clean_social_url("linkedin", "https://www.linkedin.com/in/bbkcreator")
    assert err is None
    assert val == "https://www.linkedin.com/in/bbkcreator"

    # GitHub
    val, err = clean_social_url("github", "amanverma-bbk")
    assert err is None
    assert val == "https://github.com/amanverma-bbk"

    # Portfolio
    val, err = clean_portfolio_url("https://zaidpurweaves.example.in/gallery")
    assert err is None
    assert val == "https://zaidpurweaves.example.in/gallery"


def test_social_validator_rejects_untrusted_and_malicious_urls():
    """Ensure phishing, cross-domain spoofing, javascript:, and data: schemes are rejected."""
    # Malicious JS URI
    val, err = clean_social_url("instagram", "javascript:alert('XSS')")
    assert val is None
    assert "Invalid URL scheme" in err

    # Data URI
    val, err = clean_social_url("youtube", "data:text/html,<script>alert(1)</script>")
    assert val is None
    assert "Invalid URL scheme" in err

    # Phishing domain attempting to disguise as instagram
    val, err = clean_social_url("instagram", "https://phishing-instagram.com/victim")
    assert val is None
    assert "Must be a legitimate" in err

    # Cross-platform mismatch (e.g. facebook link in instagram field)
    val, err = clean_social_url("instagram", "https://facebook.com/username")
    assert val is None
    assert "Must be a legitimate" in err

    # Dangerous portfolio link
    val, err = clean_portfolio_url("javascript:document.cookie")
    assert val is None
    assert "Invalid URL" in err


# ==============================================================================
# 2. CREATOR DISCOVERY & DIRECTORY TESTS
# ==============================================================================

def test_creator_directory_web_and_search_filters(client, phase6_entities):
    """Test creator directory list view with keywords, category, and verified filters."""
    # 1. Main Directory Page
    resp = client.get("/creators")
    assert resp.status_code == 200
    assert "Creator Hub & Social Directory" in resp.text
    assert "Master Weaver Zaidpur" in resp.text

    # 2. Category Filter (Handloom & Textiles)
    resp_cat = client.get("/creators?category=Handloom+%26+Textiles")
    assert resp_cat.status_code == 200
    assert "Master Weaver Zaidpur" in resp_cat.text

    # 3. Locality Filter (Zaidpur)
    resp_loc = client.get("/creators?locality=Zaidpur")
    assert resp_loc.status_code == 200
    assert "Master Weaver Zaidpur" in resp_loc.text

    # 4. Verified Only Filter
    resp_ver = client.get("/creators?verified_only=true")
    assert resp_ver.status_code == 200
    assert "Master Artisan" in resp_ver.text

    # 5. Keyword search match
    resp_q = client.get("/creators?q=Jacquard")
    assert resp_q.status_code == 200
    assert "Master Weaver Zaidpur" in resp_q.text

    # 6. Useful Empty State
    resp_empty = client.get("/creators?q=NonExistentArtisanXYZ999")
    assert resp_empty.status_code == 200
    assert "No Creators Found" in resp_empty.text
    assert "Clear All Filters" in resp_empty.text


def test_creator_detail_view_and_metrics_increment(client, phase6_entities, db_session):
    """Detail page must increment profile views, render verified badge info, and safe link rel tags."""
    creator = phase6_entities["creator_profile"]
    initial_views = creator.profile_views

    resp = client.get(f"/creators/{creator.id}")
    assert resp.status_code == 200
    assert "Master Weaver Zaidpur" in resp.text
    assert "Master Jacquard Weaver" in resp.text
    assert "Master Artisan" in resp.text

    # Security check: External social link attributes MUST contain rel="noopener noreferrer" target="_blank"
    assert 'target="_blank"' in resp.text
    assert 'rel="noopener noreferrer"' in resp.text

    # Check that profile views incremented in DB
    db_session.refresh(creator)
    assert creator.profile_views == initial_views + 1


# ==============================================================================
# 3. CREATOR PROFILE MANAGEMENT & ROLE PROMOTION
# ==============================================================================

def test_creator_profile_update_and_validation(client, resident_token, db_session):
    """Authenticated user edits profile, validates social allowlist, and updates user role to creator."""
    csrf = generate_csrf_token("testclient")

    # 1. Submit with invalid / phishing social link -> 400 with friendly error
    bad_payload = {
        "title": "Local Digital Artist",
        "craft_category": "Digital Art & Code",
        "bio": "Creating vector art and community illustrations of Barabanki.",
        "skills": "Figma, Illustrator, React",
        "locality": "Nawabganj",
        "languages": "Hindi, English",
        "instagram": "https://malicious-phishing-site.xyz/steal",
        "csrf_token": csrf,
    }
    resp_bad = client.post(
        "/creators/edit",
        data=bad_payload,
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_bad.status_code == 400
    assert "Must be a legitimate" in resp_bad.text

    # 2. Submit with valid allowlisted social links -> 303 Redirect to creator profile
    good_payload = {
        "title": "Local Digital Artist",
        "craft_category": "Digital Art & Code",
        "bio": "Creating vector art and community illustrations of Barabanki for civic empowerment.",
        "skills": "Figma, Illustrator, React",
        "locality": "Nawabganj",
        "languages": "Hindi, English",
        "instagram": "@barabanki_art",
        "youtube": "https://youtube.com/@barabanki_art",
        "github": "barabanki-artist",
        "portfolio_url": "https://barabankiart.example.com",
        "csrf_token": csrf,
    }
    resp_good = client.post(
        "/creators/edit",
        data=good_payload,
        headers={"Authorization": f"Bearer {resident_token}"},
        follow_redirects=False,
    )
    assert resp_good.status_code == 303
    assert "/creators/" in resp_good.headers["location"]

    # Verify user role upgraded from resident to creator
    user2 = db_session.query(User).filter(User.id == 2).first()
    assert user2.role == "creator"

    # Verify profile created in DB
    prof = db_session.query(CreatorProfile).filter(CreatorProfile.user_id == 2).first()
    assert prof is not None
    assert prof.title == "Local Digital Artist"
    assert prof.instagram == "https://www.instagram.com/barabanki_art"
    assert prof.github == "https://github.com/barabanki-artist"


def test_api_creator_profile_endpoints(client, resident_token):
    """Test REST API endpoints for creator profile creation and retrieval."""
    payload = {
        "title": "Mobile App Developer",
        "craft_category": "Digital Art & Code",
        "bio": "Building Flutter and Android apps for local vendors and agriculture in Barabanki.",
        "skills": "Flutter, Dart, Python",
        "locality": "Haidergarh",
        "languages": "Hindi, English",
        "github": "bbk-flutter-dev",
    }

    # REST PUT /api/v1/creators/profile
    resp = client.put(
        "/api/v1/creators/profile",
        json=payload,
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Mobile App Developer"
    assert data["craft_category"] == "Digital Art & Code"
    assert data["github"] == "https://github.com/bbk-flutter-dev"
    assert "followers_count" in data


# ==============================================================================
# 4. FOLLOW / UNFOLLOW CREATORS
# ==============================================================================

def test_creator_follow_unfollow_workflow_and_self_follow_prevention(client, phase6_entities, db_session):
    """Prevent self-follow; toggle follow creates follow record, dispatches notification, and unfollows cleanly."""
    creator = phase6_entities["creator_profile"]
    creator_token = create_access_token(data={"sub": str(creator.user_id), "role": "creator"})
    resident_token = create_access_token(data={"sub": "2", "role": "resident"})

    # 1. Prevent self-follow
    resp_self = client.post(
        f"/creators/{creator.id}/follow",
        headers={"Authorization": f"Bearer {creator_token}", "Accept": "application/json"},
    )
    assert resp_self.status_code == 400
    assert "cannot follow yourself" in resp_self.json()["detail"].lower()

    # 2. Resident follows Creator -> following = True, followers_count >= 1
    resp_follow = client.post(
        f"/creators/{creator.id}/follow",
        headers={"Authorization": f"Bearer {resident_token}", "Accept": "application/json"},
    )
    assert resp_follow.status_code == 200
    data_follow = resp_follow.json()
    assert data_follow["following"] is True
    assert data_follow["followers_count"] >= 1

    # Verify notification dispatched to creator user
    notif = (
        db_session.query(Notification)
        .filter(Notification.recipient_id == creator.user_id, Notification.notification_type == "follow")
        .order_by(Notification.created_at.desc())
        .first()
    )
    assert notif is not None
    assert "following your creator profile" in notif.message

    # 3. Resident calls follow again -> Unfollow toggle -> following = False
    resp_unfollow = client.post(
        f"/creators/{creator.id}/follow",
        headers={"Authorization": f"Bearer {resident_token}", "Accept": "application/json"},
    )
    assert resp_unfollow.status_code == 200
    data_unfollow = resp_unfollow.json()
    assert data_unfollow["following"] is False


# ==============================================================================
# 5. BUSINESS COLLABORATIONS WORKFLOW & ANTI-SPAM
# ==============================================================================

def test_business_collaboration_creation_and_duplicate_prevention(client, admin_token, resident_token, phase6_entities, db_session):
    """Business owner sends collaboration proposal; duplicates are rejected; anti-spam enforces limits."""
    creator = phase6_entities["creator_profile"]
    business = phase6_entities["business"]

    # 1. Resident does not own business -> 403 Forbidden
    payload = {
        "business_id": business.id,
        "campaign_title": "Winter Handloom Collection Showcase",
        "campaign_description": "A festive marketing campaign showcasing authentic handloom stoles for the winter wedding season.",
        "proposed_deliverables": "2 Instagram reels, 3 high-resolution story photo posts with shop links",
        "start_date": "10 Nov 2026",
        "end_date": "25 Nov 2026",
        "budget_range": "₹10,000 - ₹15,000",
        "contact_preference": "email",
        "contact_details": "business@test.local",
    }
    resp_unauth = client.post(
        f"/api/v1/creators/{creator.id}/collaborations",
        json=payload,
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_unauth.status_code == 403
    assert "do not own" in resp_unauth.json()["detail"].lower()

    # 2. Business owner (admin token, user id 1) sends collaboration proposal -> 201 Created
    resp_create = client.post(
        f"/api/v1/creators/{creator.id}/collaborations",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_create.status_code == 201
    collab_data = resp_create.json()
    assert collab_data["campaign_title"] == payload["campaign_title"]
    assert collab_data["status"] == "pending"
    assert collab_data["creator_id"] == creator.id
    collab_id = collab_data["id"]

    # Verify notification created for creator
    notif = (
        db_session.query(Notification)
        .filter(Notification.recipient_id == creator.user_id, Notification.notification_type == "collaboration")
        .order_by(Notification.created_at.desc())
        .first()
    )
    assert notif is not None
    assert "Winter Handloom Collection Showcase" in notif.message

    # 3. Anti-Spam: Submitting another pending proposal for same business and creator -> 400 Bad Request
    resp_dup = client.post(
        f"/api/v1/creators/{creator.id}/collaborations",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_dup.status_code == 400
    assert "already active" in resp_dup.json()["detail"].lower()


def test_collaboration_status_lifecycle_and_authorization(client, admin_token, phase6_entities, db_session):
    """Target creator accepts or declines proposal; sender can cancel; unauthorized cannot modify."""
    creator = phase6_entities["creator_profile"]
    business = phase6_entities["business"]
    creator_token = create_access_token(data={"sub": str(creator.user_id), "role": "creator"})
    resident_token = create_access_token(data={"sub": "2", "role": "resident"})

    # Create fresh collaboration
    collab = BusinessCollaboration(
        business_id=business.id,
        creator_id=creator.id,
        sender_user_id=1,
        campaign_title="Zaidpur Heritage Documentary Reel",
        campaign_description="A documentary capturing centuries of handloom weaving heritage in Zaidpur.",
        proposed_deliverables="1 mini-documentary 90s reel with custom Awadhi audio track",
        contact_preference="email",
        contact_details="admin@test.local",
        status="pending",
    )
    db_session.add(collab)
    db_session.commit()
    db_session.refresh(collab)

    # 1. Unauthorized resident tries to accept -> 403 Forbidden
    resp_unauth = client.patch(
        f"/api/v1/collaborations/{collab.id}/status",
        json={"status": "accepted", "creator_response_notes": "Hacked response"},
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_unauth.status_code == 403

    # 2. Target Creator accepts proposal -> 200 OK, status = "accepted"
    resp_accept = client.patch(
        f"/api/v1/collaborations/{collab.id}/status",
        json={"status": "accepted", "creator_response_notes": "Accepted! Ready to begin production next week."},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp_accept.status_code == 200
    data_acc = resp_accept.json()
    assert data_acc["status"] == "accepted"
    assert "Accepted!" in data_acc["creator_response_notes"]

    # Verify notification sent back to sender user (id 1)
    notif = (
        db_session.query(Notification)
        .filter(Notification.recipient_id == 1, Notification.notification_type == "collaboration")
        .order_by(Notification.created_at.desc())
        .first()
    )
    assert notif is not None
    assert "accepted" in notif.message.lower()

    # 3. Create another pending proposal to test cancellation by sender
    collab2 = BusinessCollaboration(
        business_id=business.id,
        creator_id=creator.id,
        sender_user_id=1,
        campaign_title="Temporary Test Collaboration",
        campaign_description="Short trial campaign to be cancelled by business sender.",
        proposed_deliverables="1 story mention",
        contact_preference="email",
        contact_details="admin@test.local",
        status="pending",
    )
    db_session.add(collab2)
    db_session.commit()
    db_session.refresh(collab2)

    resp_cancel = client.patch(
        f"/api/v1/collaborations/{collab2.id}/status",
        json={"status": "cancelled", "creator_response_notes": "Business timeline postponed"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "cancelled"


# ==============================================================================
# 6. ADMIN CREATOR VERIFICATION BADGES & SPOTLIGHT
# ==============================================================================

def test_admin_creator_verification_and_badging(client, admin_token, resident_token, phase6_entities, db_session):
    """Admins assign defined verification badges; non-admins are blocked; invalid badges rejected."""
    creator = phase6_entities["creator_profile"]

    # 1. Non-admin receives 403 Forbidden
    resp_unauth = client.post(
        f"/api/v1/admin/creators/{creator.id}/verify",
        json={"is_verified": True, "verification_badge": "Community Voice"},
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_unauth.status_code == 403

    # 2. Admin cannot assign invalid badge -> 400 Bad Request
    resp_invalid = client.post(
        f"/api/v1/admin/creators/{creator.id}/verify",
        json={"is_verified": True, "verification_badge": "Super Celebrity VIP"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_invalid.status_code == 400
    assert "Invalid badge" in resp_invalid.json()["detail"]

    # 3. Admin successfully awards official badge "Community Voice" with notes -> 200 OK
    resp_valid = client.post(
        f"/api/v1/admin/creators/{creator.id}/verify",
        json={
            "is_verified": True,
            "verification_badge": "Community Voice",
            "verification_notes": "Civic contributor recognized for preserving Barabanki cultural documentation.",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_valid.status_code == 200
    data = resp_valid.json()
    assert data["is_verified"] is True
    assert data["verification_badge"] == "Community Voice"
    assert "preserving Barabanki" in data["verification_notes"]

    # 4. Admin toggles featured status
    resp_feat = client.post(
        f"/api/v1/admin/creators/{creator.id}/feature",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_feat.status_code == 200
    assert "is_featured" in resp_feat.json()
