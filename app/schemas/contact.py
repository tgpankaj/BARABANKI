from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ContactMessageCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=100, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: Optional[str] = None
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=10)


class ContactMessageOut(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    subject: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
