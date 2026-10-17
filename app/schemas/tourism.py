from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class TourismSpotBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    category: str
    short_description: str
    historical_background: str
    visiting_hours: str = "Open all days"
    entry_fee: str = "Free Entry"
    nearest_railway_station: str = "Barabanki Junction (BBK)"
    distance_from_headquarters: Optional[str] = None
    address: str
    locality: str
    latitude: float
    longitude: float
    is_verified_coordinates: bool = True
    image_url: Optional[str] = None
    best_time_to_visit: Optional[str] = "October to March"


class TourismSpotCreate(TourismSpotBase):
    pass


class TourismSpotOut(TourismSpotBase):
    id: int
    slug: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
