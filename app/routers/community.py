import math
from typing import Optional, List
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user_optional, get_current_user
from app.core.security import generate_csrf_token, validate_csrf_token
from app.models.community import CommunityPost, Comment
from app.models.report import Report
from app.schemas.community import CommunityPostCreate, CommunityPostOut, CommentCreate, CommentOut, ReportCreate

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- WEB HTML ROUTES ---

@router.get("/community", response_class=HTMLResponse)
def community_list_view(
    request: Request,
    page: int = Query(1, ge=1),
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    page_size = settings.DEFAULT_PAGE_SIZE
    query = db.query(CommunityPost).filter(CommunityPost.status == "published")

    if category:
        query = query.filter(CommunityPost.category == category)

    total_posts = query.count()
    total_pages = math.ceil(total_posts / page_size) or 1
    offset = (page - 1) * page_size

    posts = query.order_by(CommunityPost.created_at.desc()).offset(offset).limit(page_size).all()

    return templates.TemplateResponse(
        request=request,
        name="community/list.html",
        context={
            "active_page": "community",
            "current_user": current_user,
            "posts": posts,
            "current_page": page,
            "total_pages": total_pages,
            "current_category": category,
        },
    )


@router.get("/community/new", response_class=HTMLResponse)
def community_create_view(
    request: Request,
    current_user = Depends(get_current_user_optional),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    return templates.TemplateResponse(
        request=request,
        name="community/create.html",
        context={
            "active_page": "community",
            "current_user": current_user,
            "csrf_token": csrf_token,
        },
    )


@router.post("/community/new")
def community_create_action(
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    content: str = Form(...),
    csrf_token: str = Form(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        return RedirectResponse(url="/community/new", status_code=303)

    from app.seeds.seed_data import slugify
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    while db.query(CommunityPost).filter(CommunityPost.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    post = CommunityPost(
        title=title.strip(),
        slug=slug,
        category=category.strip(),
        content=content.strip(),
        author_id=current_user.id,
        upvotes=1,
        status="published",
    )
    db.add(post)
    db.commit()
    return RedirectResponse(url=f"/community/{slug}", status_code=303)


@router.get("/community/{slug}", response_class=HTMLResponse)
def community_detail_view(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    post = db.query(CommunityPost).filter(CommunityPost.slug == slug, CommunityPost.status == "published").first()
    if not post:
        raise HTTPException(status_code=404, detail="Discussion thread not found.")

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    return templates.TemplateResponse(
        request=request,
        name="community/detail.html",
        context={
            "active_page": "community",
            "current_user": current_user,
            "post": post,
            "csrf_token": csrf_token,
        },
    )


@router.post("/community/{slug}/comment")
def community_add_comment(
    slug: str,
    request: Request,
    content: str = Form(...),
    csrf_token: str = Form(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        return RedirectResponse(url=f"/community/{slug}", status_code=303)

    post = db.query(CommunityPost).filter(CommunityPost.slug == slug).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    comment = Comment(
        post_id=post.id,
        author_id=current_user.id,
        content=content.strip(),
    )
    db.add(comment)
    db.commit()
    return RedirectResponse(url=f"/community/{slug}", status_code=303)


@router.post("/community/{slug}/upvote")
def community_upvote_post(
    slug: str,
    request: Request,
    csrf_token: str = Form(None),
    db: Session = Depends(get_db),
):
    post = db.query(CommunityPost).filter(CommunityPost.slug == slug).first()
    if post:
        post.upvotes += 1
        db.commit()
    return RedirectResponse(url=f"/community/{slug}", status_code=303)


@router.post("/community/report")
def community_report_action(
    request: Request,
    target_type: str = Form(...),
    target_id: int = Form(...),
    reason: str = Form(...),
    details: Optional[str] = Form(None),
    csrf_token: str = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    session_id = request.client.host if request.client else "bbk_guest"
    validate_csrf_token(csrf_token, session_id)

    rep = Report(
        target_type=target_type.strip(),
        target_id=target_id,
        reason=reason.strip(),
        details=details.strip() if details else None,
        reported_by_id=current_user.id if current_user else None,
        status="pending",
    )
    db.add(rep)
    db.commit()
    return RedirectResponse(url="/community?msg=Report+submitted+for+review", status_code=303)


# --- REST API ROUTES ---

@router.get("/api/v1/community/posts", response_model=List[CommunityPostOut])
def api_get_posts(
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(CommunityPost).filter(CommunityPost.status == "published")
    if category:
        query = query.filter(CommunityPost.category == category)
    return query.order_by(CommunityPost.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/api/v1/community/posts/{slug}", response_model=CommunityPostOut)
def api_get_post(
    slug: str,
    db: Session = Depends(get_db),
):
    post = db.query(CommunityPost).filter(CommunityPost.slug == slug, CommunityPost.status == "published").first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    return post


@router.post("/api/v1/community/posts", response_model=CommunityPostOut, status_code=status.HTTP_201_CREATED)
def api_create_post(
    payload: CommunityPostCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.seeds.seed_data import slugify
    base_slug = slugify(payload.title)
    slug = base_slug
    counter = 1
    while db.query(CommunityPost).filter(CommunityPost.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    post = CommunityPost(
        title=payload.title,
        slug=slug,
        category=payload.category,
        content=payload.content,
        author_id=current_user.id,
        upvotes=1,
        status="published",
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.post("/api/v1/community/posts/{slug}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def api_create_comment(
    slug: str,
    payload: CommentCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(CommunityPost).filter(CommunityPost.slug == slug).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    comment = Comment(
        post_id=post.id,
        author_id=current_user.id,
        content=payload.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
