from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String(50), index=True, nullable=False)  # post, comment, business, job
    target_id = Column(Integer, index=True, nullable=False)
    reason = Column(String(100), nullable=False)  # Spam, Harassment, Misinformation, Inappropriate, Other
    details = Column(Text, nullable=True)
    reported_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), default="pending", index=True, nullable=False)  # pending, resolved, dismissed
    action_taken = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Report #{self.id} on {self.target_type}:{self.target_id} [{self.status}]>"
