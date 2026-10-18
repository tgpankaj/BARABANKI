from app.core.security import generate_csrf_token
from app.models.event import Event
from app.models.business import Business
from app.models.community import CommunityPost, Comment
from app.models.user import User


def test_event_form_submission_unauthenticated(client):
    """Anonymous event submission attempts must redirect to login."""
    resp = client.post(
        "/events/create",
        data={
            "title": "Unauthorized District Mela",
            "category": "Cultural",
            "description": "Attempt to post an event without resident authentication.",
            "start_date": "2026-11-01T10:00",
            "venue_name": "Town Hall",
            "address": "Civil Lines, Barabanki",
            "csrf_token": generate_csrf_token("testclient"),
        },
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303, 307)
    assert "/auth/login" in resp.headers["location"]


def test_event_form_submission_authenticated(client, resident_token, db_session):
    """Authenticated user can submit an event and have it persisted to the database."""
    csrf = generate_csrf_token("testclient")
    title = "Annual Barabanki Mango & Agriculture Festival 2026"

    resp = client.post(
        "/events/create",
        data={
            "title": title,
            "category": "Cultural",
            "description": "Celebrating the finest Dasheri mango harvests and organic farming across Ramnagar tehsils.",
            "start_date": "2026-07-15T09:00",
            "venue_name": "Kishan Mandi Ground",
            "address": "Ramnagar Road, Barabanki",
            "locality": "Ramnagar",
            "organizer_name": "District Farmers Collective",
            "organizer_contact": "+91-9876543210",
            "csrf_token": csrf,
        },
        headers={"Cookie": f"barabanki_session={resident_token}"},
        follow_redirects=False,
    )

    assert resp.status_code in (302, 303, 307)
    location = resp.headers["location"]
    assert "/events/" in location

    # Verify database persistence
    event = db_session.query(Event).filter(Event.title == title).first()
    assert event is not None
    assert event.locality == "Ramnagar"
    assert event.is_approved is True
    assert event.slug in location


def test_event_detail_page_loads_persisted_event(client, resident_token):
    """Event detail page loads verified data for the created event."""
    csrf = generate_csrf_token("testclient")
    title = "Zaidpur Weaver Heritage Exhibition"
    slug_expected = "zaidpur-weaver-heritage-exhibition"

    client.post(
        "/events/create",
        data={
            "title": title,
            "category": "Cultural",
            "description": "Live loom demonstration and master weaver awards from Zaidpur cluster.",
            "start_date": "2026-08-20T10:00",
            "venue_name": "Zaidpur Community Center",
            "address": "Main Bazaar, Zaidpur",
            "locality": "Zaidpur",
            "organizer_name": "Zaidpur Weavers Guild",
            "csrf_token": csrf,
        },
        headers={"Cookie": f"barabanki_session={resident_token}"},
        follow_redirects=False,
    )

    resp = client.get(f"/events/{slug_expected}")
    assert resp.status_code == 200
    assert title in resp.text
    assert "Zaidpur Community Center" in resp.text
    assert "Cultural" in resp.text


def test_business_creation_authenticated_persists(client, resident_token, db_session):
    """Authenticated user creates a business listing with slug collision protection."""
    csrf = generate_csrf_token("testclient")
    name = "Awadh Khadi Bhandar"

    # 1st creation
    resp1 = client.post(
        "/businesses/new",
        data={
            "name": name,
            "category": "Handloom & Textiles",
            "locality": "Nawabganj",
            "address": "Station Road, Nawabganj, Barabanki",
            "description": "Authentic hand-spun khadi kurtas and handcrafted organic cotton fabrics.",
            "phone": "05248-223344",
            "csrf_token": csrf,
        },
        headers={"Cookie": f"barabanki_session={resident_token}"},
        follow_redirects=False,
    )
    assert resp1.status_code in (302, 303, 307)
    assert "/businesses/awadh-khadi-bhandar" in resp1.headers["location"]

    # 2nd creation with duplicate name - should auto-append collision suffix
    resp2 = client.post(
        "/businesses/new",
        data={
            "name": name,
            "category": "Handloom & Textiles",
            "locality": "Deva Sharif",
            "address": "Dargah Road, Deva Sharif",
            "description": "Second branch outlet of Awadh Khadi Bhandar.",
            "phone": "05248-223345",
            "csrf_token": csrf,
        },
        headers={"Cookie": f"barabanki_session={resident_token}"},
        follow_redirects=False,
    )
    assert resp2.status_code in (302, 303, 307)
    assert "/businesses/awadh-khadi-bhandar-1" in resp2.headers["location"]

    biz1 = db_session.query(Business).filter(Business.slug == "awadh-khadi-bhandar").first()
    biz2 = db_session.query(Business).filter(Business.slug == "awadh-khadi-bhandar-1").first()
    assert biz1 is not None
    assert biz2 is not None
    assert biz2.locality == "Deva Sharif"


def test_business_creation_unauthenticated_redirects(client):
    """Unauthenticated business creation attempts redirect to login."""
    resp = client.post(
        "/businesses/new",
        data={
            "name": "Anonymous Store",
            "category": "Retail",
            "locality": "Nawabganj",
            "address": "Market Road",
            "description": "Unauthenticated submission attempt.",
            "csrf_token": generate_csrf_token("testclient"),
        },
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303, 307)
    assert "/auth/login" in resp.headers["location"]


def test_community_post_and_comment_workflows(client, resident_token, db_session):
    """Test community post creation, commenting and upvoting end-to-end."""
    csrf = generate_csrf_token("testclient")
    title = "Repair requested for streetlights near Ghanta Ghar"

    # Post creation
    post_resp = client.post(
        "/community/new",
        data={
            "title": title,
            "category": "Civic Issues",
            "content": "Several streetlights on the clock tower roundabout have been flickering and need bulb replacement.",
            "csrf_token": csrf,
        },
        headers={"Cookie": f"barabanki_session={resident_token}"},
        follow_redirects=False,
    )
    assert post_resp.status_code in (302, 303, 307)

    post = db_session.query(CommunityPost).filter(CommunityPost.title == title).first()
    assert post is not None

    # Comment submission using slug
    comment_resp = client.post(
        f"/community/{post.slug}/comment",
        data={
            "content": "Noted by local ward committee, ticket logged with Nagar Palika Parishad.",
            "csrf_token": csrf,
        },
        headers={"Cookie": f"barabanki_session={resident_token}"},
        follow_redirects=False,
    )
    assert comment_resp.status_code in (302, 303, 307)

    comment = db_session.query(Comment).filter(Comment.post_id == post.id).first()
    assert comment is not None
    assert "Nagar Palika" in comment.content

    # Upvoting using slug
    init_votes = post.upvotes
    upvote_resp = client.post(
        f"/community/{post.slug}/upvote",
        data={"csrf_token": csrf},
        headers={"Cookie": f"barabanki_session={resident_token}"},
        follow_redirects=False,
    )
    assert upvote_resp.status_code in (302, 303, 307)
    db_session.refresh(post)
    assert post.upvotes == init_votes + 1


def test_services_category_filtering(client):
    """Verify that Public Services Directory filters according to the selected category."""
    # Transport filter
    resp_transport = client.get("/services?category=Transport")
    assert resp_transport.status_code == 200
    assert "Transport Services" in resp_transport.text
    assert "UPSRTC Roadways Bus Depot" in resp_transport.text
    assert "Collectorate, DM & ADM Office" not in resp_transport.text

    # Emergency filter
    resp_emergency = client.get("/services?category=Emergency")
    assert resp_emergency.status_code == 200
    assert "Emergency Contacts" in resp_emergency.text
    assert "Hospitals Directory" in resp_emergency.text
    assert "UPSRTC Roadways Bus Depot" not in resp_emergency.text


def test_universal_search_across_entities(client, resident_token, db_session):
    """Verify universal search across news, businesses, events, and community threads."""
    csrf = generate_csrf_token("testclient")

    # Seed an item for search
    create_resp = client.post(
        "/events/create",
        data={
            "title": "Barabanki Robotics and Coding Olympiad",
            "category": "Educational",
            "description": "District youth competition in STEM, programming, and robotics held at Jahangirabad Institute.",
            "start_date": "2026-09-10T09:00",
            "venue_name": "JIT Auditorium",
            "address": "JIT Barabanki",
            "locality": "Barabanki",
            "organizer_name": "Youth STEM Council",
            "csrf_token": csrf,
        },
        headers={"Cookie": f"barabanki_session={resident_token}"},
        follow_redirects=False,
    )
    assert create_resp.status_code == 303
    assert "/events/barabanki-robotics" in create_resp.headers["location"]

    # Search for "Olympiad"
    search_resp = client.get("/search?q=Olympiad")
    assert search_resp.status_code == 200
    assert "Barabanki Robotics and Coding Olympiad" in search_resp.text
    assert "Event" in search_resp.text

    # Search filtered by type=events
    search_filtered = client.get("/search?q=Olympiad&type=events")
    assert search_filtered.status_code == 200
    assert "Barabanki Robotics and Coding Olympiad" in search_filtered.text


def test_prevent_self_assign_admin_on_web_registration(client, db_session):
    """Ensure malicious registration payloads cannot escalate privileges to admin."""
    csrf = generate_csrf_token("testclient")
    username = "attacker_resident"

    resp = client.post(
        "/auth/register",
        data={
            "username": username,
            "email": "attacker@evil.local",
            "full_name": "Unauthorized Admin Aspirant",
            "password": "SecurePassword123!",
            "role": "admin",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303, 307)

    user = db_session.query(User).filter(User.username == username).first()
    assert user is not None
    assert user.role == "resident"  # Forced back to resident


def test_prevent_self_assign_admin_on_api_registration(client, db_session):
    """Ensure REST API registration cannot self-grant admin role."""
    username = "api_privilege_escalation"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": "escalate@api.local",
            "full_name": "API Privilege Tester",
            "password": "Password789!",
            "role": "admin",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "resident"

    user = db_session.query(User).filter(User.username == username).first()
    assert user is not None
    assert user.role == "resident"


def test_admin_toggle_approve_event(client, admin_token, resident_token, db_session):
    """Admins can toggle the approval status of an event."""
    event = db_session.query(Event).first()
    if not event:
        # Create a test event if none in in-memory db
        csrf = generate_csrf_token("testclient")
        client.post(
            "/events/create",
            data={
                "title": "Townhall Coordination Meeting",
                "category": "Social",
                "description": "Monthly civic coordination meeting.",
                "start_date": "2026-10-30T10:00",
                "venue_name": "Town Hall",
                "address": "Nawabganj",
                "locality": "Nawabganj",
                "csrf_token": csrf,
            },
            headers={"Cookie": f"barabanki_session={admin_token}"},
            follow_redirects=False,
        )
        event = db_session.query(Event).first()

    assert event is not None
    original_approval = event.is_approved

    # Admin toggles
    csrf = generate_csrf_token("testclient")
    resp = client.post(
        f"/admin/events/{event.id}/toggle-approve",
        data={"csrf_token": csrf},
        headers={"Cookie": f"barabanki_session={admin_token}"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303, 307)
    db_session.refresh(event)
    assert event.is_approved == (not original_approval)

    # Non-admin cannot toggle
    resp_unauth = client.post(
        f"/admin/events/{event.id}/toggle-approve",
        data={"csrf_token": csrf},
        headers={"Cookie": f"barabanki_session={resident_token}"},
        follow_redirects=False,
    )
    assert resp_unauth.status_code in (401, 403, 302, 303)
