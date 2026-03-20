import json
import time
import click
import requests
import logging

from op.config import ensure_config
from op.workflow.core import build_invoke_url, build_notification_url, extract_outputs

logger = logging.getLogger(__name__)


@click.command(name="workflow:invoke")
@click.argument("workflow_id")
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False))
def workflow_invoke(workflow_id: str, input_file: str):
    """
    Invoke a ComfyUI workflow using the provided workflow ID and input JSON file.
    The input JSON file should contain a list of node overrides.
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
