import json
import time
import os
import mimetypes
import uuid
from datetime import datetime
import click
import requests
import logging

from op.config import ensure_config
from op.workflow.core import (
    build_invoke_url,
    build_notification_url,
    construct_asset_url,
    extract_outputs,
    is_local_image_path,
    compute_file_hash,
    construct_hashed_filename,
    replace_image_paths_in_payload,
)
from op.utils.api import get_workflow
from kaleidescope.services.convex import get_client, generate_upload_url, save_asset

logger = logging.getLogger(__name__)


def _comfy_base_url() -> str:
    return "http://127.0.0.1:8188"


def _set_save_image_prefix(prompt: dict, prefix: str) -> int:
    count = 0
    for node in prompt.values():
        if not isinstance(node, dict):
            continue
        class_type = node.get("class_type", "")
        if "SaveImage" not in class_type:
            continue
        inputs = node.setdefault("inputs", {})
        inputs["filename_prefix"] = prefix
        count += 1
    return count


def _extract_comfy_outputs(history: dict, config) -> list[dict]:
    outputs = []
    instance_name = os.path.basename(config.comfyui_instance_base_path.rstrip("/\\"))
    for output_data in history.get("outputs", {}).values():
        media_items = []
        if "images" in output_data:
            media_items.extend(output_data["images"])
        if "gifs" in output_data:
            media_items.extend(output_data["gifs"])

        for item in media_items:
            subfolder = item.get("subfolder", "")
            filename = item.get("filename", "")
            if not filename:
                continue
            file_path = os.path.abspath(
                os.path.join(config.comfyui_instance_base_path, "output", subfolder, filename)
            )
            uri = f"/images/{instance_name}/output/{subfolder}/{filename}"
            outputs.append({"file_path": file_path, "url": construct_asset_url(config.kaleidescope_ui_url, uri)})
    return outputs


def _queue_prompt_and_wait(prompt: dict, config) -> list[dict]:
    client_id = str(uuid.uuid4())
    comfy_url = _comfy_base_url()

    try:
        response = requests.post(
            f"{comfy_url}/prompt", json={"prompt": prompt, "client_id": client_id}, timeout=30
        )
        response.raise_for_status()
        prompt_id = response.json().get("prompt_id")
    except requests.exceptions.RequestException as e:
        click.echo(f"Error queueing prompt: {e}", err=True)
        raise SystemExit(1)

    if not prompt_id:
        click.echo("ComfyUI did not return a prompt_id.", err=True)
        raise SystemExit(1)

    start = time.time()
    while time.time() - start < 300:
        try:
            response = requests.get(f"{comfy_url}/history/{prompt_id}", timeout=30)
            response.raise_for_status()
            history = response.json().get(prompt_id)
        except requests.exceptions.RequestException as e:
            click.echo(f"Error checking ComfyUI history: {e}", err=True)
            raise SystemExit(1)

        if history and "outputs" in history:
            return _extract_comfy_outputs(history, config)

        time.sleep(2)

    click.echo("Timed out waiting for ComfyUI prompt completion.", err=True)
    raise SystemExit(1)


@click.command(name="workflow:invoke", no_args_is_help=True)
@click.argument("workflow_id")
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False))
def workflow_invoke(workflow_id: str, input_file: str):
    """
    Invoke a ComfyUI workflow using the provided workflow ID and an input JSON file.

    The input JSON file should contain a list of node overrides.
    It supports overriding text fields as well as automatically uploading local images.

    \b
    ## Examples

    \b
    **1. Text Input Override**
    Provide a JSON file to override text prompts for a specific node ID:
    ```json
    [
      {
        "id": "273",
        "text1": "A high quality professional photograph..."
      }
    ]
    ```

    \b
    **2. Local Image Upload**
    Provide a JSON file to override an image input. If the value is a valid local file path,
    the CLI will automatically upload it and substitute the correct URI before invoking the workflow:
    ```json
    [
      {
        "id": "78",
        "image": "./path/to/myimage.jpg"
      }
    ]
    ```
    """
    config = ensure_config()

    # Read the input payload
    try:
        with open(input_file, "r") as f:
            payload = json.load(f)
    except json.JSONDecodeError as e:
        click.echo(f"Error parsing input JSON: {e}", err=True)
        raise SystemExit(1)

    api_url = config.kaleidescope_api_url
    ui_url = config.kaleidescope_ui_url
    base_path = config.comfyui_instance_base_path
    release_folder = config.release_folder or "release"

    # Process image overrides
    replacements = {}
    convex_client = None

    for node in payload:
        for key, val in node.items():
            if isinstance(val, str) and is_local_image_path(val):
                local_path = val
                if local_path in replacements:
                    continue

                if convex_client is None:
                    convex_client = get_client(config.convex_url)

                with open(local_path, "rb") as img_f:
                    file_bytes = img_f.read()

                file_hash = compute_file_hash(file_bytes)
                hashed_filename = construct_hashed_filename(local_path, file_hash)
                mime_type, _ = mimetypes.guess_type(local_path)
                mime_type = mime_type or "application/octet-stream"

                upload_url = generate_upload_url(convex_client)
                if not upload_url:
                    click.echo(f"Failed to get upload URL for {local_path}", err=True)
                    raise SystemExit(1)

                try:
                    up_resp = requests.post(
                        upload_url,
                        headers={"Content-Type": mime_type},
                        data=file_bytes,
                    )
                    up_resp.raise_for_status()
                    storage_id = up_resp.json().get("storageId")
                except requests.exceptions.RequestException as e:
                    click.echo(f"Failed to upload {local_path}: {e}", err=True)
                    raise SystemExit(1)

                asset_data = {
                    "storageId": storage_id,
                    "source": "cli",
                    "path": f"input/{release_folder}/{hashed_filename}",
                    "name": hashed_filename,
                    "type": mime_type,
                    "size": len(file_bytes),
                }

                save_asset(convex_client, asset_data)

                virtual_uri = f"virtual://{storage_id}/cli/input/{release_folder}/{hashed_filename}"
                replacements[local_path] = virtual_uri

    if replacements:
        payload = replace_image_paths_in_payload(payload, replacements)

    invoke_url = build_invoke_url(api_url, workflow_id, config.invoke_method)

    # Send the invoke request
    try:
        response = requests.post(invoke_url, json=payload)
        response.raise_for_status()
        invoke_data = response.json()
    except requests.exceptions.RequestException as e:
        click.echo(f"Error invoking workflow: {e}", err=True)
        if hasattr(e, "response") and e.response is not None:
            click.echo(f"Response: {e.response.text}", err=True)
        raise SystemExit(1)

    notification_id = invoke_data.get("notification_id")
    if not notification_id:
        click.echo("Failed to get notification ID from invoke response", err=True)
        raise SystemExit(1)

    notification_url = build_notification_url(api_url, notification_id)

    # Poll for completion
    while True:
        try:
            resp = requests.get(notification_url)
            resp.raise_for_status()
            notif_data = resp.json()
        except requests.exceptions.RequestException as e:
            click.echo(f"Error checking notification status: {e}", err=True)
            raise SystemExit(1)

        # In main.py notifications might return an error dict directly
        if "error" in notif_data:
            click.echo(f"Notification error: {notif_data['error']}", err=True)
            raise SystemExit(1)

        status = notif_data.get("status")

        if status == "completed":
            payload_data = notif_data.get("payload", {})
            outputs = extract_outputs(payload_data, base_path, ui_url)

            # Print the final list of outputs as JSON
            click.echo(json.dumps([out.to_dict() for out in outputs], indent=2))
            break

        elif status == "ERROR":
            payload_data = notif_data.get("payload", {})
            output_err = payload_data.get("output", {}).get("error", "Unknown error")
            click.echo(f"Workflow failed: {output_err}", err=True)
            raise SystemExit(1)

        # Wait before polling again
        time.sleep(2)


@click.command(name="workflow:get", no_args_is_help=True)
@click.argument("workflow_id")
def workflow_get(workflow_id: str):
    """
    Get a workflow's details (inputs and text) from Meilisearch by its ID.

    Outputs a JSON object containing the `id`, `inputs`, and `text` fields.

    \b
    ## Examples

    \b
    **1. Retrieve a specific workflow**
    ```bash
    op workflow:get 1e11af0abd47a164eb008b4caeab57af7a8f064151c6f24f82cfd290da6f6d09
    ```

    \b
    **Example Output:**
    ```json
    {
      "id": "1e11af0abd47a164eb008b4caeab57af7a8f064151c6f24f82cfd290da6f6d09",
      "inputs": [
        {
          "_id": "120",
          "value": "283a78e6ad2ceb5ddb5ab9bb557eae85.jpg",
          "key": "image",
          "type": "image "
        }
      ],
      "text": [
        {
          "_id": "45",
          "value": "An incredibly striking high fashion full color editorial...",
          "key": "text",
          "type": "text "
        }
      ]
    }
    ```
    """
    config = ensure_config()

    from op.workflow.meilisearch import fetch_workflow_from_meilisearch, extract_workflow_fields

    try:
        doc = fetch_workflow_from_meilisearch(
            base_url=config.meilisearch_host, index_name=config.index_name, doc_id=workflow_id
        )
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            click.echo(f"Workflow '{workflow_id}' not found.", err=True)
        else:
            click.echo(f"Failed to fetch workflow '{workflow_id}': {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"Failed to fetch workflow '{workflow_id}': {e}", err=True)
        raise SystemExit(1)

    extracted = extract_workflow_fields(doc)
    click.echo(json.dumps(extracted, indent=2))


@click.command(name="workflow:get-prompt", no_args_is_help=True)
@click.argument("workflow_id")
def workflow_get_prompt(workflow_id: str):
    """Get the raw ComfyUI API prompt JSON for a workflow/document ID."""
    config = ensure_config()

    try:
        prompt = get_workflow(config, workflow_id)
    except SystemExit:
        raise
    except Exception as e:
        click.echo(f"Failed to fetch prompt for workflow '{workflow_id}': {e}", err=True)
        raise SystemExit(1)

    click.echo(json.dumps(prompt, indent=2))


@click.command(name="workflow:invoke-prompt", no_args_is_help=True)
@click.argument("prompt_file", type=click.Path(exists=True, dir_okay=False))
def workflow_invoke_prompt(prompt_file: str):
    """Invoke a ComfyUI API prompt JSON after setting SaveImage output prefixes."""
    config = ensure_config()

    try:
        with open(prompt_file, "r") as f:
            prompt = json.load(f)
    except json.JSONDecodeError as e:
        click.echo(f"Error parsing prompt JSON: {e}", err=True)
        raise SystemExit(1)

    if not isinstance(prompt, dict):
        click.echo("Prompt JSON must be a ComfyUI API prompt object.", err=True)
        raise SystemExit(1)

    now = datetime.now()
    prefix = f"{config.release_folder or 'release'}/{now.day}-{now.month}/img"
    changed = _set_save_image_prefix(prompt, prefix)
    if changed == 0:
        click.echo("No SaveImage nodes found in prompt JSON.", err=True)
        raise SystemExit(1)

    outputs = _queue_prompt_and_wait(prompt, config)
    click.echo(json.dumps(outputs, indent=2))

@click.command(name="workflow:lineage", no_args_is_help=True)
@click.argument("workflow_id")
def workflow_lineage(workflow_id: str):
    """
    Get a workflow's ancestral lineage by its ID.

    Outputs a JSON array containing objects with the `id` and `inputs` fields for each ancestor.

    \b
    ## Examples

    \b
    **1. Retrieve a specific workflow's lineage**
    ```bash
    op workflow:lineage 1e11af0abd47a164eb008b4caeab57af7a8f064151c6f24f82cfd290da6f6d09
    ```
    """
    config = ensure_config()
    api_url = config.kaleidescope_api_url

    lineage_url = f"{api_url}/workflow/{workflow_id}/lineage"

    try:
        response = requests.get(lineage_url)
        response.raise_for_status()
        lineage_data = response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            click.echo(f"Workflow '{workflow_id}' not found.", err=True)
        else:
            click.echo(f"Failed to fetch lineage for '{workflow_id}': {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"Failed to fetch lineage for '{workflow_id}': {e}", err=True)
        raise SystemExit(1)

    result = []
    for doc in lineage_data:
        result.append({
            "id": doc.get("id"),
            "inputs": doc.get("inputs", [])
        })

    click.echo(json.dumps(result, indent=2))
