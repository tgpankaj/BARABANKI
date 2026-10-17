from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserProfileUpdate,
    UserPasswordChange,
    UserOut,
    TokenResponse,
)
from app.schemas.news import (
    NewsArticleBase,
    NewsArticleCreate,
    NewsArticleUpdate,
    NewsArticleOut,
)
from app.schemas.event import EventBase, EventCreate, EventOut
from app.schemas.business import BusinessBase, BusinessCreate, BusinessOut
from app.schemas.job import JobListingBase, JobListingCreate, JobListingOut
from app.schemas.education import EducationInstituteBase, EducationInstituteCreate, EducationInstituteOut
from app.schemas.community import (
    CommentBase,
    CommentCreate,
    CommentOut,
    CommunityPostBase,
    CommunityPostCreate,
    CommunityPostOut,
    ReportCreate,
)
from app.schemas.contact import ContactMessageCreate, ContactMessageOut
from app.schemas.tourism import TourismSpotBase, TourismSpotCreate, TourismSpotOut

__all__ = [
    "UserRegister",
    "UserLogin",
    "UserProfileUpdate",
    "UserPasswordChange",
    "UserOut",
    "TokenResponse",
    "NewsArticleBase",
    "NewsArticleCreate",
    "NewsArticleUpdate",
    "NewsArticleOut",
    "EventBase",
    "EventCreate",
    "EventOut",
    "BusinessBase",
    "BusinessCreate",
    "BusinessOut",
    "JobListingBase",
    "JobListingCreate",
    "JobListingOut",
    "EducationInstituteBase",
    "EducationInstituteCreate",
    "EducationInstituteOut",
    "CommentBase",
    "CommentCreate",
    "CommentOut",
    "CommunityPostBase",
    "CommunityPostCreate",
    "CommunityPostOut",
    "ReportCreate",
    "ContactMessageCreate",
    "ContactMessageOut",
    "TourismSpotBase",
    "TourismSpotCreate",
    "TourismSpotOut",
]
