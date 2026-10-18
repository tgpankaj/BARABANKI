from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.core.database import Base, utc_now


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=True)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, index=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


    def __repr__(self):
        return f"<ContactMessage #{self.id} from {self.name}>"
