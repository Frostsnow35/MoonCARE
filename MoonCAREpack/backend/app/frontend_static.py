from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def register_frontend_static(app: FastAPI, dist_dir: Path) -> None:
    """Serve the built Vue frontend when a production dist directory exists."""
    dist_path = Path(dist_dir)
    index_path = dist_path / "index.html"
    assets_path = dist_path / "assets"

    if not index_path.exists():
        return

    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend_app(full_path: str):
        """Return the Vue app shell for client-side routes."""
        return FileResponse(index_path)
