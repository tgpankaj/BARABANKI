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
    capacity: Optional[int] = None


class EventCreate(EventBase):
    pass


class EventRegistrationCreate(BaseModel):
    notes: Optional[str] = None


class EventRegistrationOut(BaseModel):
    id: int
    event_id: int
    user_id: int
    status: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventOut(EventBase):
    id: int
    slug: str
    capacity: Optional[int] = None
    registrations_count: Optional[int] = 0
    is_registered: Optional[bool] = False
    is_approved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

