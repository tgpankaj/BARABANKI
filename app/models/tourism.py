from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float
from app.core.database import Base


class TourismSpot(Base):
    __tablename__ = "tourism_spots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(220), unique=True, index=True, nullable=False)
    category = Column(String(60), index=True, nullable=False)  # Spiritual & Shrines, Ancient Heritage, Botanical Wonders, Architecture
    short_description = Column(String(300), nullable=False)
    historical_background = Column(Text, nullable=False)
    visiting_hours = Column(String(150), default="Open all days, sunrise to sunset", nullable=False)
    entry_fee = Column(String(100), default="Free Entry", nullable=False)
    nearest_railway_station = Column(String(120), default="Barabanki Junction (BBK)", nullable=False)
    distance_from_headquarters = Column(String(100), nullable=True)  # e.g., 12 km from District HQ
    address = Column(String(255), nullable=False)
    locality = Column(String(100), index=True, nullable=False)  # Deva, Kintoor, Ramnagar, Nawabganj
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    is_verified_coordinates = Column(Boolean, default=True, nullable=False)
    image_url = Column(String(500), nullable=True)
    best_time_to_visit = Column(String(120), default="October to March", nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<TourismSpot {self.name}>"
