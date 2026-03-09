import os
import stat
import platform
import logging
import requests
from dataclasses import dataclass
from typing import Dict
from rich.progress import Progress, SpinnerColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn

logger = logging.getLogger(__name__)

@dataclass
class PlatformInfo:
    os_name: str
    arch: str

def get_platform_info() -> PlatformInfo:
    os_name = platform.system().lower()
    arch = platform.machine().lower()
    logger.debug(f"Detected platform: {os_name} {arch}")
    return PlatformInfo(os_name=os_name, arch=arch)

def get_meilisearch_url(plat_info: PlatformInfo) -> str:
    base_url = "https://github.com/meilisearch/meilisearch/releases/download/v1.37.0"
    
    os_map: Dict[str, str] = {
        "darwin": "macos", 
        "linux": "linux", 
        "windows": "windows"
    }
    
    os_str = os_map.get(plat_info.os_name, "linux")
    
    if plat_info.arch in ["aarch64", "arm64"]:
        arch_str = "apple-silicon" if os_str == "macos" else "aarch64"
    else:
        arch_str = "amd64"
        
    binary_name = f"meilisearch-{os_str}-{arch_str}"
    if os_str == "windows":
        binary_name += ".exe"
        
    url = f"{base_url}/{binary_name}"
    logger.debug(f"Generated Meilisearch URL: {url}")
    return url

def download_meilisearch(dest_path: str) -> None:
    plat_info = get_platform_info()
    url = get_meilisearch_url(plat_info)
    
    logger.info(f"Starting download of Meilisearch from {url}")
    
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get("content-length", 0))
    
    with Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Downloading Meilisearch...", total=total_size)
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                progress.update(task, advance=len(chunk))
                
    if plat_info.os_name != "windows":
        logger.debug(f"Setting executable permissions on {dest_path}")
        st = os.stat(dest_path)
        os.chmod(dest_path, st.st_mode | stat.S_IEXEC)
    
    logger.info(f"Successfully downloaded Meilisearch to {dest_path}")
