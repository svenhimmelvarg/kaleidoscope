from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from contextlib import asynccontextmanager
from kaleidescope.config import load_config
from kaleidescope.utils.logging import setup_logging
from kaleidescope.api import workflow, notifications, download, publish, embed
import logging
from pathlib import Path
import os

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Kaleidescope backend starting up")
    logger.info("Kaleidescope main module loaded from %s", __file__)
    logger.info("Process cwd: %s", os.getcwd())
    for key, value in getattr(app.state, "image_debug_info", {}).items():
        logger.info("Image config %s: %s", key, value)
    yield
    logger.info("Kaleidescope backend shutting down")


def create_app() -> FastAPI:
    config = load_config()

    app = FastAPI(lifespan=lifespan)
    app.state.image_debug_info = {
        "main_file": __file__,
        "cwd": os.getcwd(),
        "comfyui_output_path": config.comfyui_output_path,
        "release_folder": config.output_folder_filter,
        "comfyui_instance_base_path": config.comfyui_instance_base_path,
    }

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
    app.include_router(embed.router)

    # Static files setup
    STATIC_DIR = Path(__file__).parent / "static"

    # Mount assets if they exist
    if (STATIC_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    # Serve thumbnails dynamically from local and legacy directories
    local_thumbnails = STATIC_DIR / "images" / "thumbnails"
    legacy_thumbnails = (
        Path(__file__).parent.parent / "indexer.legacy" / "public" / "images" / "thumbnails"
    )

    @app.get("/images/thumbnails/{file_name:path}")
    async def serve_thumbnails(file_name: str):
        from fastapi import HTTPException

        # Check local thumbnails first
        if local_thumbnails.exists():
            local_path = local_thumbnails / file_name
            try:
                resolved_local = local_path.resolve()
                resolved_base = local_thumbnails.resolve()
                resolved_local.relative_to(resolved_base)
                if resolved_local.exists() and resolved_local.is_file():
                    return FileResponse(resolved_local)
            except ValueError:
                pass

        # Check legacy thumbnails
        if legacy_thumbnails.exists():
            legacy_path = legacy_thumbnails / file_name
            try:
                resolved_legacy = legacy_path.resolve()
                resolved_base = legacy_thumbnails.resolve()
                resolved_legacy.relative_to(resolved_base)
                if resolved_legacy.exists() and resolved_legacy.is_file():
                    return FileResponse(resolved_legacy)
            except ValueError:
                pass

        raise HTTPException(status_code=404, detail="Thumbnail not found")

    if config.comfyui_output_path:
        output_root = (Path(config.comfyui_output_path) / config.output_folder_filter).resolve()
        app.state.image_debug_info["output_root"] = str(output_root)

        @app.get("/images/file")
        async def serve_output_image(path: str):
            from fastapi import HTTPException

            requested_path = Path(path)
            if requested_path.is_absolute():
                full_path = requested_path.resolve()
            else:
                relative_path = path.lstrip("/")
                release_prefix = f"{config.output_folder_filter}/"
                output_release_prefix = f"output/{config.output_folder_filter}/"
                if relative_path.startswith(output_release_prefix):
                    relative_path = relative_path.removeprefix(output_release_prefix)
                elif relative_path.startswith(release_prefix):
                    relative_path = relative_path.removeprefix(release_prefix)
                full_path = (output_root / relative_path).resolve()

            try:
                full_path.relative_to(output_root)
            except ValueError:
                logger.warning(
                    "Output image denied: requested=%r resolved=%s root=%s",
                    path,
                    full_path,
                    output_root,
                )
                raise HTTPException(status_code=403, detail="Access denied")

            if full_path.exists() and full_path.is_file():
                logger.info(
                    "Serving output image: requested=%r resolved=%s root=%s",
                    path,
                    full_path,
                    output_root,
                )
                return FileResponse(full_path)

            logger.warning(
                "Output image not found: requested=%r resolved=%s root=%s exists=%s is_file=%s",
                path,
                full_path,
                output_root,
                full_path.exists(),
                full_path.is_file(),
            )
            raise HTTPException(status_code=404, detail="Image not found")

        logger.info(f"Serving output images from {output_root}")

    # Serve images dynamically to handle missing source names gracefully
    if config.comfyui_instance_base_path:
        input_root = (Path(config.comfyui_instance_base_path) / "input").resolve()
        app.state.image_debug_info["input_root"] = str(input_root)

        @app.get("/images/input")
        async def serve_input_image(path: str):
            from fastapi import HTTPException

            requested_path = Path(path)
            if requested_path.is_absolute():
                full_path = requested_path.resolve()
            else:
                full_path = (input_root / path.lstrip("/")).resolve()
            try:
                full_path.relative_to(input_root)
            except ValueError:
                logger.warning(
                    "Input image denied: requested=%r resolved=%s root=%s",
                    path,
                    full_path,
                    input_root,
                )
                raise HTTPException(status_code=403, detail="Access denied")

            if full_path.exists() and full_path.is_file():
                logger.info(
                    "Serving input image: requested=%r resolved=%s root=%s",
                    path,
                    full_path,
                    input_root,
                )
                return FileResponse(full_path)

            logger.warning(
                "Input image not found: requested=%r resolved=%s root=%s exists=%s is_file=%s",
                path,
                full_path,
                input_root,
                full_path.exists(),
                full_path.is_file(),
            )
            raise HTTPException(status_code=404, detail="Input image not found")

        logger.info(f"Serving input images from {input_root}")

        images_dir = Path(config.comfyui_instance_base_path).parent
        if images_dir.exists():
            default_instance_name = Path(config.comfyui_instance_base_path).name

            @app.get("/images/{file_path:path}")
            async def serve_images(file_path: str):
                cleaned_path = file_path.lstrip("/")
                parts = cleaned_path.split("/")
                original_path = cleaned_path

                # Fallback to default instance if a standard folder is accessed directly
                if parts and parts[0] in ["input", "output", "release", "prerelease"]:
                    cleaned_path = f"{default_instance_name}/{cleaned_path}"

                full_path = images_dir / cleaned_path

                # Security check to prevent path traversal
                try:
                    resolved_full = full_path.resolve()
                    resolved_base = images_dir.resolve()
                    resolved_full.relative_to(resolved_base)
                except ValueError:
                    from fastapi import HTTPException

                    logger.warning(
                        "Legacy image denied: requested=%r cleaned=%r resolved=%s root=%s",
                        file_path,
                        cleaned_path,
                        full_path.resolve(),
                        images_dir.resolve(),
                    )
                    raise HTTPException(status_code=403, detail="Access denied")

                if resolved_full.exists() and resolved_full.is_file():
                    logger.info(
                        "Serving legacy image: requested=%r original=%r cleaned=%r resolved=%s root=%s",
                        file_path,
                        original_path,
                        cleaned_path,
                        resolved_full,
                        resolved_base,
                    )
                    return FileResponse(resolved_full)

                from fastapi import HTTPException

                logger.warning(
                    "Legacy image not found: requested=%r original=%r cleaned=%r resolved=%s root=%s exists=%s is_file=%s",
                    file_path,
                    original_path,
                    cleaned_path,
                    resolved_full,
                    resolved_base,
                    resolved_full.exists(),
                    resolved_full.is_file(),
                )
                raise HTTPException(status_code=404, detail="Image not found")

            logger.info(
                f"Serving images dynamically from {images_dir} (default instance: {default_instance_name})"
            )
        else:
            logger.warning(f"Parent of ComfyUI instance path {images_dir} does not exist")

    # SPA handling
    INDEX_HTML_PATH = STATIC_DIR / "index.html"

    def inject_env_config(html_content: str) -> str:
        """Inject environment variables as window.ENV in index.html"""
        base_path = config.comfyui_instance_base_path
        if not base_path:
            raise ValueError("COMFYUI_INSTANCE_BASE_PATH configuration is missing.")

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
