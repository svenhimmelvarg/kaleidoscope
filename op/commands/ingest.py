import os
import subprocess
import sys
import click
import logging

from op.config import ensure_config
from op.utils.banner import display_indexer_banner, display_error, display_info

logger = logging.getLogger(__name__)


@click.command()
@click.argument("path", required=True)
def ingest(path):
    logger.info("Starting ingest")
    config = ensure_config()

    watch_path = os.path.abspath(path)

    if not os.path.exists(watch_path):
        logger.error(f"Path not found: {watch_path}")
        display_error(f"Path not found: {watch_path}")
        raise SystemExit(1)

    logger.info(f"Ingesting path: {watch_path}")

    display_indexer_banner(watch_path, config.index_name, config.meilisearch_host)

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
        "false",
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
        logger.error(f"Ingest failed: {e}")
        display_error(f"Ingest failed: {e}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        logger.info("Ingest stopped by user")
        display_info("Ingest stopped")
