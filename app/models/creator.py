from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class CreatorProfile(Base):
    __tablename__ = "creator_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    title = Column(String(120), nullable=False)  # e.g., Master Handloom Weaver, Tech Enthusiast, Folk Artist, Poet
    craft_category = Column(String(60), index=True, nullable=False)  # Handloom & Zari, Digital Art & Code, Literature & Poetry, Music & Folk, Photography
    bio = Column(Text, nullable=False)
    skills = Column(String(255), nullable=True)  # e.g., Jacquard Weaving, Python, Chikan Embroidery
    portfolio_url = Column(String(255), nullable=True)
    instagram = Column(String(100), nullable=True)
    youtube = Column(String(100), nullable=True)
    github = Column(String(100), nullable=True)
    is_featured = Column(Boolean, default=False, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="creator_profile")

    def __repr__(self):
        return f"<CreatorProfile {self.title}>"
