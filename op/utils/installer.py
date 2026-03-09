import os
import platform
import stat
import requests
import logging
from dataclasses import dataclass

from rich.progress import (
    Progress,
    BarColumn,
    DownloadColumn,
    TextColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)

logger = logging.getLogger(__name__)

MEILISEARCH_VERSION = "v1.37.0"
BASE_URL = f"https://github.com/meilisearch/meilisearch/releases/download/{MEILISEARCH_VERSION}/meilisearch"


@dataclass(frozen=True)
class PlatformInfo:
    system: str
    machine: str


def get_platform_info() -> PlatformInfo:
    return PlatformInfo(
        system=platform.system().lower(),
        machine=platform.machine().lower(),
    )


def get_meilisearch_binary_name(info: PlatformInfo) -> str:
    if info.system == "linux":
        if info.machine in ["x86_64", "amd64"]:
            return "linux-amd64"
        elif info.machine in ["aarch64", "arm64"]:
            return "linux-aarch64"
    elif info.system == "darwin":
        if info.machine in ["x86_64", "amd64"]:
            return "macos-amd64"
        elif info.machine in ["arm64", "aarch64"]:
            return "macos-apple-silicon"
    elif info.system == "windows":
        if info.machine in ["x86_64", "amd64"]:
            return "windows-amd64.exe"

    raise ValueError(f"Unsupported platform: {info.system} {info.machine}")


def build_download_url(binary_name: str) -> str:
    return f"{BASE_URL}-{binary_name}"


def download_with_progress(url: str, dest_path: str) -> None:
    logger.info(f"Downloading {url} to {dest_path}")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))

    with Progress(
        TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
    ) as progress:
        task_id = progress.add_task(
            "download", filename=os.path.basename(dest_path), total=total_size
        )

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    progress.update(task_id, advance=len(chunk))


def make_executable(path: str) -> None:
    logger.info(f"Making {path} executable")
    current_stat = os.stat(path)
    os.chmod(path, current_stat.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_meilisearch(dest_path: str) -> None:
    logger.info("Starting Meilisearch installation process")

    dest_dir = os.path.dirname(dest_path)
    if not os.path.exists(dest_dir):
        logger.info(f"Creating directory {dest_dir}")
        os.makedirs(dest_dir, exist_ok=True)

    info = get_platform_info()
    logger.info(f"Detected platform: {info.system} {info.machine}")

    binary_name = get_meilisearch_binary_name(info)
    url = build_download_url(binary_name)

    download_with_progress(url, dest_path)

    if info.system != "windows":
        make_executable(dest_path)

    logger.info("Meilisearch installation completed successfully")
