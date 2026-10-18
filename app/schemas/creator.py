from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.core.social_validator import validate_social_url, validate_portfolio_url
from app.models.creator import VERIFICATION_BADGES


class CreatorProfileBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=120)
    craft_category: str = Field(..., min_length=2, max_length=80)
    bio: str = Field(..., min_length=10)
    skills: Optional[str] = Field(None, max_length=255)
    locality: str = Field("Barabanki", max_length=100)
    languages: Optional[str] = Field("Hindi, Awadhi", max_length=150)
    content_categories: Optional[str] = Field(None, max_length=255)
    portfolio_url: Optional[str] = None
    profile_photo: Optional[str] = None

    # Social profile links
    instagram: Optional[str] = None
    youtube: Optional[str] = None
    facebook: Optional[str] = None
    linkedin: Optional[str] = None
    twitter_x: Optional[str] = None
    github: Optional[str] = None

    @field_validator("instagram", mode="before")
    @classmethod
    def validate_ig(cls, v):
        return validate_social_url("instagram", v)

    @field_validator("youtube", mode="before")
    @classmethod
    def validate_yt(cls, v):
        return validate_social_url("youtube", v)

    @field_validator("facebook", mode="before")
    @classmethod
    def validate_fb(cls, v):
        return validate_social_url("facebook", v)

    @field_validator("linkedin", mode="before")
    @classmethod
    def validate_li(cls, v):
        return validate_social_url("linkedin", v)

    @field_validator("twitter_x", mode="before")
    @classmethod
    def validate_x(cls, v):
        return validate_social_url("twitter_x", v)

    @field_validator("github", mode="before")
    @classmethod
    def validate_gh(cls, v):
        return validate_social_url("github", v)

    @field_validator("portfolio_url", mode="before")
    @classmethod
    def validate_port(cls, v):
        return validate_portfolio_url(v)


class CreatorProfileCreate(CreatorProfileBase):
    pass


class CreatorProfileUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=120)
    craft_category: Optional[str] = Field(None, min_length=2, max_length=80)
    bio: Optional[str] = Field(None, min_length=10)
    skills: Optional[str] = Field(None, max_length=255)
    locality: Optional[str] = Field(None, max_length=100)
    languages: Optional[str] = Field(None, max_length=150)
    content_categories: Optional[str] = Field(None, max_length=255)
    portfolio_url: Optional[str] = None
    profile_photo: Optional[str] = None

    instagram: Optional[str] = None
    youtube: Optional[str] = None
    facebook: Optional[str] = None
    linkedin: Optional[str] = None
    twitter_x: Optional[str] = None
    github: Optional[str] = None

    @field_validator("instagram", mode="before")
    @classmethod
    def validate_ig(cls, v):
        return validate_social_url("instagram", v)

    @field_validator("youtube", mode="before")
    @classmethod
    def validate_yt(cls, v):
        return validate_social_url("youtube", v)

    @field_validator("facebook", mode="before")
    @classmethod
    def validate_fb(cls, v):
        return validate_social_url("facebook", v)

    @field_validator("linkedin", mode="before")
    @classmethod
    def validate_li(cls, v):
        return validate_social_url("linkedin", v)

    @field_validator("twitter_x", mode="before")
    @classmethod
    def validate_x(cls, v):
        return validate_social_url("twitter_x", v)

    @field_validator("github", mode="before")
    @classmethod
    def validate_gh(cls, v):
        return validate_social_url("github", v)

    @field_validator("portfolio_url", mode="before")
    @classmethod
    def validate_port(cls, v):
        return validate_portfolio_url(v)


class CreatorProfileOut(CreatorProfileBase):
    id: int
    user_id: int
    name: str
    username: str
    is_featured: bool
    is_verified: bool
    verification_badge: Optional[str] = None
    verification_meaning: Optional[str] = None
    verification_notes: Optional[str] = None
    followers_count: int = 0
    profile_views: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_metrics(cls, obj, followers_count: int = 0, posts_count: int = 0):
        user = obj.user
        meaning = VERIFICATION_BADGES.get(obj.verification_badge) if obj.verification_badge else None
        return cls(
            id=obj.id,
            user_id=obj.user_id,
            name=user.full_name if user else "Creator",
            username=user.username if user else f"creator_{obj.id}",
            title=obj.title,
            craft_category=obj.craft_category,
            bio=obj.bio,
            skills=obj.skills,
            locality=obj.locality,
            languages=obj.languages,
            content_categories=obj.content_categories,
            portfolio_url=obj.portfolio_url,
            profile_photo=obj.profile_photo,
            instagram=obj.instagram,
            youtube=obj.youtube,
            facebook=obj.facebook,
            linkedin=obj.linkedin,
            twitter_x=obj.twitter_x,
            github=obj.github,
            is_featured=obj.is_featured,
            is_verified=obj.is_verified,
            verification_badge=obj.verification_badge,
            verification_meaning=meaning,
            verification_notes=obj.verification_notes,
            followers_count=followers_count,
            profile_views=obj.profile_views or 0,
            created_at=obj.created_at,
            updated_at=obj.updated_at or obj.created_at,
        )


class CreatorVerificationUpdate(BaseModel):
    is_verified: bool
    verification_badge: Optional[str] = Field(None, max_length=60)
    verification_notes: Optional[str] = None


class BusinessCollaborationCreate(BaseModel):
    business_id: int
    campaign_title: str = Field(..., min_length=5, max_length=150)
    campaign_description: str = Field(..., min_length=20)
    proposed_deliverables: str = Field(..., min_length=10)
    start_date: Optional[str] = Field(None, max_length=50)
    end_date: Optional[str] = Field(None, max_length=50)
    budget_range: Optional[str] = Field(None, max_length=80)
    contact_preference: str = Field("email", max_length=50)
    contact_details: str = Field(..., min_length=3, max_length=150)


class BusinessCollaborationStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(accepted|declined|cancelled)$")
    creator_response_notes: Optional[str] = None
    response_notes: Optional[str] = None


class BusinessCollaborationOut(BaseModel):
    id: int
    business_id: int
    business_name: str
    creator_id: int
    creator_name: str
    sender_user_id: int
    campaign_title: str
    campaign_description: str
    proposed_deliverables: str
    start_date: Optional[str]
    end_date: Optional[str]
    budget_range: Optional[str]
    contact_preference: str
    contact_details: str
    status: str
    creator_response_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_names(cls, obj):
        biz_name = obj.business.name if obj.business else "Business"
        creator_name = (
            obj.creator.user.full_name
            if obj.creator and obj.creator.user
            else f"Creator #{obj.creator_id}"
        )
        return cls(
            id=obj.id,
            business_id=obj.business_id,
            business_name=biz_name,
            creator_id=obj.creator_id,
            creator_name=creator_name,
            sender_user_id=obj.sender_user_id,
            campaign_title=obj.campaign_title,
            campaign_description=obj.campaign_description,
            proposed_deliverables=obj.proposed_deliverables,
            start_date=obj.start_date,
            end_date=obj.end_date,
            budget_range=obj.budget_range,
            contact_preference=obj.contact_preference,
            contact_details=obj.contact_details,
            status=obj.status,
            creator_response_notes=obj.creator_response_notes,
            created_at=obj.created_at,
            updated_at=obj.updated_at or obj.created_at,
        )
