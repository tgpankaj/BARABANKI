from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base, utc_now

AD_OBJECTIVES = {
    "brand_awareness": "Build brand recognition across District Barabanki",
    "store_visit": "Drive local foot traffic to retail store, workshop or clinic",
    "lead_generation": "Collect inquiries, customer phone calls or WhatsApp messages",
    "website_traffic": "Direct visitors to official website, catalog or portfolio",
}

AD_PLACEMENTS = {
    "homepage_sponsored": "Homepage Sponsored Spotlight (High visibility on portal home page)",
    "directory_featured": "Business Directory Featured Listing (Pinned priority slot in directory)",
    "category_banner": "Category Page Promotion (Targeted banner on specific category pages)",
    "community_sponsored": "Community Sponsored Update (Tasteful sponsored card in community feed)",
}

PRICING_PLANS = {
    "starter_7days": {
        "name": "Local Starter",
        "duration_days": 7,
        "price_inr": 499.0,
        "description": "7 days targeted placement in business directory or category pages",
        "recommended_for": "Local artisans, weavers, home kitchens, and small service providers",
    },
    "growth_15days": {
        "name": "Business Growth",
        "duration_days": 15,
        "price_inr": 999.0,
        "description": "15 days dual placement in directory & category with prominent sponsored badge",
        "recommended_for": "Clinics, coaching institutes, automobile showrooms, wedding halls",
    },
    "premium_30days": {
        "name": "Festival & Market Leader",
        "duration_days": 30,
        "price_inr": 1799.0,
        "description": "30 days priority homepage sponsored slot + directory pin + category spotlight",
        "recommended_for": "Leading hospitals, colleges, major brands, and festival season campaigns",
    },
    "custom_daily": {
        "name": "Flexible Daily Rate",
        "duration_days": 1,
        "price_inr": 99.0,
        "description": "Daily flexible tier at ₹99/day for custom short-term announcements",
        "recommended_for": "Weekend flash sales, one-day clearance events, workshop alerts",
    },
}

CAMPAIGN_STATUSES = [
    "draft",
    "pending_review",
    "approved",
    "rejected",
    "active",
    "paused",
    "completed",
    "expired",
]

PAYMENT_STATUSES = [
    "pending",
    "proof_submitted",
    "verified",
    "failed",
    "refunded",
    "waived",
]


class AdCampaign(Base):
    __tablename__ = "ad_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Campaign Metadata
    name = Column(String(150), nullable=False)
    objective = Column(String(50), default="brand_awareness", nullable=False)

    # Ad Creative
    headline = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=True)
    destination_url = Column(String(500), nullable=True)
    contact_action = Column(String(50), default="visit_website", nullable=False)  # visit_website, call_now, whatsapp, view_listing
    contact_value = Column(String(100), nullable=True)  # phone number, URL, or business slug

    # Placement & Targeting
    placement = Column(String(50), default="homepage_sponsored", index=True, nullable=False)
    target_locality = Column(String(100), default="All Localities", nullable=False)
    target_category = Column(String(80), default="All Categories", nullable=False)

    # Schedule & Budget
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    pricing_plan = Column(String(50), default="starter_7days", nullable=False)
    budget_amount = Column(Float, nullable=False)

    # Review & Lifecycle
    status = Column(String(30), default="pending_review", index=True, nullable=False)
    review_feedback = Column(Text, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    is_paused = Column(Boolean, default=False, nullable=False)

    # Payment State
    payment_status = Column(String(30), default="pending", index=True, nullable=False)

    # Genuine Internal Analytics (Zero Fake Figures)
    impression_count = Column(Integer, default=0, nullable=False)
    click_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    business = relationship("Business", back_populates="campaigns")
    user = relationship("User", foreign_keys=[user_id], back_populates="ad_campaigns")
    reviewer = relationship("User", foreign_keys=[reviewed_by_id])
    payments = relationship("AdPayment", back_populates="campaign", cascade="all, delete-orphan", order_by="AdPayment.created_at.desc()")
    impressions = relationship("AdImpression", back_populates="campaign", cascade="all, delete-orphan")
    clicks = relationship("AdClick", back_populates="campaign", cascade="all, delete-orphan")
    reports = relationship("AdReport", back_populates="campaign", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_ad_campaign_active_placement", "placement", "status", "payment_status", "is_paused"),
    )

    def is_eligible_for_display(self, now: datetime = None) -> bool:
        """
        Server-side eligibility check.
        Only approved campaigns with verified payment within active dates and unpaused status can be displayed.
        """
        current_time = now or utc_now()
        if self.is_paused:
            return False
        if self.status not in ("approved", "active"):
            return False
        if self.payment_status not in ("verified", "waived"):
            return False
        if not (self.start_date <= current_time <= self.end_date):
            return False
        if self.business and not self.business.is_approved:
            return False
        return True

    @property
    def ctr(self) -> float:
        """Calculate real Click-Through Rate (CTR%)."""
        if self.impression_count <= 0:
            return 0.0
        return round((self.click_count / self.impression_count) * 100.0, 2)

    def __repr__(self):
        return f"<AdCampaign {self.id}: {self.name} ({self.status})>"


class AdPayment(Base):
    __tablename__ = "ad_payments"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("ad_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    payment_method = Column(String(50), default="upi_qr", nullable=False)  # upi_qr, bank_transfer, offline_cash, gateway_stub
    gateway_provider = Column(String(50), default="manual_admin_verify", nullable=False)

    transaction_reference = Column(String(120), unique=True, index=True, nullable=False)  # e.g., Bank UTR or UPI Ref ID
    idempotency_key = Column(String(120), unique=True, index=True, nullable=True)

    status = Column(String(30), default="proof_submitted", index=True, nullable=False)  # pending, proof_submitted, verified, failed, refunded
    payment_proof_url = Column(String(500), nullable=True)

    verified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    admin_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    campaign = relationship("AdCampaign", back_populates="payments")
    business = relationship("Business")
    user = relationship("User", foreign_keys=[user_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])

    def __repr__(self):
        return f"<AdPayment {self.id}: {self.transaction_reference} - ₹{self.amount} ({self.status})>"


class AdImpression(Base):
    __tablename__ = "ad_impressions"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("ad_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    placement = Column(String(50), nullable=False)
    viewer_ip = Column(String(64), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True, nullable=False)

    # Relationships
    campaign = relationship("AdCampaign", back_populates="impressions")
    user = relationship("User")

    def __repr__(self):
        return f"<AdImpression campaign={self.campaign_id} placement={self.placement}>"


class AdClick(Base):
    __tablename__ = "ad_clicks"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("ad_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    placement = Column(String(50), nullable=False)
    destination_url = Column(String(500), nullable=False)
    viewer_ip = Column(String(64), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True, nullable=False)

    # Relationships
    campaign = relationship("AdCampaign", back_populates="clicks")
    user = relationship("User")

    def __repr__(self):
        return f"<AdClick campaign={self.campaign_id}>"


class AdReport(Base):
    __tablename__ = "ad_reports"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("ad_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    reported_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reporter_email = Column(String(100), nullable=True)
    reason = Column(String(80), nullable=False)  # misleading, inappropriate, fraud, counterfeit, other
    details = Column(Text, nullable=False)
    status = Column(String(30), default="pending", index=True, nullable=False)  # pending, reviewed_dismissed, action_taken_ad_paused
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    campaign = relationship("AdCampaign", back_populates="reports")
    reporter = relationship("User", foreign_keys=[reported_by_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by_id])

    def __repr__(self):
        return f"<AdReport campaign={self.campaign_id} reason={self.reason}>"
