from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base, utc_now

# Standard Verification Badges with Clear Definitions
VERIFICATION_BADGES = {
    "Verified Creator": "Identity confirmed by Barabanki Connect administration as an authentic local creator.",
    "Master Artisan": "Master craftsperson or traditional weaver recognized by district handloom & handicraft clusters.",
    "Community Voice": "Recognized civic contributor, local writer, poet, or public documentarian in Barabanki.",
    "Official Partner": "Verified district administration, educational, or civic institutional partner.",
}


class CreatorProfile(Base):
    __tablename__ = "creator_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    title = Column(String(120), nullable=False)  # e.g., Master Handloom Weaver, Tech Enthusiast, Folk Artist, Poet
    craft_category = Column(String(80), index=True, nullable=False)  # Handloom & Textiles, Digital Art & Code, Literature & Poetry, Music & Folk, Photography, Crafts & Pottery
    bio = Column(Text, nullable=False)
    skills = Column(String(255), nullable=True)  # e.g., Jacquard Weaving, Python, Chikan Embroidery
    locality = Column(String(100), default="Barabanki", index=True, nullable=False)  # Nawabganj, Zaidpur, Fatehpur, Ramnagar, etc.
    languages = Column(String(150), default="Hindi, Awadhi", nullable=True)  # e.g., "Hindi, Awadhi, Urdu"
    content_categories = Column(String(255), nullable=True)  # e.g., "Culture & Heritage, Handloom Reels, Local Stories"
    portfolio_url = Column(String(255), nullable=True)
    profile_photo = Column(String(500), nullable=True)

    # Public Social Links (Strictly validated via domain allowlist)
    instagram = Column(String(255), nullable=True)
    youtube = Column(String(255), nullable=True)
    facebook = Column(String(255), nullable=True)
    linkedin = Column(String(255), nullable=True)
    twitter_x = Column(String(255), nullable=True)
    github = Column(String(255), nullable=True)

    # Admin Verification & Highlights
    is_featured = Column(Boolean, default=False, index=True, nullable=False)
    is_verified = Column(Boolean, default=False, index=True, nullable=False)
    verification_badge = Column(String(60), nullable=True)
    verification_notes = Column(Text, nullable=True)

    # Internal Engagement Analytics
    profile_views = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="creator_profile")
    collaborations = relationship("BusinessCollaboration", back_populates="creator", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CreatorProfile {self.title} (User #{self.user_id})>"


class BusinessCollaboration(Base):
    __tablename__ = "business_collaborations"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("creator_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    campaign_title = Column(String(150), nullable=False)
    campaign_description = Column(Text, nullable=False)
    proposed_deliverables = Column(Text, nullable=False)  # e.g. "1 dedicated reel, 2 story mentions"
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    budget_range = Column(String(80), nullable=True)  # e.g. "₹5,000 - ₹10,000" or "Barter / Product Sample"
    contact_preference = Column(String(50), default="email", nullable=False)  # email, phone, in_app, whatsapp
    contact_details = Column(String(150), nullable=False)

    # Status: pending, accepted, declined, cancelled
    status = Column(String(30), default="pending", index=True, nullable=False)
    creator_response_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    business = relationship("Business", back_populates="collaborations")
    creator = relationship("CreatorProfile", back_populates="collaborations")
    sender = relationship("User")

    def __repr__(self):
        return f"<BusinessCollaboration #{self.id} Biz:{self.business_id} -> Creator:{self.creator_id} ({self.status})>"
