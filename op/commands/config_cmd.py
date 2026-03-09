import click
import logging

from dotenv import dotenv_values

from op.config import init_env, set_config_value, load_config, get_env_path, DEFAULT_CONFIG
from op.utils.banner import display_success, display_info

logger = logging.getLogger(__name__)


@click.group()
def config():
    pass


@config.command()
def init():
    logger.info("Initializing op configuration")
    env_path = init_env()
    display_success(f"Initialized op configuration at {env_path}")
    display_info("Edit .env file to customize settings")


@config.command(name="set")
@click.argument("key")
@click.argument("value")
def set_config(key, value):
    logger.info(f"Setting configuration {key}={value}")
    set_config_value(key, value)
    display_success(f"Set {key}={value}")


@config.command()
def show():
    config = load_config()
    if config:
        print(f"KALEIDESCOPE_API_URL={config.kaleidescope_api_url}")
        print(f"KALEIDESCOPE_UI_URL={config.kaleidescope_ui_url}")
        print(f"COMFYUI_OUTPUT_PATH={config.comfyui_output_path}")
        print(f"RELEASE_FOLDER={config.release_folder}")
        print(f"PRERELEASE_FOLDER={config.prerelease_folder}")
        print(f"MEILISEARCH_HOST={config.meilisearch_host}")
        print(f"INDEX_NAME={config.index_name}")
        print(f"CONVEX_URL={config.convex_url}")
        print(f"DATA_DIR={config.data_dir}")
    else:
        print("No configuration found. Run 'op init' first.")


@config.command()
def validate():
    env_path = get_env_path()

    if not env_path.exists():
        print(f"{env_path.name} FAILED - No .env file found")
        print()
        print("type:  op config init")
        return

    config_dict = dotenv_values(env_path)
    expected_keys = set(DEFAULT_CONFIG.keys())

    missing_or_empty = []
    for key in expected_keys:
        value = config_dict.get(key)
        if not value:
            missing_or_empty.append(key)

    if not missing_or_empty:
        print(f"{env_path.name} OK")
        return

    print(f"{env_path.name} FAILED - Missing configuration keys detected:")
    print()

    for key in sorted(missing_or_empty):
        default_value = DEFAULT_CONFIG[key]
        print(f"  op config set {key} (default: {default_value})")
