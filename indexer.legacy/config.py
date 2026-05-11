import os
import json

RELEASE_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "release.json")

def is_indexing_experimental_enabled():
    try:
        with open(RELEASE_JSON_PATH, "r") as f:
            data = json.load(f)
            return data.get("experimental.indexing", {}).get("defaultValue", False)
    except Exception:
        return False

def get_indexer_legacy_config():
    """
    Returns the indexer_legacy configuration block from config.json
    if the experimental.indexing feature flag is enabled.
    Otherwise, returns default values.
    """
    defaults = {
        "hyponym_count_cap": 50,
        "vlm": {
            "model_name": "smolvlm",  # Fallback to older hardcoded default
            "prompt": "describe this image in great detail focusing on the concrete subjects, objects, and setting."
        }
    }

    if not is_indexing_experimental_enabled():
        return defaults

    config_path = os.path.join(os.getcwd(), "config.json")
    if not os.path.exists(config_path):
        return defaults

    try:
        with open(config_path, "r") as f:
            data = json.load(f)
            config = data.get("indexer_legacy", {})
            
            # Merge loaded config with defaults to ensure all keys exist
            merged_config = defaults.copy()
            if "hyponym_count_cap" in config:
                merged_config["hyponym_count_cap"] = config["hyponym_count_cap"]
            
            if "vlm" in config:
                merged_config["vlm"] = defaults["vlm"].copy()
                merged_config["vlm"].update(config["vlm"])
                
            return merged_config
    except Exception as e:
        print(f"Warning: Failed to load config.json: {e}")
        return defaults
