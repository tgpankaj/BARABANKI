from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base, utc_now


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(220), unique=True, index=True, nullable=False)
    category = Column(String(80), index=True, nullable=False)  # Handloom & Textiles, Dining & Sweets, Healthcare, Retail & Groceries, Services, Agro & Fertilizers
    description = Column(Text, nullable=False)
    address = Column(String(255), nullable=False)
    locality = Column(String(100), index=True, nullable=False)  # Nawabganj, Zaidpur, Fatehpur, Ramnagar, Haidergarh, Rudauli
    phone = Column(String(30), nullable=True)
    email = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    opening_hours = Column(String(100), default="10:00 AM - 08:00 PM", nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_approximate_coords = Column(Boolean, default=True, nullable=False)
    image_url = Column(String(500), nullable=True)
    rating = Column(Float, default=4.5, nullable=False)
    is_verified = Column(Boolean, default=False, index=True, nullable=False)
    is_approved = Column(Boolean, default=True, index=True, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)  # Label demo entries clearly
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


    # Relationships
    owner = relationship("User", back_populates="businesses")
    collaborations = relationship("BusinessCollaboration", back_populates="business", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Business {self.name} ({self.locality})>"
