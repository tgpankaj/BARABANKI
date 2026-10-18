from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class CivicIssueBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10)
    category: str = "Roads"
    locality: str = "Barabanki"
    landmark: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None


class CivicIssueCreate(CivicIssueBase):
    pass


class CivicIssueUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=10)
    category: Optional[str] = None
    locality: Optional[str] = None
    landmark: Optional[str] = None
    image_url: Optional[str] = None


class IssueStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(Submitted|Under Review|In Progress|Resolved|Rejected)$")
    notes: Optional[str] = None


class IssueStatusHistoryOut(BaseModel):
    id: int
    issue_id: int
    old_status: str
    new_status: str
    notes: Optional[str] = None
    changed_by_id: Optional[int] = None
    changed_by_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CivicIssueOut(CivicIssueBase):
    id: int
    slug: str
    reported_by_id: int
    reporter_name: Optional[str] = None
    status: str
    upvotes: int
    admin_notes: Optional[str] = None
    has_upvoted: Optional[bool] = False
    created_at: datetime
    updated_at: datetime
    status_history: List[IssueStatusHistoryOut] = []

    model_config = ConfigDict(from_attributes=True)
