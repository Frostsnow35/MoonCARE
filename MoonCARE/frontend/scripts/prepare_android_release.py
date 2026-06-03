import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare a self-hosted MoonCARE Android release manifest.")
    parser.add_argument("--apk", required=True, help="Path to the signed APK file.")
    parser.add_argument("--channel", required=True, choices=["beta", "stable"], help="Update channel.")
    parser.add_argument("--flavor", required=True, choices=["internal", "public"], help="Android flavor.")
    parser.add_argument("--version-name", required=True, help="Semantic version name, e.g. 1.1.0.")
    parser.add_argument("--version-code", required=True, type=int, help="Monotonic Android versionCode.")
    parser.add_argument(
        "--min-supported-version-code",
        required=True,
        type=int,
        help="Lowest supported installed versionCode before forcing update.",
    )
    parser.add_argument("--base-url", required=True, help="HTTPS base URL serving the mobile release API.")
    parser.add_argument(
        "--release-dir",
        default=str(Path(__file__).resolve().parents[2] / "mobile_releases"),
        help="Directory where the canonical APK and android-{channel}.json will be written.",
    )
    parser.add_argument(
        "--release-note",
        action="append",
        dest="release_notes",
        required=True,
        help="Release note entry. Repeat this flag for multiple notes.",
    )
    parser.add_argument("--force-update", action="store_true", help="Mark the release as force update.")
    return parser.parse_args()


def validate_args(args):
    if not SEMVER_RE.match(args.version_name):
        raise SystemExit("--version-name must use major.minor.patch")
    if args.version_code <= 0:
        raise SystemExit("--version-code must be positive")
    if args.min_supported_version_code <= 0:
        raise SystemExit("--min-supported-version-code must be positive")
    if not args.base_url.startswith("https://"):
        raise SystemExit("--base-url must use HTTPS")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    args = parse_args()
    validate_args(args)

    apk_path = Path(args.apk).resolve()
    if not apk_path.is_file():
        raise SystemExit(f"APK not found: {apk_path}")

    release_dir = Path(args.release_dir).resolve()
    release_dir.mkdir(parents=True, exist_ok=True)

    canonical_apk_name = f"MoonCARE-{args.flavor}-{args.version_name}-{args.version_code}.apk"
    canonical_apk_path = release_dir / canonical_apk_name
    shutil.copy2(apk_path, canonical_apk_path)

    payload = {
        "platform": "android",
        "channel": args.channel,
        "version_code": args.version_code,
        "version_name": args.version_name,
        "min_supported_version_code": args.min_supported_version_code,
        "force_update": args.force_update,
        "apk_file_name": canonical_apk_name,
        "sha256": sha256(canonical_apk_path),
        "size_bytes": canonical_apk_path.stat().st_size,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "release_notes": args.release_notes,
    }

    manifest_path = release_dir / f"android-{args.channel}.json"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"APK: {canonical_apk_path}")
    print(f"Manifest: {manifest_path}")
    print("API metadata route:")
    print(f"{args.base_url.rstrip('/')}/api/v1/mobile/releases/android/{args.channel}")
    print("Download route:")
    print(f"{args.base_url.rstrip('/')}/api/v1/mobile/releases/android/{args.channel}/download")
    print("Manifest template file: android-{channel}.json")


if __name__ == "__main__":
    main()
