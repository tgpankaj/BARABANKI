from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class NewsArticleBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    summary: str = Field(..., min_length=10)
    content: str = Field(..., min_length=20)
    category: str = "Civic"
    source_attribution: str = Field(..., min_length=3, max_length=255)
    image_url: Optional[str] = None


class NewsArticleCreate(NewsArticleBase):
    pass


class NewsArticleUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    source_attribution: Optional[str] = None
    image_url: Optional[str] = None
    is_published: Optional[bool] = None


class NewsArticleOut(NewsArticleBase):
    id: int
    slug: str
    author_id: Optional[int] = None
    is_published: bool
    views_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
