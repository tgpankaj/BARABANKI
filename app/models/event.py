from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float
from app.core.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), default="Cultural", index=True, nullable=False)  # Cultural, Religious, Educational, Civic, Sports
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=True)
    venue_name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    locality = Column(String(100), default="Barabanki", index=True, nullable=False)  # Nawabganj, Deva, Ramnagar, etc.
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_approximate_coords = Column(Boolean, default=True, nullable=False)  # Transparency for map coords
    organizer_name = Column(String(150), nullable=False)
    organizer_contact = Column(String(100), nullable=True)
    registration_link = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    is_approved = Column(Boolean, default=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Event {self.title[:30]}>"
