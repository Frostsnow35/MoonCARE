from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, field_validator


class AndroidReleaseManifest(BaseModel):
    """Internal release manifest stored on the server."""

    platform: str
    channel: str
    version_code: int
    version_name: str
    min_supported_version_code: int
    force_update: bool = False
    apk_file_name: str
    sha256: str
    size_bytes: int
    published_at: datetime
    release_notes: List[str] = []

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized != "android":
            raise ValueError("platform must be android")
        return normalized

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"beta", "stable"}:
            raise ValueError("channel must be beta or stable")
        return normalized

    @field_validator("version_code", "min_supported_version_code")
    @classmethod
    def validate_positive_version_code(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("version code must be positive")
        return value

    @field_validator("version_name")
    @classmethod
    def validate_semver(cls, value: str) -> str:
        parts = value.split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise ValueError("version_name must use major.minor.patch")
        return value

    @field_validator("apk_file_name")
    @classmethod
    def validate_apk_file_name(cls, value: str) -> str:
        name = Path(value).name
        if not name.endswith(".apk"):
            raise ValueError("apk_file_name must end with .apk")
        if name != value:
            raise ValueError("apk_file_name must not contain directories")
        return name

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
            raise ValueError("sha256 must be 64 hex characters")
        return normalized

    @field_validator("size_bytes")
    @classmethod
    def validate_size(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("size_bytes must be positive")
        return value

    @field_validator("release_notes")
    @classmethod
    def validate_release_notes(cls, value: List[str]) -> List[str]:
        notes = [note.strip() for note in value if note and note.strip()]
        if not notes:
            raise ValueError("release_notes must contain at least one note")
        return notes


class AndroidReleaseResponse(BaseModel):
    """Public response sent to the mobile client."""

    platform: str
    channel: str
    version_code: int
    version_name: str
    min_supported_version_code: int
    force_update: bool
    apk_url: str
    sha256: str
    size_bytes: int
    published_at: datetime
    release_notes: List[str]

    @field_validator("apk_url")
    @classmethod
    def validate_apk_url(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("apk_url must use https")
        return value
