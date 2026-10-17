import math
from typing import Optional, List
from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user_optional, require_admin
from app.models.news import NewsArticle
from app.schemas.news import NewsArticleCreate, NewsArticleOut

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- WEB HTML ROUTES ---

@router.get("/news", response_class=HTMLResponse)
def news_list_view(
    request: Request,
    page: int = Query(1, ge=1),
    category: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    page_size = settings.DEFAULT_PAGE_SIZE
    query = db.query(NewsArticle).filter(NewsArticle.is_published == True)

    if category:
        query = query.filter(NewsArticle.category == category)
    if q:
        query = query.filter(NewsArticle.title.ilike(f"%{q.strip()}%"))

    total_articles = query.count()
    total_pages = math.ceil(total_articles / page_size) or 1
    offset = (page - 1) * page_size

    articles = query.order_by(NewsArticle.created_at.desc()).offset(offset).limit(page_size).all()

    return templates.TemplateResponse(
        request=request,
        name="news/list.html",
        context={
            "active_page": "news",
            "current_user": current_user,
            "articles": articles,
            "current_page": page,
            "total_pages": total_pages,
            "current_category": category,
            "q": q,
        },
    )


@router.get("/news/{slug}", response_class=HTMLResponse)
def news_detail_view(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    article = db.query(NewsArticle).filter(NewsArticle.slug == slug, NewsArticle.is_published == True).first()
    if not article:
        raise HTTPException(status_code=404, detail="News article not found.")

    # Increment view count
    article.views_count += 1
    db.commit()

    return templates.TemplateResponse(
        request=request,
        name="news/detail.html",
        context={
            "active_page": "news",
            "current_user": current_user,
            "article": article,
        },
    )


# --- REST API ROUTES ---

@router.get("/api/v1/news", response_model=List[NewsArticleOut])
def api_get_news(
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(NewsArticle).filter(NewsArticle.is_published == True)
    if category:
        query = query.filter(NewsArticle.category == category)
    return query.order_by(NewsArticle.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/api/v1/news/{slug}", response_model=NewsArticleOut)
def api_get_article(
    slug: str,
    db: Session = Depends(get_db),
):
    article = db.query(NewsArticle).filter(NewsArticle.slug == slug, NewsArticle.is_published == True).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")
    article.views_count += 1
    db.commit()
    return article


@router.post("/api/v1/news", response_model=NewsArticleOut, status_code=status.HTTP_201_CREATED)
def api_create_article(
    payload: NewsArticleCreate,
    current_admin = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.seeds.seed_data import slugify
    slug = slugify(payload.title)

    article = NewsArticle(
        title=payload.title,
        slug=slug,
        summary=payload.summary,
        content=payload.content,
        category=payload.category,
        source_attribution=payload.source_attribution,
        image_url=payload.image_url,
        author_id=current_admin.id,
        is_published=True,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article
