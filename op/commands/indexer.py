import os
import click
import logging

from op.config import ensure_config, set_config_value
from op.utils.banner import display_success, display_info

logger = logging.getLogger(__name__)


@click.group()
def indexer():
    pass


@indexer.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def add(path):
    logger.info(f"Adding indexer path: {path}")

    config = ensure_config()

    release_folder = os.path.join(path, config.release_folder)
    prerelease_folder = os.path.join(path, config.prerelease_folder)

    os.makedirs(release_folder, exist_ok=True)
    os.makedirs(prerelease_folder, exist_ok=True)

    logger.info(f"Created release folders: {release_folder}, {prerelease_folder}")

    set_config_value("COMFYUI_INSTANCE_BASE_PATH", path)
    display_success(f"Added ComfyUI instance base path: {path}")
    display_info(f"Release folder: {release_folder}")
    display_info(f"Prerelease folder: {prerelease_folder}")
