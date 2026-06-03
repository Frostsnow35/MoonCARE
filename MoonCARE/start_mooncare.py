#!/usr/bin/env python3
"""Start the MoonCARE local development services.

This script is intentionally small and conservative: it starts the existing
FastAPI backend and Vite frontend, checks that required dependencies are
present, and keeps logs in the repository root for troubleshooting.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
LOG_DIR = ROOT_DIR / "logs"


def _cmd(name: str) -> str:
    resolved = shutil.which(name)
    if not resolved:
        raise RuntimeError(f"Missing command: {name}")
    return resolved


def _python() -> str:
    return sys.executable


def _check_file(path: Path, message: str) -> None:
    if not path.exists():
        raise RuntimeError(f"{message}: {path}")


def _run_check(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or f"Command failed: {' '.join(command)}")


def check_environment() -> None:
    """Verify that the local machine can start the app."""
    print("[check] Verifying local tools and dependencies...")
    _check_file(BACKEND_DIR / "app" / "main.py", "Backend entrypoint not found")
    _check_file(FRONTEND_DIR / "package.json", "Frontend package.json not found")
    _cmd("node")
    _cmd("npm")

    if sys.version_info < (3, 10):
        version = ".".join(map(str, sys.version_info[:3]))
        raise RuntimeError(f"Python 3.10+ is required, current version is {version}")

    if not (ROOT_DIR / "node_modules").exists():
        raise RuntimeError("Root dependencies are missing. Run: npm run setup")
    if not (FRONTEND_DIR / "node_modules").exists():
        raise RuntimeError("Frontend dependencies are missing. Run: npm run setup")

    _run_check([_python(), "-c", "import fastapi, uvicorn, sqlalchemy"], ROOT_DIR)


def ensure_local_env_files() -> None:
    """Create local .env files from examples when they do not exist."""
    copies = [
        (ROOT_DIR / ".env.example", ROOT_DIR / ".env"),
        (BACKEND_DIR / ".env.example", BACKEND_DIR / ".env"),
        (FRONTEND_DIR / ".env.example", FRONTEND_DIR / ".env"),
    ]
    for source, target in copies:
        if source.exists() and not target.exists():
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"[env] Created {target.relative_to(ROOT_DIR)} from example")


def start_process(name: str, command: list[str], cwd: Path, log_file: Path) -> subprocess.Popen[str]:
    """Start a service and stream its output to a log file."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handle = log_file.open("w", encoding="utf-8")
    print(f"[start] {name}: {' '.join(command)}")
    print(f"        log: {log_file.relative_to(ROOT_DIR)}")
    return subprocess.Popen(
        command,
        cwd=cwd,
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )


def stop_processes(processes: list[tuple[str, subprocess.Popen[str]]]) -> None:
    """Stop any still-running child processes."""
    for _, process in processes:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
    time.sleep(1)
    for _, process in processes:
        if process.poll() is None:
            process.kill()


def wait_for_exit(processes: list[tuple[str, subprocess.Popen[str]]]) -> int:
    """Keep the script alive and stop all services on exit."""
    try:
        while True:
            for name, process in processes:
                code = process.poll()
                if code is not None:
                    print(f"[exit] {name} stopped with code {code}")
                    stop_processes(processes)
                    return code
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[stop] Stopping MoonCARE services...")
        stop_processes(processes)
        return 0


def main() -> int:
    print("MoonCARE local development launcher")
    print("===================================")
    try:
        ensure_local_env_files()
        check_environment()

        backend = start_process(
            "backend",
            [
                _python(),
                "-m",
                "uvicorn",
                "app.main:app",
                "--app-dir",
                "backend",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            ROOT_DIR,
            LOG_DIR / "backend-dev.log",
        )
        frontend = start_process(
            "frontend",
            [_cmd("npm"), "run", "dev", "--", "--host", "127.0.0.1", "--port", "3000"],
            FRONTEND_DIR,
            LOG_DIR / "frontend-dev.log",
        )

        print("\nReady:")
        print("  Frontend: http://localhost:3000")
        print("  Backend:  http://localhost:8000")
        print("  API docs: http://localhost:8000/docs")
        print("Press Ctrl+C to stop.")
        return wait_for_exit([("backend", backend), ("frontend", frontend)])
    except RuntimeError as exc:
        print(f"\n[error] {exc}")
        print("Run `npm run setup` first, then retry `npm run dev`.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
