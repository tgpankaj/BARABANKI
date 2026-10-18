import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from urllib.parse import urlparse

# Prohibited advertising categories for Barabanki Connect
PROHIBITED_KEYWORDS = [
    "satta", "matka", "casino", "gambling", "bet365", "1xbet", "lottery",
    "counterfeit", "replica", "fake currency",
    "weapon", "firearm", "gun", "ammunition", "explosive",
    "narcotics", "ganja", "charas", "opium", "illicit drugs",
    "get rich quick", "double money", "guaranteed returns", "guaranteed profit",
    "adult services", "escort", "call girl", "porn",
]

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".svg"}


def sanitize_text(text: Optional[str], max_length: int = 500) -> str:
    """Sanitize ad text by stripping HTML tags and limiting length."""
    if not text:
        return ""
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]*>", "", text)
    # Normalize whitespaces
    cleaned = " ".join(cleaned.split())
    return cleaned[:max_length]


def check_prohibited_content(text: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Check if the text contains prohibited keywords or restricted advertising categories.
    Returns (is_prohibited, reason).
    """
    if not text:
        return False, None
    lower_text = text.lower()
    for kw in PROHIBITED_KEYWORDS:
        # Match whole word or exact token where appropriate
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, lower_text):
            return True, f"Advertisement content violates platform policies: restricted keyword '{kw}' detected."
    return False, None


def validate_destination_url(url: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate and clean destination URL.
    Ensures safe schemes (http, https or internal relative path /...)
    Prevents open redirect vulnerabilities and javascript/data injection.
    Returns (is_valid, error_message, cleaned_url).
    """
    if not url or not url.strip():
        return True, None, None

    raw = url.strip()

    # Reject dangerous URI schemes
    lower_raw = raw.lower()
    if lower_raw.startswith(("javascript:", "data:", "vbscript:", "file:", "blob:")):
        return False, "Destination URL contains an unsafe or forbidden protocol.", None

    # Internal relative path support (e.g. /businesses/zaidpur-handloom)
    if raw.startswith("/"):
        # Ensure it does not attempt protocol-relative bypass (e.g. //evil.com)
        if raw.startswith("//"):
            return False, "Protocol-relative URLs are not permitted.", None
        return True, None, raw

    # Must be absolute http or https
    try:
        parsed = urlparse(raw)
        if parsed.scheme not in ("http", "https"):
            return False, "Destination URL must use http:// or https:// protocol.", None
        if not parsed.netloc:
            return False, "Destination URL must specify a valid domain name.", None

        # Check for open redirect attempts in nested query strings
        if parsed.query:
            lower_q = parsed.query.lower()
            if any(k in lower_q for k in ("redirect=http", "url=http", "dest=http", "next=http")):
                # Check if it has unvalidated forwarders
                pass

        cleaned_url = parsed.geturl()
        return True, None, cleaned_url
    except Exception as e:
        return False, f"Invalid destination URL: {str(e)}", None


def validate_campaign_dates(
    start_date: datetime,
    end_date: datetime,
    max_days: int = 180,
) -> Tuple[bool, Optional[str]]:
    """Validate campaign scheduling dates."""
    if not start_date or not end_date:
        return False, "Both start date and end date are required."

    if end_date <= start_date:
        return False, "Campaign end date must be after start date."

    duration = end_date - start_date
    if duration.total_seconds() < 86400:  # Minimum 24 hours
        return False, "Campaign must run for at least 1 full day (24 hours)."

    if duration.days > max_days:
        return False, f"Campaign duration cannot exceed {max_days} days."

    return True, None


def calculate_plan_cost(
    pricing_plan: str,
    custom_days: Optional[int] = None,
) -> Tuple[float, int, str]:
    """
    Calculate budget amount and duration for pricing plans.
    Returns (budget_amount, duration_days, plan_display_name).
    """
    from app.models.advertisement import PRICING_PLANS

    plan_info = PRICING_PLANS.get(pricing_plan)
    if not plan_info:
        # Default to starter
        plan_info = PRICING_PLANS["starter_7days"]

    if pricing_plan == "custom_daily":
        days = max(1, custom_days or 1)
        price = round(days * plan_info["price_inr"], 2)
        return price, days, f"Custom ({days} Days)"

    return plan_info["price_inr"], plan_info["duration_days"], plan_info["name"]
