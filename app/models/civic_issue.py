from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base, utc_now


class CivicIssue(Base):
    __tablename__ = "civic_issues"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(280), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), default="Roads", index=True, nullable=False)  # Roads & Potholes, Sanitation & Garbage, Water Supply, Electricity, Drainage & Sewage, Streetlights, Public Health, Other
    locality = Column(String(100), default="Barabanki", index=True, nullable=False)  # Nawabganj, Deva, Ramnagar, Fatehpur, Haidergarh, Rudauli, Zaidpur, etc.
    landmark = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    image_url = Column(String(500), nullable=True)
    reported_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), default="Submitted", index=True, nullable=False)  # Submitted, Under Review, In Progress, Resolved, Rejected
    upvotes = Column(Integer, default=0, nullable=False)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    reporter = relationship("User", back_populates="reported_issues")
    status_history = relationship("IssueStatusHistory", back_populates="issue", cascade="all, delete-orphan", order_by="IssueStatusHistory.created_at.asc()")
    upvote_records = relationship("CivicIssueUpvote", back_populates="issue", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CivicIssue #{self.id} {self.title[:30]} [{self.status}]>"


class CivicIssueUpvote(Base):
    __tablename__ = "civic_issue_upvotes"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("civic_issues.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("issue_id", "user_id", name="uq_civic_issue_upvote"),
    )

    issue = relationship("CivicIssue", back_populates="upvote_records")
    user = relationship("User", back_populates="issue_upvotes")

    def __repr__(self):
        return f"<CivicIssueUpvote issue={self.issue_id} user={self.user_id}>"


class IssueStatusHistory(Base):
    __tablename__ = "issue_status_history"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("civic_issues.id", ondelete="CASCADE"), nullable=False, index=True)
    old_status = Column(String(30), nullable=False)
    new_status = Column(String(30), nullable=False)
    notes = Column(Text, nullable=True)
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    issue = relationship("CivicIssue", back_populates="status_history")
    changed_by = relationship("User")

    def __repr__(self):
        return f"<IssueStatusHistory #{self.id} issue={self.issue_id} {self.old_status}->{self.new_status}>"
