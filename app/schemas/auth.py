from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: str = Field(..., min_length=5, max_length=100, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    phone: Optional[str] = None
    role: Optional[str] = "resident"


class UserLogin(BaseModel):
    email_or_username: str
    password: str


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserPasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
