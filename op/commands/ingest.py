import os
import subprocess
import sys
import click
import logging
import glob

from op.config import ensure_config
from op.utils.banner import display_indexer_banner, display_error, display_info

logger = logging.getLogger(__name__)


@click.command()
@click.argument("paths", nargs=-1, required=True)
def ingest(paths):
    logger.info("Starting ingest")
    config = ensure_config()

    cwd = os.path.join(os.getcwd(), "indexer.legacy")

    if not os.path.exists(cwd):
        logger.error(f"Directory not found: {cwd}")
        display_error(f"Directory not found: {cwd}")
        raise SystemExit(1)

    data_dir = os.path.realpath(config.data_dir)

    # Resolve all paths (handling both shell-expanded paths and explicit globs)
    resolved_paths = []
    for p in paths:
        # glob.glob handles both exact paths and glob patterns
        expanded = os.path.expanduser(p)
        matches = (
            glob.glob(expanded)
            if "*" in expanded or "?" in expanded or "[" in expanded
            else [expanded]
        )
        if not matches:
            resolved_paths.append(os.path.abspath(expanded))
        else:
            resolved_paths.extend([os.path.abspath(m) for m in matches])

    # Filter for directories
    directories_to_ingest = []
    for rp in resolved_paths:
        if os.path.isdir(rp):
            if rp not in directories_to_ingest:  # keep unique
                directories_to_ingest.append(rp)
        else:
            logger.warning(f"Skipping non-directory path: {rp}")

    if not directories_to_ingest:
        logger.error("No valid directories found to ingest.")
        display_error("No valid directories found to ingest.")
        raise SystemExit(1)

    has_errors = False

    for watch_path in directories_to_ingest:
        logger.info(f"Ingesting path: {watch_path}")
        display_indexer_banner(watch_path, config.index_name, config.meilisearch_host)

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
            logger.error(f"Ingest failed for {watch_path}: {e}")
            display_error(f"Ingest failed for {watch_path}: {e}")
            has_errors = True
        except KeyboardInterrupt:
            logger.info("Ingest stopped by user")
            display_info("Ingest stopped")
            raise SystemExit(1)

    if has_errors:
        display_error("Ingestion completed with some errors.")
        raise SystemExit(1)
