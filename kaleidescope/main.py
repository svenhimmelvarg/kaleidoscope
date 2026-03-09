from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from contextlib import asynccontextmanager
from kaleidescope.config import load_config
from kaleidescope.utils.logging import setup_logging
from kaleidescope.api import workflow, notifications, download, publish
import logging
from pathlib import Path
import os

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Kaleidescope backend starting up")
    yield
    logger.info("Kaleidescope backend shutting down")


def create_app() -> FastAPI:
    config = load_config()

    app = FastAPI(lifespan=lifespan)

    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        config.host if config.host else "*",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(workflow.router)
    app.include_router(notifications.router)
    app.include_router(download.router)
    app.include_router(publish.router)

    # Static files setup
    STATIC_DIR = Path(__file__).parent / "static"

    # Mount assets if they exist
    if (STATIC_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    # Mount local thumbnails specifically (takes precedence over ComfyUI images)
    local_thumbnails = STATIC_DIR / "images" / "thumbnails"
    if local_thumbnails.exists():
        app.mount("/images/thumbnails", StaticFiles(directory=local_thumbnails), name="thumbnails")
        logger.info(f"Serving local thumbnails from {local_thumbnails}")

    # Mount images from ComfyUI output parent directory
    # The UI expects /images to map to the parent of the instance (e.g., /mnt/sdc1/apps/)
    # so that /images/comfyui.bleedingedge/output/... resolves correctly.
    if config.comfyui_instance_base_path:
        images_dir = Path(config.comfyui_instance_base_path).parent
        if images_dir.exists():
            app.mount("/images", StaticFiles(directory=images_dir), name="images")
            logger.info(f"Serving images from {images_dir}")
        else:
            logger.warning(f"Parent of ComfyUI instance path {images_dir} does not exist")

    # SPA handling
    INDEX_HTML_PATH = STATIC_DIR / "index.html"

    def inject_env_config(html_content: str) -> str:
        """Inject environment variables as window.ENV in index.html"""
        config_script = f"""<script>
    window.ENV = {{
        "VITE_CONVEX_URL": "{config.convex_url}",
        "VITE_MEILISEARCH_HOST": "{config.meilisearch_host}"
    }};
</script>"""

        # Inject before closing </head> tag
        if "</head>" in html_content:
            return html_content.replace("</head>", f"{config_script}</head>")
        # Fallback: inject after <html> tag
        elif "<html" in html_content:
            return html_content.replace("<html", f"<html>{config_script}")
        else:
            return config_script + html_content

    @app.get("/")
    async def serve_index():
        """Serve index.html with injected environment variables"""
        if INDEX_HTML_PATH.exists():
            with open(INDEX_HTML_PATH, "r") as f:
                html_content = f.read()
            return HTMLResponse(content=inject_env_config(html_content))
        return {"error": "index.html not found"}

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve index.html for all non-API routes (SPA fallback)"""
        # Skip API routes (those already handled by routers or mounts)
        # Note: API routes are matched first by FastAPI, so we only need to catch
        # what fell through. However, mounts are also matched early.
        # This handler catches everything else.

        # Explicitly skip known API prefixes just in case
        if full_path.startswith(("api/", "docs", "openapi.json")):
            return {"detail": "Not found"}

        # Check if file exists in static directory (e.g. favicon.ico)
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        # Serve index.html for SPA routes
        if INDEX_HTML_PATH.exists():
            with open(INDEX_HTML_PATH, "r") as f:
                html_content = f.read()
            return HTMLResponse(content=inject_env_config(html_content))

        return {"error": "index.html not found"}

    return app


app = create_app()
