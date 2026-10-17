from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class JobListingBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    company_name: str = Field(..., min_length=2, max_length=200)
    job_type: str = "Full-time"
    category: str = "General"
    location: str = "Barabanki, UP"
    salary_range: Optional[str] = None
    description: str = Field(..., min_length=15)
    requirements: str = Field(..., min_length=10)
    application_email: Optional[str] = None
    application_link: Optional[str] = None
    contact_phone: Optional[str] = None
    is_demo: bool = False


class JobListingCreate(JobListingBase):
    pass


class JobListingOut(JobListingBase):
    id: int
    slug: str
    is_approved: bool
    is_active: bool
    posted_by_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
