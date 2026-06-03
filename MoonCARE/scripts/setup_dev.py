#!/usr/bin/env python3
"""Prepare a local MoonCARE development checkout."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"


def command_exists(command: str) -> bool:
    """Return whether a command is available on PATH."""
    return shutil.which(command) is not None


def run(command: list[str], cwd: Path) -> None:
    """Run a setup command and raise a readable error on failure."""
    print(f"[run] {cwd.relative_to(ROOT_DIR) if cwd != ROOT_DIR else '.'}> {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def copy_env(source: Path, target: Path) -> None:
    """Create a local env file from its example when missing."""
    if source.exists() and not target.exists():
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[env] Created {target.relative_to(ROOT_DIR)}")


def main() -> int:
    if sys.version_info < (3, 10):
        version = ".".join(map(str, sys.version_info[:3]))
        print(f"[error] Python 3.10+ is required, current version is {version}")
        return 1
    if not command_exists("node") or not command_exists("npm"):
        print("[error] Node.js 20+ with npm is required: https://nodejs.org/")
        return 1

    copy_env(ROOT_DIR / ".env.example", ROOT_DIR / ".env")
    copy_env(BACKEND_DIR / ".env.example", BACKEND_DIR / ".env")
    copy_env(FRONTEND_DIR / ".env.example", FRONTEND_DIR / ".env")

    run([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"], ROOT_DIR)
    run(["npm", "install"], ROOT_DIR)
    run(["npm", "install"], FRONTEND_DIR)

    print("\nSetup complete.")
    print("Start the app with: npm run dev")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
