from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base, utc_now


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String(50), index=True, nullable=False)  # post, comment, business, job, civic_issue
    target_id = Column(Integer, index=True, nullable=False)
    reason = Column(String(100), nullable=False)  # Spam, Harassment, Misinformation, Inappropriate, Other
    details = Column(Text, nullable=True)
    reported_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), default="pending", index=True, nullable=False)  # pending, resolved, dismissed
    action_taken = Column(String(100), nullable=True)
    moderator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    moderator_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    moderator = relationship("User", foreign_keys=[moderator_id])

    def __repr__(self):
        return f"<Report #{self.id} on {self.target_type}:{self.target_id} [{self.status}]>"


class ModerationAudit(Base):
    __tablename__ = "moderation_audits"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # post, comment, event, business, civic_issue, report
    entity_id = Column(Integer, nullable=False, index=True)
    moderator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)  # approved, rejected, hidden, resolved, dismissed, edited
    reason = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    moderator = relationship("User", foreign_keys=[moderator_id])

    def __repr__(self):
        return f"<ModerationAudit {self.action} on {self.entity_type}:{self.entity_id} by User {self.moderator_id}>"

