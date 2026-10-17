from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    summary = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), default="Civic", index=True, nullable=False)  # Administration, Development, Culture, Sports, Education
    source_attribution = Column(String(255), nullable=False)  # Clear attribution per Real Data Policy
    image_url = Column(String(500), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_published = Column(Boolean, default=True, index=True, nullable=False)
    views_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    author = relationship("User", back_populates="news_articles")

    def __repr__(self):
        return f"<NewsArticle {self.title[:30]}>"
