from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class EducationInstituteBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    category: str = "College"
    affiliation: Optional[str] = None
    address: str
    locality: str = "Barabanki"
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    description: str = Field(..., min_length=15)
    courses_offered: str
    admission_info: Optional[str] = None


class EducationInstituteCreate(EducationInstituteBase):
    pass


class EducationInstituteOut(EducationInstituteBase):
    id: int
    slug: str
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
