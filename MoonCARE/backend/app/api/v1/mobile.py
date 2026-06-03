import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app.config import settings
from app.schemas.mobile import AndroidReleaseManifest, AndroidReleaseResponse


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mobile", tags=["移动发布"])


def _mobile_releases_dir() -> Path:
    configured = os.getenv("MOBILE_RELEASES_DIR") or settings.MOBILE_RELEASES_DIR
    return Path(configured)


def _mobile_releases_public_base_url(request: Request) -> str:
    configured = os.getenv("MOBILE_RELEASES_PUBLIC_BASE_URL") or settings.MOBILE_RELEASES_PUBLIC_BASE_URL
    base_url = (configured or str(request.base_url)).rstrip("/")
    if not base_url.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mobile release download base URL must use HTTPS.",
        )
    return base_url


def _release_manifest_path(platform: str, channel: str) -> Path:
    return _mobile_releases_dir() / f"{platform}-{channel}.json"


def _load_android_release_manifest(channel: str) -> AndroidReleaseManifest:
    manifest_path = _release_manifest_path("android", channel)
    if not manifest_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Android release metadata for channel '{channel}' not found.",
        )

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = AndroidReleaseManifest.model_validate(payload)
    except ValidationError as exc:
        logger.warning("Invalid android release manifest %s: %s", manifest_path, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Android release metadata is invalid.",
        ) from exc
    except json.JSONDecodeError as exc:
        logger.warning("Unreadable android release manifest %s: %s", manifest_path, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Android release metadata is unreadable.",
        ) from exc

    apk_path = _mobile_releases_dir() / manifest.apk_file_name
    if not apk_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Android release package '{manifest.apk_file_name}' is missing.",
        )

    return manifest


def _build_android_release_response(
    request: Request,
    channel: str,
    manifest: AndroidReleaseManifest,
) -> AndroidReleaseResponse:
    base_url = _mobile_releases_public_base_url(request)
    apk_url = f"{base_url}{settings.API_V1_PREFIX}/mobile/releases/android/{channel}/download"
    return AndroidReleaseResponse(
        platform=manifest.platform,
        channel=manifest.channel,
        version_code=manifest.version_code,
        version_name=manifest.version_name,
        min_supported_version_code=manifest.min_supported_version_code,
        force_update=manifest.force_update,
        apk_url=apk_url,
        sha256=manifest.sha256,
        size_bytes=manifest.size_bytes,
        published_at=manifest.published_at,
        release_notes=manifest.release_notes,
    )


@router.get("/releases/android/{channel}")
async def get_android_release(channel: str, request: Request):
    """Return the latest Android release metadata for the requested channel."""

    manifest = _load_android_release_manifest(channel)
    payload = _build_android_release_response(request, channel, manifest)
    return {"code": 200, "data": payload.model_dump(mode="json"), "message": "ok"}


@router.get("/releases/android/{channel}/download")
async def download_android_release(channel: str):
    """Serve the current Android APK for the requested channel."""

    manifest = _load_android_release_manifest(channel)
    apk_path = _mobile_releases_dir() / manifest.apk_file_name
    return FileResponse(
        apk_path,
        media_type="application/vnd.android.package-archive",
        filename=manifest.apk_file_name,
    )
