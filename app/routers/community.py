import math
from typing import Optional, List
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, utc_now
from app.core.dependencies import get_current_user_optional, get_current_user
from app.core.security import generate_csrf_token, validate_csrf_token
from app.models.community import CommunityPost, Comment, PostLike
from app.models.report import Report
from app.models.notification import Notification
from app.schemas.community import (
    CommunityPostCreate,
    CommunityPostUpdate,
    CommunityPostOut,
    CommentCreate,
    CommentOut,
    PostLikeOut,
    ReportCreate,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- WEB HTML ROUTES ---

@router.get("/community", response_class=HTMLResponse)
def community_list_view(
    request: Request,
    page: int = Query(1, ge=1),
    category: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    page_size = settings.DEFAULT_PAGE_SIZE
    query = db.query(CommunityPost).filter(CommunityPost.status == "published")

    if category and category != "All":
        query = query.filter(CommunityPost.category == category)
    if q:
        query = query.filter(CommunityPost.title.ilike(f"%{q.strip()}%") | CommunityPost.content.ilike(f"%{q.strip()}%"))

    total_posts = query.count()
    total_pages = math.ceil(total_posts / page_size) or 1
    offset = (page - 1) * page_size

    posts = query.order_by(CommunityPost.created_at.desc()).offset(offset).limit(page_size).all()

    user_liked_post_ids = set()
    if current_user:
        likes = db.query(PostLike.post_id).filter(PostLike.user_id == current_user.id).all()
        user_liked_post_ids = {l[0] for l in likes}

    return templates.TemplateResponse(
        request=request,
        name="community/list.html",
        context={
            "active_page": "community",
            "current_user": current_user,
            "posts": posts,
            "current_page": page,
            "total_pages": total_pages,
            "current_category": category or "All",
            "search_query": q or "",
            "user_liked_post_ids": user_liked_post_ids,
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
    image_url: Optional[str] = Form(None),
    csrf_token: str = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

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
        image_url=image_url.strip() if image_url else None,
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
    post = db.query(CommunityPost).filter(CommunityPost.slug == slug).first()
    if not post or (post.status != "published" and (not current_user or (current_user.id != post.author_id and current_user.role not in ["admin", "moderator"]))):
        raise HTTPException(status_code=404, detail="Discussion thread not found.")

    has_liked = False
    if current_user:
        has_liked = bool(db.query(PostLike).filter(PostLike.post_id == post.id, PostLike.user_id == current_user.id).first())

    is_owner = bool(current_user and (current_user.id == post.author_id or current_user.role in ["admin", "moderator"]))
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    return templates.TemplateResponse(
        request=request,
        name="community/detail.html",
        context={
            "active_page": "community",
            "current_user": current_user,
            "post": post,
            "has_liked": has_liked,
            "is_owner": is_owner,
            "csrf_token": csrf_token,
        },
    )


@router.get("/community/{slug}/edit", response_class=HTMLResponse)
def community_edit_view(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    post = db.query(CommunityPost).filter(CommunityPost.slug == slug).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    if post.author_id != current_user.id and current_user.role not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="You do not have permission to edit this post.")

    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    return templates.TemplateResponse(
        request=request,
        name="community/edit.html",
        context={
            "active_page": "community",
            "current_user": current_user,
            "post": post,
            "csrf_token": csrf_token,
        },
    )


@router.post("/community/{slug}/edit")
def community_edit_action(
    slug: str,
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    content: str = Form(...),
    image_url: Optional[str] = Form(None),
    csrf_token: str = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        return RedirectResponse(url=f"/community/{slug}/edit", status_code=303)

    post = db.query(CommunityPost).filter(CommunityPost.slug == slug).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    if post.author_id != current_user.id and current_user.role not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="You do not have permission to edit this post.")

    post.title = title.strip()
    post.category = category.strip()
    post.content = content.strip()
    post.image_url = image_url.strip() if image_url else None
    post.updated_at = utc_now()
    db.commit()

    return RedirectResponse(url=f"/community/{slug}?msg=Post+updated+successfully", status_code=303)


@router.post("/community/{slug}/delete")
def community_delete_action(
    slug: str,
    request: Request,
    csrf_token: Optional[str] = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    post = db.query(CommunityPost).filter(CommunityPost.slug == slug).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    if post.author_id != current_user.id and current_user.role not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this post.")

    db.delete(post)
    db.commit()
    return RedirectResponse(url="/community?msg=Post+deleted+successfully", status_code=303)


@router.post("/community/{slug}/like")
@router.post("/community/{slug}/upvote")
def community_toggle_like(
    slug: str,
    request: Request,
    csrf_token: Optional[str] = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        if request.headers.get("accept") == "application/json":
            raise HTTPException(status_code=401, detail="Authentication required to like posts.")
        return RedirectResponse(url="/auth/login", status_code=303)

    post = db.query(CommunityPost).filter(CommunityPost.slug == slug).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    existing_like = db.query(PostLike).filter(PostLike.post_id == post.id, PostLike.user_id == current_user.id).first()
    if existing_like:
        db.delete(existing_like)
        post.upvotes = max(0, post.upvotes - 1)
        liked = False
    else:
        new_like = PostLike(post_id=post.id, user_id=current_user.id)
        db.add(new_like)
        post.upvotes += 1
        liked = True

        # Send notification to post author if not liking own post
        if post.author_id != current_user.id:
            notif = Notification(
                recipient_id=post.author_id,
                sender_id=current_user.id,
                notification_type="like",
                title="New Like on your post",
                message=f"{current_user.full_name} liked your post: '{post.title[:35]}'",
                link=f"/community/{post.slug}",
            )
            db.add(notif)

    db.commit()

    if request.headers.get("accept") == "application/json":
        return JSONResponse({"post_id": post.id, "upvotes": post.upvotes, "liked": liked})
    return RedirectResponse(url=f"/community/{slug}", status_code=303)


@router.post("/community/{slug}/comment")
def community_add_comment(
    slug: str,
    request: Request,
    content: str = Form(...),
    csrf_token: str = Form(None),
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

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

    # Persistent notification to post author
    if post.author_id != current_user.id:
        notif = Notification(
            recipient_id=post.author_id,
            sender_id=current_user.id,
            notification_type="comment",
            title="New comment on your post",
            message=f"{current_user.full_name} commented on '{post.title[:30]}'",
            link=f"/community/{post.slug}",
        )
        db.add(notif)

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
    q: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    query = db.query(CommunityPost).filter(CommunityPost.status == "published")
    if category and category != "All":
        query = query.filter(CommunityPost.category == category)
    if q:
        query = query.filter(CommunityPost.title.ilike(f"%{q.strip()}%") | CommunityPost.content.ilike(f"%{q.strip()}%"))

    posts = query.order_by(CommunityPost.created_at.desc()).offset(offset).limit(limit).all()

    user_liked_post_ids = set()
    if current_user:
        likes = db.query(PostLike.post_id).filter(PostLike.user_id == current_user.id).all()
        user_liked_post_ids = {l[0] for l in likes}

    result = []
    for p in posts:
        out = CommunityPostOut.model_validate(p)
        out.author_name = p.author.full_name if p.author else "Barabanki Resident"
        out.comments_count = len(p.comments)
        out.has_liked = p.id in user_liked_post_ids
        result.append(out)

    return result


@router.get("/api/v1/community/posts/{slug}", response_model=CommunityPostOut)
def api_get_post(
    slug: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    post = db.query(CommunityPost).filter(CommunityPost.slug == slug).first()
    if not post or (post.status != "published" and (not current_user or (current_user.id != post.author_id and current_user.role not in ["admin", "moderator"]))):
        raise HTTPException(status_code=404, detail="Post not found.")

    out = CommunityPostOut.model_validate(post)
    out.author_name = post.author.full_name if post.author else "Barabanki Resident"
    out.comments_count = len(post.comments)
    if current_user:
        out.has_liked = bool(db.query(PostLike).filter(PostLike.post_id == post.id, PostLike.user_id == current_user.id).first())
    return out


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
        image_url=payload.image_url,
        author_id=current_user.id,
        upvotes=1,
        status="published",
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    out = CommunityPostOut.model_validate(post)
    out.author_name = current_user.full_name
    out.comments_count = 0
    out.has_liked = False
    return out




@router.put("/api/v1/community/posts/{slug}", response_model=CommunityPostOut)
def api_update_post(
    slug: str,
    payload: CommunityPostUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(CommunityPost).filter(CommunityPost.slug == slug).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    if post.author_id != current_user.id and current_user.role not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="You do not have permission to edit this post.")

    if payload.title is not None:
        post.title = payload.title
    if payload.content is not None:
        post.content = payload.content
    if payload.category is not None:
        post.category = payload.category
    if payload.image_url is not None:
        post.image_url = payload.image_url
    post.updated_at = utc_now()
    db.commit()
    db.refresh(post)

    out = CommunityPostOut.model_validate(post)
    out.author_name = post.author.full_name if post.author else "Barabanki Resident"
    out.comments_count = len(post.comments)
    out.has_liked = bool(db.query(PostLike).filter(PostLike.post_id == post.id, PostLike.user_id == current_user.id).first())
    return out


@router.delete("/api/v1/community/posts/{slug}")
def api_delete_post(
    slug: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(CommunityPost).filter(CommunityPost.slug == slug).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    if post.author_id != current_user.id and current_user.role not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this post.")

    db.delete(post)
    db.commit()
    return {"message": "Post deleted successfully", "slug": slug}


@router.post("/api/v1/community/posts/{slug}/like", response_model=PostLikeOut)
def api_like_post(
    slug: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(CommunityPost).filter(CommunityPost.slug == slug).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    existing_like = db.query(PostLike).filter(PostLike.post_id == post.id, PostLike.user_id == current_user.id).first()
    if existing_like:
        db.delete(existing_like)
        post.upvotes = max(0, post.upvotes - 1)
        liked = False
    else:
        new_like = PostLike(post_id=post.id, user_id=current_user.id)
        db.add(new_like)
        post.upvotes += 1
        liked = True

        if post.author_id != current_user.id:
            notif = Notification(
                recipient_id=post.author_id,
                sender_id=current_user.id,
                notification_type="like",
                title="New Like on your post",
                message=f"{current_user.full_name} liked your post: '{post.title[:35]}'",
                link=f"/community/{post.slug}",
            )
            db.add(notif)

    db.commit()
    return PostLikeOut(post_id=post.id, user_id=current_user.id, upvotes=post.upvotes, liked=liked)


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

    if post.author_id != current_user.id:
        notif = Notification(
            recipient_id=post.author_id,
            sender_id=current_user.id,
            notification_type="comment",
            title="New comment on your post",
            message=f"{current_user.full_name} commented on '{post.title[:30]}'",
            link=f"/community/{post.slug}",
        )
        db.add(notif)

    db.commit()
    db.refresh(comment)

    out = CommentOut.model_validate(comment)
    out.author_name = current_user.full_name
    return out


@router.post("/api/v1/community/report")
def api_report(
    payload: ReportCreate,
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    rep = Report(
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        details=payload.details,
        reported_by_id=current_user.id if current_user else None,
        status="pending",
    )
    db.add(rep)
    db.commit()
    return {"message": "Report submitted for review", "report_id": rep.id}
