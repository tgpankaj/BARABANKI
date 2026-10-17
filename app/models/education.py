from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.core.database import Base


class EducationInstitute(Base):
    __tablename__ = "education_institutes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(220), unique=True, index=True, nullable=False)
    category = Column(String(50), index=True, nullable=False)  # College, School, Polytechnic / ITI, Coaching Centre, Vocational
    affiliation = Column(String(150), nullable=True)  # e.g., AKTU, Dr. RMLAU, CBSE, UP Board, BTEUP
    address = Column(String(255), nullable=False)
    locality = Column(String(100), default="Barabanki", index=True, nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    description = Column(Text, nullable=False)
    courses_offered = Column(Text, nullable=False)  # Comma-separated or bullet list
    admission_info = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<EducationInstitute {self.name}>"
