from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class EventBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    category: str = "Cultural"
    start_date: datetime
    end_date: Optional[datetime] = None
    venue_name: str
    address: str
    locality: str = "Barabanki"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_approximate_coords: bool = True
    organizer_name: str
    organizer_contact: Optional[str] = None
    registration_link: Optional[str] = None
    image_url: Optional[str] = None


class EventCreate(EventBase):
    pass


class EventOut(EventBase):
    id: int
    slug: str
    is_approved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
