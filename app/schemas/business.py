from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class BusinessBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    category: str = Field(..., min_length=2, max_length=80)
    description: str = Field(..., min_length=10)
    address: str
    locality: str
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    opening_hours: Optional[str] = "10:00 AM - 08:00 PM"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_approximate_coords: bool = True
    image_url: Optional[str] = None
    is_demo: bool = False


class BusinessCreate(BusinessBase):
    pass


class BusinessOut(BusinessBase):
    id: int
    slug: str
    rating: float
    is_verified: bool
    is_approved: bool
    created_by_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
