import os
import subprocess
import sys
import click
import logging
from urllib.parse import urlparse


from op.config import ensure_config, get_config_value, load_config
from op.utils.banner import display_banner, display_error, display_info
from op.install import download_meilisearch, download_convex

logger = logging.getLogger(__name__)


@click.group()
def serve():
    config = load_config()
    data_dir = config.data_dir if config and config.data_dir else "./data"
    os.makedirs(data_dir, exist_ok=True)


@serve.command()
@click.option("--port", "-p", type=int, help="Port to run the server on (overrides config)")
def kaleidescope(port):
    logger.info("Starting kaleidescope server")
    config = ensure_config()

    display_banner(config, "Kaleidescope Server")
    display_info(f"Starting server at {config.kaleidescope_api_url}")

    parsed_url = urlparse(config.kaleidescope_api_url)
    port = port or parsed_url.port or 8000
    host = parsed_url.hostname or "127.0.0.1"

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "kaleidescope.main:app",
                "--reload",
                "--host",
                host,
                "--port",
                str(port),
            ],
            cwd=config.kaleidescope_repo_path,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Server failed to start: {e}")
        display_error(f"Server failed to start: {e}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        display_info("Server stopped")


@serve.command()
@click.option("--path", "-p", help="Path to ComfyUI output directory")
def indexer(path):
    logger.info("Starting indexer")
    config = ensure_config()

    comfyui_path = path or config.comfyui_output_path or get_config_value("COMFYUI_OUTPUT_PATH")

    if not comfyui_path:
        print("config.error - No comfyui instance configured")
        print()
        print("type:  op config set COMFYUI_OUTPUT_PATH /path/to/output")
        raise SystemExit(1)

    watch_path = os.path.join(comfyui_path, config.release_folder)

    logger.info(f"Indexing path: {comfyui_path}")
    logger.info(f"Watch folder: {watch_path}")

    from op.utils.banner import display_indexer_banner

    display_indexer_banner(watch_path, config.index_name, config.meilisearch_host)

    from op.indexer import run_indexer

    try:
        run_indexer(
            watch_path=watch_path,
            index_name=config.index_name,
            meilisearch_url=config.meilisearch_host,
            root_path="./kaleidescope/static/images",
            watch=True,
        )
    except Exception as e:
        logger.error(f"Indexer failed: {e}")
        display_error(f"Indexer failed: {e}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        logger.info("Indexer stopped by user")
        display_info("Indexer stopped")


@serve.command(name="indexer.legacy")
@click.option("--path", "-p", help="Path to ComfyUI output directory")
def indexer_legacy(path):
    logger.info("Starting legacy indexer")
    config = ensure_config()

    comfyui_path = path or config.comfyui_output_path or get_config_value("COMFYUI_OUTPUT_PATH")

    if not comfyui_path:
        print("config.error - No comfyui instance configured")
        print()
        print("type:  op config set COMFYUI_OUTPUT_PATH /path/to/output")
        raise SystemExit(1)

    # Resolve to absolute path because we change cwd below
    watch_path = os.path.abspath(os.path.join(comfyui_path, config.release_folder))

    logger.info(f"Indexing path: {comfyui_path}")
    logger.info(f"Watch folder: {watch_path}")

    # We need to run this from the indexer.legacy directory so it can find its local imports
    # like 'punter', 'graph', etc.
    cwd = os.path.join(os.getcwd(), "indexer.legacy")

    if not os.path.exists(cwd):
        logger.error(f"Directory not found: {cwd}")
        display_error(f"Directory not found: {cwd}")
        raise SystemExit(1)

    data_dir = os.path.realpath(config.data_dir)

    cmd = [
        sys.executable,
        "graph.py",
        watch_path,
        "--watch",
        "true",
        "--data_dir",
        data_dir,
        "--indexer.host",
        config.meilisearch_host,
        "--indexer.name",
        config.index_name,
    ]

    logger.info(f"Running command: {' '.join(cmd)} in {cwd}")

    try:
        subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Legacy indexer failed: {e}")
        display_error(f"Legacy indexer failed: {e}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        logger.info("Legacy indexer stopped by user")
        display_info("Legacy indexer stopped")


@serve.command(name="kaleidescope.ui")
def kaleidescope_ui():
    logger.info("Starting kaleidescope.ui dev server")
    config = ensure_config()

    parsed_url = urlparse(config.kaleidescope_ui_url)
    port = parsed_url.port or 5173
    host = parsed_url.hostname or "127.0.0.1"

    env = os.environ.copy()
    env["VITE_KALEIDESCOPE_API_URL"] = config.kaleidescope_api_url or "http://127.0.0.1:8000"
    env["VITE_MEILISEARCH_HOST"] = config.meilisearch_host or "127.0.0.1:7700"
    env["VITE_CONVEX_URL"] = config.convex_url or "http://127.0.0.1:3214"

    display_banner(config, "Kaleidescope UI Dev Server")
    display_info(f"Starting UI server at http://{host}:{port}")
    display_info(f"Proxying API to: {config.kaleidescope_api_url}")
    display_info(f"Meilisearch: {env['VITE_MEILISEARCH_HOST']}")

    try:
        subprocess.run(
            [
                "npm",
                "run",
                "dev",
                "--",
                "--host",
                host,
                "--port",
                str(port),
            ],
            env=env,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"UI dev server failed to start: {e}")
        display_error(f"UI dev server failed to start: {e}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        logger.info("UI dev server stopped by user")
        display_info("UI dev server stopped")


@serve.command()
def convex():
    logger.info("Starting Convex")
    config = ensure_config()

    run_convex_path = "./bin/run_convex.sh"

    if not os.path.exists(run_convex_path):
        logger.error(f"Convex script not found at {run_convex_path}")
        display_error(f"Convex script not found at {run_convex_path}")
        raise SystemExit(1)

    parsed_url = urlparse(config.convex_url)
    port = parsed_url.port or 3214

    convex_bin_path = "./bin/convex-local-backend"
    if sys.platform == "win32":
        convex_bin_path += ".exe"

    if not os.path.exists(convex_bin_path):
        display_info(f"Convex binary not found at {convex_bin_path}, downloading...")
        try:
            download_convex(convex_bin_path)
        except Exception as e:
            logger.error(f"Failed to download Convex: {e}")
            display_error(f"Failed to download Convex: {e}")
            raise SystemExit(1)

    display_banner(config, "Convex Server")
    display_info(f"Starting Convex at {config.convex_url}")
    display_info(f"Instance Name: {config.convex_instance_name}")

    try:
        subprocess.run(
            [
                run_convex_path,
                config.convex_instance_name,
                config.convex_secret,
                str(port),
                config.data_dir,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Convex failed to start: {e}")
        display_error(f"Convex failed to start: {e}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        logger.info("Convex stopped by user")
        display_info("Convex stopped")


@serve.command()
def search():
    logger.info("Starting MeiliSearch")

    config = load_config()

    if config is None:
        logger.error("No .env file found")
        display_error("No .env file found. Run 'op init' first.")
        raise SystemExit(1)

    meilisearch_path = "./bin/meilisearch"

    if not os.path.exists(meilisearch_path):
        display_info(f"MeiliSearch binary not found at {meilisearch_path}, downloading...")
        try:
            download_meilisearch(meilisearch_path)
        except Exception as e:
            logger.error(f"Failed to download MeiliSearch: {e}")
            display_error(f"Failed to download MeiliSearch: {e}")
            raise SystemExit(1)

    display_info(f"Starting MeiliSearch at {config.meilisearch_host}")

    try:
        subprocess.run(
            [
                meilisearch_path,
                "--http-addr",
                config.meilisearch_host,
                "--master-key",
                "password",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"MeiliSearch failed to start: {e}")
        display_error(f"MeiliSearch failed to start: {e}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        logger.info("MeiliSearch stopped by user")
        display_info("MeiliSearch stopped")
