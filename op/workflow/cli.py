import json
import time
import os
import mimetypes
import click
import requests
import logging

from op.config import ensure_config
from op.workflow.core import (
    build_invoke_url,
    build_notification_url,
    extract_outputs,
    is_local_image_path,
    compute_file_hash,
    construct_hashed_filename,
    replace_image_paths_in_payload,
)
from kaleidescope.services.convex import get_client, generate_upload_url, save_asset

logger = logging.getLogger(__name__)


@click.command(name="workflow:invoke")
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

    invoke_url = build_invoke_url(api_url, workflow_id)

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
