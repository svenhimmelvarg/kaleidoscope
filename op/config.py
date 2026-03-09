from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging
import os

from dotenv import dotenv_values, set_key


logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "KALEIDESCOPE_API_URL": "http://127.0.0.1:8000",
    "KALEIDESCOPE_UI_URL": "http://127.0.0.1:5173",
    "KALEIDESCOPE_REPO_PATH": None,
    "COMFYUI_OUTPUT_PATH": None,
    "COMFYUI_INSTANCE_BASE_PATH": None,
    "MEILISEARCH_HOST": "127.0.0.1:7700",
    "INDEX_NAME": "comfy_outputs_v110",
    "CONVEX_URL": "http://127.0.0.1:3214",
    "CONVEX_INSTANCE_NAME": "kaleidescope",
    "CONVEX_SECRET": "password",
    "DATA_DIR": "./data",
    "RELEASE_FOLDER": "release",
    "PRERELEASE_FOLDER": "prerelease",
}


@dataclass(frozen=True)
class Config:
    kaleidescope_api_url: str
    kaleidescope_ui_url: str
    kaleidescope_repo_path: str
    comfyui_output_path: str
    comfyui_instance_base_path: str
    meilisearch_host: str
    index_name: str
    convex_url: str
    convex_instance_name: str
    convex_secret: str
    data_dir: str
    release_folder: str
    prerelease_folder: str


def get_env_path() -> Path:
    env_file = os.environ.get("OP_ENV_FILE", ".env")
    path = Path(env_file)
    return path if path.is_absolute() else Path.cwd() / path


def init_env() -> Path:
    env_path = get_env_path()

    if not env_path.exists():
        env_content = """# op CLI configuration
# Kaleidescope API endpoints
KALEIDESCOPE_API_URL=http://127.0.0.1:8000
KALEIDESCOPE_UI_URL=http://127.0.0.1:5173

# Kaleidoscope repository path
KALEIDESCOPE_REPO_PATH=

# ComfyUI configuration
COMFYUI_OUTPUT_PATH=
COMFYUI_INSTANCE_BASE_PATH=

# Release folders (for indexer)
RELEASE_FOLDER=release
PRERELEASE_FOLDER=prerelease

# Meilisearch configuration
MEILISEARCH_HOST=127.0.0.1:7700
INDEX_NAME=comfy_outputs_v110

# Convex configuration
CONVEX_URL=http://127.0.0.1:3214
CONVEX_INSTANCE_NAME=kaleidescope
CONVEX_SECRET=password

# Data directory
DATA_DIR=./data
"""
        env_path.write_text(env_content)
        logger.info(f"Created environment file at {env_path}")
        return env_path

    existing_config = dotenv_values(env_path)
    updated = False

    for key, default_value in DEFAULT_CONFIG.items():
        if key not in existing_config or existing_config.get(key) is None:
            value = default_value if default_value is not None else ""
            set_key(env_path, key, value)
            logger.info(
                f"Added missing configuration {key}={'<no value>' if default_value is None else value}"
            )
            updated = True

    if updated:
        logger.info(f"Updated environment file at {env_path}")
    else:
        logger.info(f"Environment file already complete at {env_path}")

    return env_path


def load_config() -> Optional[Config]:
    env_path = get_env_path()

    if not env_path.exists():
        logger.warning(f"Environment file not found at {env_path}")
        return None

    config_dict = dotenv_values(env_path)

    def get_value(key: str) -> str:
        value = config_dict.get(key)
        if value is not None and value != "":
            return str(value)
        default = DEFAULT_CONFIG[key]
        return default if default is not None else ""

    return Config(
        kaleidescope_api_url=get_value("KALEIDESCOPE_API_URL"),
        kaleidescope_ui_url=get_value("KALEIDESCOPE_UI_URL"),
        kaleidescope_repo_path=get_value("KALEIDESCOPE_REPO_PATH"),
        comfyui_output_path=get_value("COMFYUI_OUTPUT_PATH"),
        comfyui_instance_base_path=get_value("COMFYUI_INSTANCE_BASE_PATH"),
        meilisearch_host=get_value("MEILISEARCH_HOST"),
        index_name=get_value("INDEX_NAME"),
        convex_url=get_value("CONVEX_URL"),
        convex_instance_name=get_value("CONVEX_INSTANCE_NAME"),
        convex_secret=get_value("CONVEX_SECRET"),
        data_dir=get_value("DATA_DIR"),
        release_folder=get_value("RELEASE_FOLDER"),
        prerelease_folder=get_value("PRERELEASE_FOLDER"),
    )


def validate_config(config: Optional[Config]) -> tuple[bool, list[str]]:
    if config is None:
        return False, ["No configuration found. Run 'op init' first."]

    errors = []

    if not config.kaleidescope_api_url:
        errors.append("KALEIDESCOPE_API_URL is not set")

    if not config.kaleidescope_ui_url:
        errors.append("KALEIDESCOPE_UI_URL is not set")

    if not config.kaleidescope_repo_path:
        errors.append("KALEIDESCOPE_REPO_PATH is not set")

    if not config.comfyui_instance_base_path:
        errors.append("COMFYUI_INSTANCE_BASE_PATH is not set")

    return len(errors) == 0, errors


def set_config_value(key: str, value: str) -> None:
    env_path = get_env_path()

    if not env_path.exists():
        init_env()

    set_key(env_path, key, value)
    logger.info(f"Set configuration {key}={value}")


def get_config_value(key: str) -> Optional[str]:
    env_path = get_env_path()

    if not env_path.exists():
        return None

    config_dict = dotenv_values(env_path)
    return config_dict.get(key)


def ensure_config() -> Config:
    config = load_config()

    if config is None:
        logger.error("No .env file found")
        print("Error: No .env file found. Run 'op init' first.")
        raise SystemExit(1)

    is_valid, errors = validate_config(config)

    if not is_valid:
        logger.error(f"Invalid configuration: {errors}")
        print("Error: Invalid configuration:")
        for error in errors:
            print(f"  - {error}")
        raise SystemExit(1)

    logger.info("Configuration validated successfully")
    return config
