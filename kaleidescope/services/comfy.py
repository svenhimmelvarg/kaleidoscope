import os
import requests
import time
import logging
import shutil
from typing import Dict, Any, List, Optional, Tuple
from kaleidescope.config import Config
from convex import ConvexClient

logger = logging.getLogger(__name__)


def is_virtual_uri(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("virtual://")


def is_local_output_uri(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("local-output://")


def process_local_output_uri(value: str, config: Config) -> str:
    if not is_local_output_uri(value):
        return value

    try:
        data = value.replace("local-output://", "")
        if "||" not in data:
            logger.error(f"Invalid local-output URI format: {value}")
            return value

        doc_id, src_path = data.split("||", 1)

        release_folder = config.output_folder_filter if config.output_folder_filter else "release"

        # ComfyUI expects a path relative to its input directory
        rel_path = f"{release_folder}/{doc_id}.png"

        # Target absolute path in the input directory
        dest_path = os.path.join(config.comfyui_instance_base_path, "input", rel_path)

        if os.path.exists(src_path):
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(src_path, dest_path)
            logger.info(f"Copied output {src_path} to input {dest_path}")
            return rel_path
        else:
            logger.error(f"Source file not found for local-output: {src_path}")

    except Exception as e:
        logger.error(f"Error processing local-output URI {value}: {e}")

    return value


def parse_virtual_uri(virtual_uri: str) -> Tuple[str, str]:
    # virtual://storageId/path/to/file
    parts = virtual_uri.split("://")[1].split("/")
    storage_id = parts[0]
    path = "/".join(parts[1:])
    return storage_id, path


def download_from_convex(client: ConvexClient, storage_id: str, output_path: str) -> bool:
    try:
        file_url = client.query("assets:getImageUrl", {"storageId": storage_id})
        if not file_url:
            logger.error(f"Could not retrieve URL for storage ID: {storage_id}")
            return False

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        response = requests.get(file_url)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

        return True
    except Exception as e:
        logger.error(f"Error downloading from convex: {e}")
        return False


def process_virtual_uri(client: ConvexClient, value: str, config: Config) -> str:
    if not is_virtual_uri(value):
        return value

    storage_id, path = parse_virtual_uri(value)

    # Extract filename from the end of the path
    filename = path.split("/")[-1]

    # Use the output_folder_filter (which corresponds to RELEASE_FOLDER)
    release_folder = config.output_folder_filter if config.output_folder_filter else "release"

    # ComfyUI expects a path relative to its input directory
    rel_path = f"{release_folder}/{filename}"

    # Download directly to ComfyUI's input directory
    local_path = os.path.join(config.comfyui_instance_base_path, "input", rel_path)

    if download_from_convex(client, storage_id, local_path):
        logger.info(f"Downloaded {value} to {local_path}")
        return rel_path

    return value


def queue_prompt(comfy_base_url: str, prompt: Dict[str, Any], client_id: str) -> Optional[str]:
    p = {"prompt": prompt, "client_id": client_id}
    try:
        res = requests.post(f"{comfy_base_url}/prompt", json=p)
        res.raise_for_status()
        return res.json().get("prompt_id")
    except Exception as e:
        logger.error(f"Error queuing prompt: {e}")
        return None


def get_history(comfy_base_url: str, prompt_id: str) -> Optional[Dict[str, Any]]:
    try:
        res = requests.get(f"{comfy_base_url}/history/{prompt_id}")
        res.raise_for_status()
        return res.json().get(prompt_id)
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return None


def cancel_workflow(comfy_base_url: str, prompt_id: str) -> bool:
    try:
        requests.post(f"{comfy_base_url}/interrupt", json={"prompt_id": prompt_id})
        return True
    except Exception as e:
        logger.error(f"Error cancelling workflow: {e}")
        return False


def wait_for_files(
    paths: List[str], timeout: float = 10.0, poll_interval: float = 0.5
) -> Tuple[bool, List[str]]:
    start = time.time()
    while time.time() - start < timeout:
        missing = [p for p in paths if not os.path.exists(p)]
        if not missing:
            return True, []
        time.sleep(poll_interval)
    return False, [p for p in paths if not os.path.exists(p)]


def invoke_workflow(
    config: Config,
    convex_client: ConvexClient,
    prompt_id: str,
    notification_id: str,
    body: List[Dict[str, Any]],
    png_prompt: Dict[str, Any],
    png_workflow: Dict[str, Any],
):
    # Prepare payload
    # body is list of overrides: [{"id": "6", "text": "value"}, ...]

    payload = png_prompt.copy()

    # Apply overrides
    for entry in body:
        node_id = entry.get("id")
        # Find key that isn't id
        field = next((k for k in entry.keys() if k != "id"), None)
        if not field:
            continue

        value = entry.get(field)

        if isinstance(value, str) and is_virtual_uri(value):
            value = process_virtual_uri(convex_client, value, config)
        elif isinstance(value, str) and is_local_output_uri(value):
            value = process_local_output_uri(value, config)

        # update payload
        # payload is map of node_id -> node_data
        if node_id in payload and "inputs" in payload[node_id]:
            payload[node_id]["inputs"][field] = value

    # Queue prompt
    # Assuming local comfy instance
    comfy_url = "http://127.0.0.1:8188"
    # TODO: Use config if available or config.comfyui_instance_base_path to infer?
    # Config has HOST/PORT but those are for THIS app.
    # main.py uses http://127.0.0.1:8188 hardcoded in one place, so I'll stick to that default

    prompt_id_resp = queue_prompt(comfy_url, payload, "kaleidescope")
    logger.info(f"ComfyUI prompt queued: prompt_id={prompt_id_resp}")

    if not prompt_id_resp:
        # Update failure
        from kaleidescope.services.convex import update_notification

        update_notification(
            convex_client,
            notification_id,
            {
                "status": "ERROR",
                "payload": {"input": body, "output": {"error": "Could not queue prompt"}},
            },
        )
        return

    from kaleidescope.services.convex import update_notification

    update_notification(convex_client, notification_id, {"workflow_id": prompt_id_resp})

    # Poll for completion
    # In a real system we'd use websocket, here we poll history
    start_time = time.time()
    max_wait = 300  # 5 mins

    history = None
    while time.time() - start_time < max_wait:
        history = get_history(comfy_url, prompt_id_resp)
        if history and "outputs" in history:
            break
        time.sleep(1)

    if not history or "outputs" not in history:
        update_notification(
            convex_client,
            notification_id,
            {
                "status": "ERROR",
                "payload": {"input": body, "output": {"error": "Timeout or no output"}},
            },
        )
        return

    elapsed = (time.time() - start_time) * 1000
    outputs = history["outputs"]
    logger.info(
        f"ComfyUI history outputs: node_ids={list(outputs.keys())}, filter={config.output_folder_filter}"
    )

    image_paths = []
    response_images = []

    for node_id, output_data in outputs.items():
        if "images" not in output_data:
            logger.debug(f"Node {node_id}: no images key in output")
            continue

        logger.info(f"Node {node_id}: found {len(output_data['images'])} images")
        for img in output_data["images"]:
            subfolder = img.get("subfolder", "")
            filename = img.get("filename", "")
            if config.output_folder_filter and subfolder.find(config.output_folder_filter) < 0:
                logger.info(
                    f"Filtered out: subfolder='{subfolder}' does not contain '{config.output_folder_filter}'"
                )
                continue

            logger.info(f"Including image: subfolder='{subfolder}', filename='{filename}'")

            full_path = os.path.join(
                config.comfyui_instance_base_path,
                "output",
                subfolder,
                filename,
            )
            full_path = os.path.abspath(full_path)
            image_paths.append(full_path)

            instance_name = os.path.basename(config.comfyui_instance_base_path.rstrip("/\\"))
            uri = f"/images/{instance_name}/output/{subfolder}/{filename}"

            response_images.append({"uri": uri, "_path": full_path, "elapsed_ms": elapsed})

    all_found, missing = wait_for_files(image_paths)
    if not all_found:
        logger.warning(f"Missing files: {missing}")

    from kaleidescope.services.image import update_metadata
    from op.indexer.utils import hash_file

    import json
    for img_data in response_images:
        path = img_data.pop("_path")
        if os.path.exists(path):
            meta_dict = {"elapsed_ms": elapsed, "parent_id": prompt_id}
            if png_workflow and isinstance(png_workflow, dict) and "message" not in png_workflow:
                meta_dict["workflow"] = json.dumps(png_workflow)
            update_metadata(path, meta_dict)
            img_data["_id"] = hash_file(path)
            logger.info(f"Hashed {path} to {img_data['_id']}")
        else:
            img_data["_id"] = str(hash(img_data["uri"]))
            logger.error(f"File {path} not found for hashing")

    # Update notification success
    logger.info(
        f"Updating notification {notification_id}: {len(response_images)} images, elapsed={elapsed:.0f}ms"
    )
    update_notification(
        convex_client,
        notification_id,
        {
            "status": "completed",
            "payload": {
                "input": body,
                "output": {"images": response_images, "elapsed_ms": elapsed},
            },
        },
    )
