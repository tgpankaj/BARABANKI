import time
from collections import defaultdict
from threading import Lock
from typing import Optional
from fastapi import Request, HTTPException, status
from app.core.config import settings

# Thread-safe sliding window in-memory rate limiter
_request_records = defaultdict(list)
_lock = Lock()


def get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For when behind a reverse proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First IP in list is client
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def check_rate_limit(
    request: Request,
    scope: str = "general",
    max_requests: Optional[int] = None,
    window_seconds: int = 60,
    raise_exception: bool = True,
) -> bool:
    """
    Check if the current request exceeds the rate limit for the given scope.
    Returns True if allowed, or False / raises HTTPException(429) if exceeded.
    """
    if not settings.RATE_LIMIT_ENABLED or settings.ENVIRONMENT == "test":
        return True

    ip = get_client_ip(request)
    now = time.time()
    cutoff = now - window_seconds
    bucket_key = f"{scope}:{ip}"

    limit = max_requests or (
        settings.RATE_LIMIT_AUTH_PER_MINUTE
        if "auth" in scope
        else settings.RATE_LIMIT_SUBMIT_PER_MINUTE
    )

    with _lock:
        # Purge timestamps outside current window
        valid_timestamps = [ts for ts in _request_records[bucket_key] if ts > cutoff]
        _request_records[bucket_key] = valid_timestamps

        if len(valid_timestamps) >= limit:
            if raise_exception:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests for {scope}. Please wait a moment before trying again.",
                    headers={"Retry-After": str(window_seconds)},
                )
            return False

        _request_records[bucket_key].append(now)
        return True


def clear_rate_limits():
    """Clear all rate limit records. Used in test suites."""
    with _lock:
        _request_records.clear()
