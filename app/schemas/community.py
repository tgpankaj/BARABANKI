from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class CommentBase(BaseModel):
    content: str = Field(..., min_length=2)


class CommentCreate(CommentBase):
    pass


class CommentOut(CommentBase):
    id: int
    post_id: int
    author_id: int
    author_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommunityPostBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    content: str = Field(..., min_length=10)
    category: str = "Discussion"


class CommunityPostCreate(CommunityPostBase):
    pass


class CommunityPostOut(CommunityPostBase):
    id: int
    slug: str
    author_id: int
    author_name: Optional[str] = None
    upvotes: int
    status: str
    comments_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportCreate(BaseModel):
    target_type: str  # post, comment, business, job
    target_id: int
    reason: str
    details: Optional[str] = None
