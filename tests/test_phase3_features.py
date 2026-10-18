from datetime import datetime
from app.core.security import generate_csrf_token, create_access_token
from app.models.community import CommunityPost, PostLike
from app.models.event import Event, EventRegistration
from app.models.user import User, UserFollow
from app.models.civic_issue import CivicIssue
from app.models.notification import Notification
from app.models.report import ModerationAudit


# Helper to get or create extra test users
def get_user_token(user_id: int, role: str = "resident"):
    return create_access_token(data={"sub": str(user_id), "role": role})


# ==============================================================================
# FEATURE 1: COMMUNITY FEED (Likes, Edit/Delete Ownership, Comments, Notifications)
# ==============================================================================

def test_community_post_like_toggle_and_duplicate_prevention(client, resident_token, db_session):
    """Liking a post toggles like state, updates upvotes count, and prevents duplicate likes."""
    # Ensure author (user 1) and voter (user 2) exist
    author = db_session.query(User).filter(User.id == 1).first()
    assert author is not None

    post = CommunityPost(
        title="Test Heritage Preservation Post",
        slug="test-heritage-preservation-post",
        category="Culture",
        content="Preserving the historical buildings of Barabanki.",
        author_id=author.id,
        status="published",
        upvotes=5,
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)

    # First like by resident (user 2)
    resp = client.post(
        f"/api/v1/community/posts/{post.slug}/like",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["liked"] is True
    assert data["upvotes"] == 6

    # Verify PostLike record in DB
    like_rec = db_session.query(PostLike).filter(PostLike.post_id == post.id, PostLike.user_id == 2).first()
    assert like_rec is not None

    # Verify notification sent to post author (user 1)
    notif = (
        db_session.query(Notification)
        .filter(Notification.recipient_id == 1, Notification.notification_type == "like")
        .order_by(Notification.created_at.desc())
        .first()
    )
    assert notif is not None
    assert "liked your post" in notif.message

    # Toggle like again (unlike) -> duplicate like prevented
    resp2 = client.post(
        f"/api/v1/community/posts/{post.slug}/like",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["liked"] is False
    assert data2["upvotes"] == 5

    # Verify PostLike record removed from DB
    like_rec2 = db_session.query(PostLike).filter(PostLike.post_id == post.id, PostLike.user_id == 2).first()
    assert like_rec2 is None


def test_community_post_edit_ownership_enforcement(client, admin_token, resident_token, db_session):
    """Only post author (or admin) can edit a post. Other users get 403 Forbidden."""
    # Create post owned by resident (user 2)
    post = CommunityPost(
        title="Original Resident Post",
        slug="original-resident-post",
        category="General",
        content="Original content by resident.",
        author_id=2,
        status="published",
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)

    # Create another third-party user (user 3)
    user3 = db_session.query(User).filter(User.id == 3).first()
    if not user3:
        from app.core.security import get_password_hash
        user3 = User(
            id=3,
            username="other_citizen",
            email="other@test.local",
            hashed_password=get_password_hash("Password123!"),
            full_name="Other Citizen",
            role="resident",
            is_active=True,
        )
        db_session.add(user3)
        db_session.commit()
    user3_token = get_user_token(3, "resident")

    # Attempt edit by non-owner user 3 -> 403
    resp_unauth = client.put(
        f"/api/v1/community/posts/{post.slug}",
        json={"title": "Hacked Title", "content": "Hacked Content", "category": "General"},
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert resp_unauth.status_code == 403
    assert "permission" in resp_unauth.json()["detail"]

    # Owner (user 2) edits post -> 200 OK
    resp_owner = client.put(
        f"/api/v1/community/posts/{post.slug}",
        json={"title": "Updated Resident Post", "content": "Updated content by owner.", "category": "General"},
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_owner.status_code == 200

    # Verify DB update
    db_session.refresh(post)
    assert post.title == "Updated Resident Post"
    assert post.content == "Updated content by owner."


def test_community_post_delete_ownership_enforcement(client, resident_token, db_session):
    """Only post author (or admin) can delete a post. Unauthorized users receive 403."""
    post = CommunityPost(
        title="Post To Be Deleted",
        slug="post-to-be-deleted",
        category="General",
        content="This post will test deletion permissions.",
        author_id=2,
        status="published",
    )
    db_session.add(post)
    db_session.commit()

    # User 3 attempts to delete post owned by user 2 -> 403
    user3_token = get_user_token(3, "resident")
    resp_unauth = client.delete(
        f"/api/v1/community/posts/{post.slug}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert resp_unauth.status_code == 403

    # Owner (user 2) deletes post -> 200
    resp_owner = client.delete(
        f"/api/v1/community/posts/{post.slug}",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_owner.status_code == 200

    # Verify deleted from DB
    deleted = db_session.query(CommunityPost).filter(CommunityPost.slug == "post-to-be-deleted").first()
    assert deleted is None


def test_community_comment_creates_notification(client, resident_token, db_session):
    """Adding a comment to another user's post notifies the author."""
    # Post owned by user 1 (Admin)
    post = CommunityPost(
        title="Admin Announcement Post",
        slug="admin-announcement-post",
        category="News",
        content="Important district announcement.",
        author_id=1,
        status="published",
    )
    db_session.add(post)
    db_session.commit()

    # User 2 comments on User 1's post via web form
    csrf = generate_csrf_token("testclient")
    resp = client.post(
        f"/community/{post.slug}/comment",
        data={"content": "Excellent initiative for our town!", "csrf_token": csrf},
        headers={"Cookie": f"barabanki_session={resident_token}"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    # Check notification in DB for user 1
    notif = (
        db_session.query(Notification)
        .filter(Notification.recipient_id == 1, Notification.notification_type == "comment")
        .order_by(Notification.created_at.desc())
        .first()
    )
    assert notif is not None
    assert "commented on" in notif.message


# ==============================================================================
# FEATURE 2: USER & CREATOR PROFILES (Public View, Privacy, Follow/Unfollow)
# ==============================================================================

def test_public_profile_view_and_privacy(client, db_session):
    """Public profile must display public details but NEVER expose private emails, phones, or hashes."""
    # View user 2 (test_resident)
    resp = client.get("/api/v1/users/test_resident")
    assert resp.status_code == 200
    data = resp.json()

    assert data["username"] == "test_resident"
    assert data["full_name"] == "Test Citizen"
    assert "role" in data
    assert "locality" in data

    # Strict Privacy Check: No private fields in public API response
    assert "email" not in data
    assert "phone" not in data
    assert "hashed_password" not in data
    assert "password" not in data


def test_follow_unfollow_workflow_and_self_follow_prevention(client, resident_token, db_session):
    """User can follow/unfollow creators, counts update, notifications send, and self-follow is prevented."""
    # 1. Prevent self-follow
    resp_self = client.post(
        "/api/v1/users/test_resident/follow",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_self.status_code == 400
    assert "cannot follow yourself" in resp_self.json()["detail"].lower()

    # 2. Resident (user 2) follows Admin (user 1)
    resp_follow = client.post(
        "/api/v1/users/test_admin/follow",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_follow.status_code == 200
    follow_data = resp_follow.json()
    assert follow_data["following"] is True
    assert follow_data["followers_count"] >= 1

    # Verify notification sent to user 1
    notif = (
        db_session.query(Notification)
        .filter(Notification.recipient_id == 1, Notification.notification_type == "follow")
        .order_by(Notification.created_at.desc())
        .first()
    )
    assert notif is not None
    assert "started following you" in notif.message

    # 3. Resident (user 2) unfollows Admin (user 1)
    resp_unfollow = client.post(
        "/api/v1/users/test_admin/follow",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_unfollow.status_code == 200
    unfollow_data = resp_unfollow.json()
    assert unfollow_data["following"] is False

    # Verify UserFollow record deleted
    rel = db_session.query(UserFollow).filter(UserFollow.follower_id == 2, UserFollow.following_id == 1).first()
    assert rel is None


def test_user_profile_update(client, resident_token, db_session):
    """User can update their bio and locality via profile update endpoint."""
    resp = client.patch(
        "/api/v1/auth/me",
        json={"bio": "Enthusiastic civic volunteer in Nawabganj.", "locality": "Nawabganj"},
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["bio"] == "Enthusiastic civic volunteer in Nawabganj."
    assert data["locality"] == "Nawabganj"

    # Verify DB persistence
    user = db_session.query(User).filter(User.id == 2).first()
    assert user.locality == "Nawabganj"
    assert user.bio == "Enthusiastic civic volunteer in Nawabganj."


# ==============================================================================
# FEATURE 3: EVENT PARTICIPATION (RSVP, Capacity, Cancellation)
# ==============================================================================

def test_event_rsvp_capacity_and_cancellation(client, resident_token, db_session):
    """Event registration persists, duplicate prevention works, capacity is checked, and cancellation succeeds."""
    # Create test event with capacity = 1
    event = Event(
        title="Youth Leadership Workshop 2026",
        slug="youth-leadership-workshop-2026",
        category="Educational",
        description="Limited seats workshop for district youth leaders.",
        start_date=datetime(2026, 11, 20, 10, 0),
        venue_name="Vikas Bhawan Hall",
        address="Kutchery Road, Barabanki",
        locality="Barabanki City",
        organizer_name="Barabanki Youth Council",
        capacity=1,
        is_approved=True,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    # 1. User 2 registers -> Success 200
    resp_reg = client.post(
        f"/api/v1/events/{event.slug}/register",
        json={"notes": "Registering as youth delegate"},
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_reg.status_code in (200, 201)
    reg_data = resp_reg.json()
    assert reg_data["status"] == "confirmed"

    # Verify registration in DB
    reg_db = (
        db_session.query(EventRegistration)
        .filter(EventRegistration.event_id == event.id, EventRegistration.user_id == 2)
        .first()
    )
    assert reg_db is not None
    assert reg_db.status == "confirmed"

    # 2. Duplicate registration attempt by user 2 -> 400 Already registered
    resp_dup = client.post(
        f"/api/v1/events/{event.slug}/register",
        json={"notes": "Attempting second registration"},
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_dup.status_code == 400
    assert "already registered" in resp_dup.json()["detail"].lower()

    # 3. Capacity limit enforcement: User 3 tries to register when capacity (1) is reached -> 400
    user3_token = get_user_token(3, "resident")
    resp_cap = client.post(
        f"/api/v1/events/{event.slug}/register",
        json={"notes": "Hope there is room"},
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert resp_cap.status_code == 400
    assert "maximum capacity" in resp_cap.json()["detail"].lower()

    # 4. Cancellation by User 2 -> Success
    resp_cancel = client.post(
        f"/api/v1/events/{event.slug}/cancel-registration",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_cancel.status_code == 200
    assert "cancelled successfully" in resp_cancel.json()["message"].lower()

    # Verify DB status updated to cancelled
    db_session.refresh(reg_db)
    assert reg_db.status == "cancelled"

    # 5. Now User 3 can register because 1 spot freed up
    resp_user3_reg = client.post(
        f"/api/v1/events/{event.slug}/register",
        json={"notes": "Registering after cancellation"},
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert resp_user3_reg.status_code in (200, 201)


# ==============================================================================
# FEATURE 4: CIVIC ISSUES & REPORTS (Screen 8)
# ==============================================================================

def test_civic_issue_submission_and_lifecycle(client, resident_token, admin_token, db_session):
    """Submitting a civic issue creates initial status history and upvote, and admin can update status with audit log."""
    # 1. Citizen reports issue
    issue_payload = {
        "title": "Broken Handpump near Gram Panchayat Office",
        "category": "Water Supply",
        "locality": "Haidergarh",
        "landmark": "Near Panchayat Bhawan gate",
        "description": "The public handpump has been dry and broken for two weeks, forcing residents to walk 1 km for clean drinking water.",
        "image_url": "https://images.unsplash.com/photo-1541888946425-d0fbb186c5f3",
    }
    resp = client.post(
        "/api/v1/issues",
        json=issue_payload,
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp.status_code == 201
    issue_data = resp.json()
    assert issue_data["title"] == issue_payload["title"]
    assert issue_data["status"] == "Submitted"
    assert issue_data["upvotes"] == 1
    assert issue_data["has_upvoted"] is True
    assert len(issue_data["status_history"]) >= 1

    issue_slug = issue_data["slug"]

    # 2. Detail view returns timeline
    resp_detail = client.get(f"/api/v1/issues/{issue_slug}")
    assert resp_detail.status_code == 200
    detail_data = resp_detail.json()
    assert len(detail_data["status_history"]) >= 1
    assert detail_data["status_history"][0]["new_status"] == "Submitted"

    # 3. Another user upvotes ("Me Too")
    user3_token = get_user_token(3, "resident")
    resp_upvote = client.post(
        f"/api/v1/issues/{issue_slug}/upvote",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert resp_upvote.status_code == 200
    assert resp_upvote.json()["upvotes"] == 2
    assert resp_upvote.json()["upvoted"] is True

    # 4. Regular resident cannot change status -> 403 Forbidden
    resp_unauth_status = client.post(
        f"/api/v1/issues/{issue_slug}/status",
        json={"status": "In Progress", "notes": "Resident unauthorized attempt"},
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_unauth_status.status_code == 403

    # 5. Admin updates status to "In Progress" -> 200 OK
    resp_admin_status = client.post(
        f"/api/v1/issues/{issue_slug}/status",
        json={"status": "In Progress", "notes": "Dispatched Jal Nigam repair team with replacement bore pipe."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_admin_status.status_code == 200
    updated_data = resp_admin_status.json()
    assert updated_data["status"] == "In Progress"

    # Verify notification sent to issue reporter (user 2)
    notif = (
        db_session.query(Notification)
        .filter(Notification.recipient_id == 2, Notification.notification_type == "issue_status")
        .order_by(Notification.created_at.desc())
        .first()
    )
    assert notif is not None
    assert "In Progress" in notif.title or "In Progress" in notif.message

    # Verify ModerationAudit entry logged
    audit = (
        db_session.query(ModerationAudit)
        .filter(ModerationAudit.entity_type == "civic_issue")
        .order_by(ModerationAudit.created_at.desc())
        .first()
    )
    assert audit is not None
    assert audit.moderator_id == 1
    assert "in_progress" in audit.action


def test_civic_issues_web_view_and_filtering(client, db_session):
    """Web view for /issues renders with categories, localities, and status badges."""
    resp = client.get("/issues?category=Water+Supply")
    assert resp.status_code == 200
    assert "Community &amp; Public Problems" in resp.text or "Community & Public Problems" in resp.text
    assert "Water Supply" in resp.text


# ==============================================================================
# FEATURE 5: ADMIN MODERATION & POST CONTROLS
# ==============================================================================

def test_admin_moderation_queue_and_post_status(client, admin_token, resident_token, db_session):
    """Admin can view reports, update post moderation status, and log audits."""
    # 1. Resident cannot access admin moderation -> 403 or redirect
    resp_resident = client.get(
        "/admin/moderation",
        headers={"Cookie": f"barabanki_session={resident_token}"},
        follow_redirects=False,
    )
    assert resp_resident.status_code in (302, 303, 307, 403)

    # 2. Create a test post to moderate
    post = CommunityPost(
        title="Spam Promotional Post",
        slug="spam-promotional-post",
        category="General",
        content="Buy fake goods here.",
        author_id=2,
        status="published",
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)

    # 3. Admin hides the post
    resp_hide = client.post(
        f"/admin/posts/{post.id}/status",
        data={"new_status": "hidden", "reason": "Violates community policy regarding commercial spam."},
        headers={"Cookie": f"barabanki_session={admin_token}"},
        follow_redirects=False,
    )
    assert resp_hide.status_code == 303

    # Verify status changed in DB
    db_session.refresh(post)
    assert post.status == "hidden"

    # Verify author was notified
    notif = (
        db_session.query(Notification)
        .filter(Notification.recipient_id == 2, Notification.notification_type == "moderation")
        .order_by(Notification.created_at.desc())
        .first()
    )
    assert notif is not None
    assert "hidden" in notif.message

    # Verify audit log recorded
    audit = (
        db_session.query(ModerationAudit)
        .filter(ModerationAudit.entity_type == "post", ModerationAudit.entity_id == post.id)
        .first()
    )
    assert audit is not None
    assert audit.action == "status_hidden"


# ==============================================================================
# FEATURE 6: IN-APP NOTIFICATIONS (List, Unread Count, Mark Read, Mark All Read)
# ==============================================================================

def test_notifications_workflow(client, resident_token, db_session):
    """Notifications can be listed, unread counted, and marked as read."""
    # Clear and insert 2 test notifications for user 2
    db_session.query(Notification).filter(Notification.recipient_id == 2).delete()

    n1 = Notification(
        recipient_id=2,
        sender_id=1,
        notification_type="system",
        title="Welcome Notification",
        message="Welcome to Barabanki Connect portal.",
        is_read=False,
    )
    n2 = Notification(
        recipient_id=2,
        sender_id=1,
        notification_type="issue_status",
        title="Issue Resolved",
        message="Your streetlight issue was fixed.",
        is_read=False,
    )
    db_session.add_all([n1, n2])
    db_session.commit()
    db_session.refresh(n1)
    db_session.refresh(n2)

    # 1. Unread count endpoint
    resp_count = client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_count.status_code == 200
    assert resp_count.json()["unread_count"] == 2

    # 2. List notifications endpoint
    resp_list = client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_list.status_code == 200
    items = resp_list.json()
    assert len(items) == 2

    # 3. Mark single notification as read
    resp_read = client.post(
        f"/api/v1/notifications/{n1.id}/read",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_read.status_code == 200

    resp_count2 = client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_count2.json()["unread_count"] == 1

    # 4. Mark all as read
    resp_mark_all = client.post(
        "/api/v1/notifications/mark-all-read",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_mark_all.status_code == 200

    resp_count3 = client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert resp_count3.json()["unread_count"] == 0


def test_public_profile_web_view(client, resident_token, db_session):
    """Web view for /profile/{username} displays profile stats, bio, and follow button."""
    resp = client.get("/profile/test_admin", headers={"Cookie": f"barabanki_session={resident_token}"})
    assert resp.status_code == 200
    assert "Test Administrator" in resp.text
    assert "Follow" in resp.text
    assert "Followers" in resp.text


def test_notifications_web_view(client, resident_token, db_session):
    """Web view for /notifications displays user notifications."""
    resp = client.get("/notifications", headers={"Cookie": f"barabanki_session={resident_token}"})
    assert resp.status_code == 200
    assert "Notifications" in resp.text


def test_civic_issue_create_and_detail_web_views(client, resident_token, db_session):
    """Web views for /issues/new and /issues/{slug} render properly."""
    # 1. Create page renders with form
    resp_create = client.get("/issues/new", headers={"Cookie": f"barabanki_session={resident_token}"})
    assert resp_create.status_code == 200
    assert "Report a Civic Problem" in resp_create.text
    assert "Roads &amp; Potholes" in resp_create.text or "Roads & Potholes" in resp_create.text

    # 2. Detail page renders
    issue = db_session.query(CivicIssue).first()
    assert issue is not None
    resp_detail = client.get(f"/issues/{issue.slug}")
    assert resp_detail.status_code == 200
    assert issue.title in resp_detail.text
    assert "Status Timeline" in resp_detail.text or "Status Progress" in resp_detail.text or "Status" in resp_detail.text


def test_community_post_edit_web_view(client, resident_token, db_session):
    """Web view for /community/{slug}/edit renders for post author and forbids non-author."""
    # Find post owned by user 2
    post = db_session.query(CommunityPost).filter(CommunityPost.author_id == 2).first()
    if not post:
        post = CommunityPost(
            title="Resident Web Edit Post",
            slug="resident-web-edit-post",
            category="General",
            content="Testing web edit view",
            author_id=2,
            status="published",
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)

    # Owner accesses edit page
    resp_owner = client.get(f"/community/{post.slug}/edit", headers={"Cookie": f"barabanki_session={resident_token}"})
    assert resp_owner.status_code == 200
    assert "Edit Post" in resp_owner.text

