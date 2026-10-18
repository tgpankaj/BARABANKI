from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    id: int
    recipient_id: int
    sender_id: Optional[int] = None
    sender_name: Optional[str] = None
    notification_type: str
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationCountOut(BaseModel):
    unread_count: int
