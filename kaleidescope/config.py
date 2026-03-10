from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse
import os
import sys

# Ensure op module can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from op.config import load_config as load_op_config
except ImportError:
    # Fallback if op module is not found (shouldn't happen in this repo structure)
    load_op_config = None


DEFAULT_CONFIG = {
    "CONVEX_URL": "http://127.0.0.1:3214",
    "INDEX_NAME": "comfy_outputs_v110",
    "DATA_DIR": "./data",
    "COMFYUI_INSTANCE_BASE_PATH": "",
    "PORT": "8000",
    "HOST": "127.0.0.1",
    "KALEIDESCOPE_API_URL": "http://127.0.0.1:8000",
    "MEILISEARCH_HOST": "127.0.0.1:7700",
}


@dataclass(frozen=True)
class Config:
    convex_url: str
    index_name: str
    data_dir: str
    comfyui_instance_base_path: str
    output_folder_filter: str
    port: int
    host: str
    kaleidescope_api_url: str
    meilisearch_host: str


def load_config() -> Config:
    op_conf = load_op_config() if load_op_config else None

    # Helper to get value from op config or default
    def get_op_value(attr: str, default_key: str) -> str:
        if op_conf and hasattr(op_conf, attr) and getattr(op_conf, attr):
            return str(getattr(op_conf, attr))
        return DEFAULT_CONFIG.get(default_key, "")

    api_url = get_op_value("kaleidescope_api_url", "KALEIDESCOPE_API_URL")

    derived_host = None
    derived_port = None
    if api_url:
        try:
            parsed = urlparse(api_url)
            derived_host = parsed.hostname
            derived_port = parsed.port
        except Exception:
            pass

    host_val = derived_host if derived_host else DEFAULT_CONFIG.get("HOST", "127.0.0.1")
    port_val = str(derived_port) if derived_port else DEFAULT_CONFIG.get("PORT", "8000")

    release_folder = "release"
    if op_conf and hasattr(op_conf, "release_folder") and op_conf.release_folder:
        release_folder = op_conf.release_folder

    return Config(
        convex_url=get_op_value("convex_url", "CONVEX_URL"),
        index_name=get_op_value("index_name", "INDEX_NAME"),
        data_dir=get_op_value("data_dir", "DATA_DIR"),
        comfyui_instance_base_path=get_op_value(
            "comfyui_instance_base_path", "COMFYUI_INSTANCE_BASE_PATH"
        ),
        output_folder_filter=release_folder,
        port=int(port_val),
        host=str(host_val),
        kaleidescope_api_url=api_url,
        meilisearch_host=get_op_value("meilisearch_host", "MEILISEARCH_HOST"),
    )
