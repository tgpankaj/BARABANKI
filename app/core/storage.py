"""
Barabanki Connect — Persistent Storage & Media Upload Validation Engine
Addresses Render's ephemeral filesystem limitations by providing:
1. Strict upload validation (MIME types, extensions, size limits, path-traversal prevention).
2. Safe UUID-based object key generation.
3. Pluggable backend architectures (URL reference mode, S3/Cloudflare R2, Cloudinary).
4. Ephemeral storage risk mitigation and migration utilities.
"""

import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

from app.core.config import settings

# ------------------------------------------------------------------------------
# Upload Validation Constraints
# ------------------------------------------------------------------------------
ALLOWED_MIME_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/webp": [".webp"],
    "image/svg+xml": [".svg"],
    "image/gif": [".gif"],
}

ALLOWED_EXTENSIONS = {ext for exts in ALLOWED_MIME_TYPES.values() for ext in exts}
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def sanitize_filename(filename: str) -> str:
    """
    Generate an unguessable, collision-free UUID filename preserving only the valid extension.
    Completely eliminates directory traversal (../), null byte injection, and special characters.
    """
    clean_name = os.path.basename(filename).strip()
    _, ext = os.path.splitext(clean_name)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".jpg"
    return f"{uuid.uuid4().hex}{ext}"


def validate_upload_metadata(
    filename: str,
    content_type: Optional[str] = None,
    size_bytes: Optional[int] = None,
    max_size: int = MAX_UPLOAD_SIZE_BYTES,
) -> Tuple[bool, str]:
    """
    Validate incoming file metadata against strict security criteria before processing.
    """
    if not filename or not filename.strip():
        return False, "File name cannot be empty."

    # Prevent directory traversal in filename
    if ".." in filename or "/" in filename or "\\" in filename:
        return False, "Invalid file name: directory traversal detected."

    _, ext = os.path.splitext(filename.strip().lower())
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}."

    if content_type:
        clean_content_type = content_type.split(";")[0].strip().lower()
        if clean_content_type not in ALLOWED_MIME_TYPES:
            return False, f"Unsupported MIME type '{clean_content_type}'. Allowed types: {', '.join(ALLOWED_MIME_TYPES.keys())}."
        if ext not in ALLOWED_MIME_TYPES[clean_content_type]:
            return False, f"Extension '{ext}' does not match reported MIME type '{clean_content_type}'."

    if size_bytes is not None:
        if size_bytes <= 0:
            return False, "File is empty (0 bytes)."
        if size_bytes > max_size:
            max_mb = max_size / (1024 * 1024)
            return False, f"File size exceeds the {max_mb:.1f} MB upload limit."

    return True, ""


def validate_hosted_image_url(url: Optional[str]) -> Tuple[bool, str, Optional[str]]:
    """
    Validate an image URL reference (e.g. Unsplash, Cloudinary, AWS S3, or relative /static/... path).
    Ensures safe schemes and prevents open redirects or malicious schemas.
    """
    if not url or not url.strip():
        return True, "", None

    cleaned = url.strip()

    # Relative internal static paths are safe
    if cleaned.startswith("/static/"):
        return True, "", cleaned

    # Prevent dangerous schemes
    lower = cleaned.lower()
    if lower.startswith(("javascript:", "data:", "vbscript:", "file:")):
        return False, "Unsafe URL scheme detected.", None

    if lower.startswith("//"):
        return False, "Protocol-relative URLs are not permitted.", None

    try:
        parsed = urlparse(cleaned)
    except Exception:
        return False, "Malformed image URL format.", None

    if parsed.scheme not in ("http", "https"):
        return False, "Image URLs must use HTTP or HTTPS protocols.", None

    if not parsed.netloc:
        return False, "Image URL missing valid domain.", None

    return True, "", cleaned


# ------------------------------------------------------------------------------
# Storage Provider Abstraction
# ------------------------------------------------------------------------------
class StorageService:
    """
    Unified storage service managing media assets for Barabanki Connect.
    Defaults to URL reference mode (zero ephemeral storage risk), with seamless
    extensibility to S3/Cloudflare R2 or Cloudinary via environment configuration.
    """

    def __init__(self):
        self.backend = settings.STORAGE_BACKEND.lower()
        self.bucket = settings.STORAGE_BUCKET
        self.endpoint_url = settings.STORAGE_ENDPOINT_URL
        self.public_base_url = settings.STORAGE_PUBLIC_BASE_URL.rstrip("/")

    def get_backend_info(self) -> dict:
        return {
            "backend": self.backend,
            "configured": bool(self.bucket or self.public_base_url or self.backend == "url"),
            "storage_persistence": "permanent" if self.backend in ("s3", "cloudinary", "url") else "ephemeral",
            "ephemeral_disk_used": False,
        }

    def resolve_media_url(self, file_key_or_url: str) -> str:
        """Resolve a stored key or reference to a public HTTP/HTTPS URL."""
        if not file_key_or_url:
            return ""

        # Already an absolute or root-relative URL
        if file_key_or_url.startswith(("http://", "https://", "/")):
            return file_key_or_url

        if self.public_base_url:
            return f"{self.public_base_url}/{file_key_or_url}"

        return f"/static/images/{file_key_or_url}"


storage_service = StorageService()
