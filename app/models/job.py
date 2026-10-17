from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class JobListing(Base):
    __tablename__ = "job_listings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(220), unique=True, index=True, nullable=False)
    company_name = Column(String(200), nullable=False)
    job_type = Column(String(50), default="Full-time", index=True, nullable=False)  # Full-time, Part-time, Internship, Freelance
    category = Column(String(80), default="General", index=True, nullable=False)  # IT & Tech, Education, Sales & Marketing, Healthcare, Manufacturing, Trades
    location = Column(String(150), default="Barabanki, UP", nullable=False)
    salary_range = Column(String(100), nullable=True)  # e.g., ₹15,000 - ₹25,000 / month
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=False)
    application_email = Column(String(120), nullable=True)
    application_link = Column(String(500), nullable=True)
    contact_phone = Column(String(30), nullable=True)
    is_approved = Column(Boolean, default=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, index=True, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    posted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    poster = relationship("User", back_populates="jobs")

    def __repr__(self):
        return f"<JobListing {self.title} @ {self.company_name}>"
