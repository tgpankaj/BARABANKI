from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.core.ad_validator import sanitize_text, validate_destination_url, check_prohibited_content


class AdCampaignBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=150, description="Campaign descriptive name")
    objective: str = Field("brand_awareness", description="Campaign objective: brand_awareness, store_visit, lead_generation, website_traffic")
    headline: str = Field(..., min_length=3, max_length=100, description="Ad prominent headline")
    description: str = Field(..., min_length=10, max_length=1000, description="Ad body copy")
    image_url: Optional[str] = Field(None, max_length=500, description="Banner image URL")
    destination_url: Optional[str] = Field(None, max_length=500, description="Target URL or local route")
    contact_action: str = Field("visit_website", description="visit_website, call_now, whatsapp, view_listing")
    contact_value: Optional[str] = Field(None, max_length=100, description="Phone number or relative path")
    placement: str = Field("homepage_sponsored", description="homepage_sponsored, directory_featured, category_banner, community_sponsored")
    target_locality: str = Field("All Localities", max_length=100)
    target_category: str = Field("All Categories", max_length=80)
    pricing_plan: str = Field("starter_7days", description="starter_7days, growth_15days, premium_30days, custom_daily")

    @field_validator("headline", "description")
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        clean = sanitize_text(v)
        is_prohibited, reason = check_prohibited_content(clean)
        if is_prohibited:
            raise ValueError(reason)
        return clean

    @field_validator("destination_url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        is_valid, err, cleaned = validate_destination_url(v)
        if not is_valid:
            raise ValueError(err)
        return cleaned


class AdCampaignCreate(AdCampaignBase):
    business_id: int
    start_date: datetime
    end_date: datetime
    custom_days: Optional[int] = Field(None, ge=1, le=180)


class AdCampaignUpdate(BaseModel):
    name: Optional[str] = None
    headline: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    destination_url: Optional[str] = None
    contact_action: Optional[str] = None
    contact_value: Optional[str] = None
    target_locality: Optional[str] = None
    target_category: Optional[str] = None


class AdCampaignOut(BaseModel):
    id: int
    business_id: int
    business_name: str
    business_slug: str
    user_id: int
    name: str
    objective: str
    headline: str
    description: str
    image_url: Optional[str] = None
    destination_url: Optional[str] = None
    contact_action: str
    contact_value: Optional[str] = None
    placement: str
    target_locality: str
    target_category: str
    start_date: datetime
    end_date: datetime
    pricing_plan: str
    budget_amount: float
    status: str
    review_feedback: Optional[str] = None
    is_paused: bool
    payment_status: str
    impression_count: int
    click_count: int
    ctr: float
    is_eligible: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_extras(cls, campaign) -> "AdCampaignOut":
        biz = campaign.business
        return cls(
            id=campaign.id,
            business_id=campaign.business_id,
            business_name=biz.name if biz else "Business Listing",
            business_slug=biz.slug if biz else "",
            user_id=campaign.user_id,
            name=campaign.name,
            objective=campaign.objective,
            headline=campaign.headline,
            description=campaign.description,
            image_url=campaign.image_url,
            destination_url=campaign.destination_url,
            contact_action=campaign.contact_action,
            contact_value=campaign.contact_value,
            placement=campaign.placement,
            target_locality=campaign.target_locality,
            target_category=campaign.target_category,
            start_date=campaign.start_date,
            end_date=campaign.end_date,
            pricing_plan=campaign.pricing_plan,
            budget_amount=campaign.budget_amount,
            status=campaign.status,
            review_feedback=campaign.review_feedback,
            is_paused=campaign.is_paused,
            payment_status=campaign.payment_status,
            impression_count=campaign.impression_count,
            click_count=campaign.click_count,
            ctr=campaign.ctr,
            is_eligible=campaign.is_eligible_for_display(),
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
        )


class AdPaymentCreate(BaseModel):
    transaction_reference: str = Field(..., min_length=4, max_length=120, description="UTR or Bank Reference number")
    amount: float = Field(..., gt=0)
    payment_method: str = Field("upi_qr", description="upi_qr, bank_transfer, offline_cash")
    idempotency_key: Optional[str] = Field(None, max_length=120)
    notes: Optional[str] = Field(None, max_length=500)


class AdPaymentOut(BaseModel):
    id: int
    campaign_id: int
    business_id: int
    user_id: int
    amount: float
    currency: str
    payment_method: str
    gateway_provider: str
    transaction_reference: str
    status: str
    payment_proof_url: Optional[str] = None
    verified_by_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    admin_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdReviewUpdate(BaseModel):
    status: str = Field(..., description="approved, rejected, active, paused")
    review_feedback: Optional[str] = Field(None, max_length=1000)


class AdReportCreate(BaseModel):
    reason: str = Field(..., description="misleading, inappropriate, fraud, counterfeit, other")
    details: str = Field(..., min_length=10, max_length=1000)
    reporter_email: Optional[str] = Field(None, max_length=100)


class AdReportOut(BaseModel):
    id: int
    campaign_id: int
    reported_by_id: Optional[int] = None
    reason: str
    details: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
