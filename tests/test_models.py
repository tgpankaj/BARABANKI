from datetime import datetime
from app.models import (
    User,
    NewsArticle,
    Event,
    Business,
    JobListing,
    EducationInstitute,
    CommunityPost,
    Comment,
    TourismSpot,
    ContactMessage,
    Report,
)


def test_user_model_representation():
    u = User(username="test_user", email="test@bbk.in", full_name="Test User", role="resident")
    assert "test_user" in repr(u)
    assert "resident" in repr(u)


def test_news_model_fields(db_session):
    article = NewsArticle(
        title="Test News Title",
        slug="test-news-title",
        summary="A short summary",
        content="Full content of the news article",
        source_attribution="Official Test Source",
    )
    db_session.add(article)
    db_session.flush()
    assert article.title == "Test News Title"
    assert article.views_count == 0
    assert repr(article).startswith("<NewsArticle")


def test_business_model_defaults(db_session):
    biz = Business(
        name="Test Handlooms",
        slug="test-handlooms",
        category="Handloom & Textiles",
        address="Main Market",
        locality="Zaidpur",
        description="Authentic weavers collective",
    )
    db_session.add(biz)
    db_session.flush()
    assert biz.rating == 4.5
    assert biz.is_verified is False
    assert "Zaidpur" in repr(biz)


def test_job_listing_defaults(db_session):
    job = JobListing(
        title="Data Operator",
        slug="data-operator",
        company_name="Local Enterprise",
        description="Data entry tasks",
        requirements="Basic typing skills",
    )
    db_session.add(job)
    db_session.flush()
    assert job.job_type == "Full-time"
    assert job.is_active is True
    assert "Local Enterprise" in repr(job)


def test_tourism_spot_model(db_session):
    spot = TourismSpot(
        name="Deva Sharif Test",
        slug="deva-sharif-test",
        category="Spiritual",
        short_description="Shrine of Waris Ali Shah",
        historical_background="Detailed background",
        address="Deva Sharif, Barabanki",
        locality="Deva",
        latitude=27.0223,
        longitude=81.1685,
    )
    db_session.add(spot)
    db_session.flush()
    assert spot.entry_fee == "Free Entry"
    assert repr(spot) == "<TourismSpot Deva Sharif Test>"


def test_community_post_and_comment(db_session):
    post = CommunityPost(
        title="Public Transit Idea",
        slug="public-transit-idea",
        content="Ideas for transit",
        author_id=1,
    )
    db_session.add(post)
    db_session.flush()
    assert post.upvotes == 0
    assert post.status == "published"

    comment = Comment(
        post_id=post.id,
        author_id=1,
        content="Agreed, this is vital.",
    )
    db_session.add(comment)
    db_session.flush()
    assert comment.is_hidden is False
