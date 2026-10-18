from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base, utc_now


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
    capacity = Column(Integer, nullable=True)
    is_approved = Column(Boolean, default=True, index=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    registrations = relationship("EventRegistration", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Event {self.title[:30]}>"


class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="confirmed", nullable=False)  # confirmed, cancelled
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_registration"),
    )

    event = relationship("Event", back_populates="registrations")
    user = relationship("User", back_populates="event_registrations")

    def __repr__(self):
        return f"<EventRegistration event={self.event_id} user={self.user_id} [{self.status}]>"

