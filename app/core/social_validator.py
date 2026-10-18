"""
Barabanki Connect — Social Profile URL & Domain Allowlist Validator
Enforces strict domain allowlists and URL schemes to prevent phishing, SSRF, and open-redirect vectors.
Never collects or stores social media credentials.
"""

import re
from urllib.parse import urlparse
from typing import Optional, Dict, Tuple, List

PLATFORM_DOMAINS: Dict[str, List[str]] = {
    "instagram": ["instagram.com", "www.instagram.com"],
    "youtube": ["youtube.com", "www.youtube.com", "youtu.be"],
    "facebook": ["facebook.com", "www.facebook.com", "fb.com", "www.fb.com"],
    "linkedin": ["linkedin.com", "www.linkedin.com"],
    "twitter_x": ["x.com", "www.x.com", "twitter.com", "www.twitter.com"],
    "github": ["github.com", "www.github.com"],
}

ALLOWED_DOMAINS = PLATFORM_DOMAINS

PLATFORM_CANONICAL_DOMAINS: Dict[str, str] = {
    "instagram": "www.instagram.com",
    "youtube": "www.youtube.com",
    "facebook": "www.facebook.com",
    "linkedin": "www.linkedin.com",
    "twitter_x": "x.com",
    "github": "github.com",
}

PLATFORM_CANONICAL_PREFIXES: Dict[str, str] = {
    "instagram": "https://www.instagram.com/",
    "youtube": "https://www.youtube.com/@",
    "facebook": "https://www.facebook.com/",
    "linkedin": "https://www.linkedin.com/in/",
    "twitter_x": "https://x.com/",
    "github": "https://github.com/",
}


def sanitize_handle(handle: str) -> str:
    """Strip leading @ and extraneous whitespace."""
    return handle.strip().lstrip("@")


def validate_social_url(platform: str, value: Optional[str]) -> Optional[str]:
    """
    Validates a social profile URL or username against an allowed domain list.
    Returns the sanitized, canonical https:// URL, or None if input is empty.
    Raises ValueError with a clear explanation if domain or format is disallowed.
    """
    if not value or not str(value).strip():
        return None

    val = str(value).strip()

    # Reject dangerous URI schemes immediately
    lower_val = val.lower()
    if lower_val.startswith(("javascript:", "data:", "vbscript:", "file:")):
        raise ValueError("Invalid URL scheme. Only HTTP and HTTPS are permitted.")

    if platform not in PLATFORM_DOMAINS:
        if platform == "portfolio":
            return validate_portfolio_url(val)
        raise ValueError(f"Unsupported social platform: {platform}")

    # Case 1: Plain handle (e.g. '@rohitvlogs' or 'rohitvlogs')
    # If there is no protocol and no slash/dot, treat as a handle
    if not (val.startswith("http://") or val.startswith("https://") or "/" in val):
        clean_handle = sanitize_handle(val)
        if not re.match(r"^[A-Za-z0-9_.-]{1,50}$", clean_handle):
            raise ValueError(f"Invalid username format for {platform}.")
        return f"{PLATFORM_CANONICAL_PREFIXES[platform]}{clean_handle}"

    # Case 2: Full or partial URL
    if not (val.startswith("http://") or val.startswith("https://")):
        val = f"https://{val}"

    parsed = urlparse(val)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only secure HTTP/HTTPS URLs are allowed.")

    hostname = (parsed.hostname or "").lower()
    allowed_domains = PLATFORM_DOMAINS[platform]

    if hostname not in allowed_domains:
        allowed_str = ", ".join(allowed_domains)
        raise ValueError(
            f"Must be a legitimate {platform} domain ({allowed_str}). Provided '{hostname}' is not permitted."
        )

    # Return normalized https URL with canonical domain
    canonical_domain = PLATFORM_CANONICAL_DOMAINS.get(platform, hostname)
    normalized_path = parsed.path
    if not normalized_path.startswith("/"):
        normalized_path = "/" + normalized_path

    # Construct canonical URL
    canon = f"https://{canonical_domain}{normalized_path.rstrip('/')}"
    if parsed.query:
        canon += f"?{parsed.query}"
    return canon


def validate_portfolio_url(url: Optional[str]) -> Optional[str]:
    """Validates general portfolio / personal website links."""
    if not url or not str(url).strip():
        return None

    val = str(url).strip()
    lower_val = val.lower()
    if lower_val.startswith(("javascript:", "data:", "vbscript:", "file:")):
        raise ValueError("Invalid URL scheme. Only HTTP and HTTPS are permitted.")

    if not (val.startswith("http://") or val.startswith("https://")):
        val = f"https://{val}"

    parsed = urlparse(val)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP/HTTPS URLs are permitted.")

    hostname = (parsed.hostname or "").lower()
    if not hostname or "." not in hostname:
        raise ValueError("Portfolio URL must include a valid domain name.")

    return val


def clean_social_url(platform: str, value: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Safe wrapper returning (validated_url, error_string)."""
    try:
        url = validate_social_url(platform, value)
        return url, None
    except ValueError as e:
        return None, str(e)


def clean_portfolio_url(value: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Safe wrapper returning (validated_url, error_string)."""
    try:
        url = validate_portfolio_url(value)
        return url, None
    except ValueError as e:
        return None, str(e)


validate_social_link = clean_social_url


def clean_social_payload(social_map: dict) -> Tuple[dict, List[str]]:
    """Clean a map of social platform -> url inputs, returning validated map and list of errors."""
    cleaned = {}
    errors = []
    for platform, raw_val in social_map.items():
        if platform == "portfolio_url":
            val, err = clean_portfolio_url(raw_val)
        else:
            val, err = clean_social_url(platform, raw_val)
        if err:
            errors.append(f"{platform.capitalize()}: {err}")
        else:
            cleaned[platform] = val
    return cleaned, errors
