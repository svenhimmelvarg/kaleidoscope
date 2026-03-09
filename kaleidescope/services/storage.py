import json
import os
import logging
from typing import Optional, Dict, Any
from kaleidescope.config import Config

logger = logging.getLogger(__name__)


def store_get_json(config: Config, _id: str, key: str) -> Optional[Dict[str, Any]]:
    file_path = os.path.join(config.data_dir, "output", config.index_name, _id, f"{key}.json")

    logger.debug(f"Reading JSON from {file_path}")

    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return None

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None
