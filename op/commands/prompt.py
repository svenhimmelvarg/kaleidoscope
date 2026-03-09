import json
import click
import logging

from op.config import ensure_config
from op.utils.api import get_workflow, invoke_workflow
from op.utils.banner import display_error, display_info, display_success

logger = logging.getLogger(__name__)


@click.command()
@click.argument("workflow_id")
@click.argument("prompt_text", required=False)
@click.option("--node-id", "-n", help="Specific node ID to update")
@click.option("--wait", "-w", is_flag=True, help="Wait for workflow to complete")
def prompt(workflow_id, prompt_text, node_id, wait):
    logger.info(f"Processing prompt for workflow: {workflow_id}")

    config = ensure_config()

    try:
        workflow_data = get_workflow(config, workflow_id)
    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch workflow: {e}")
        display_error(f"Failed to fetch workflow: {e}")
        raise SystemExit(1)

    text_inputs = find_text_inputs(workflow_data)

    if len(text_inputs) == 0:
        display_error("No text inputs found in workflow")
        raise SystemExit(1)

    if len(text_inputs) > 1 and not node_id and not prompt_text:
        display_info("Multiple text inputs found:")
        for node in text_inputs:
            print(f"  Node {node['id']}: {node.get('current_value', 'empty')[:50]}...")
        print()
        print(f'Usage: op prompt {workflow_id} --node-id <id> "<prompt text>"')
        return

    if not node_id:
        node_id = text_inputs[0]["id"]

    if not prompt_text:
        display_error("No prompt text provided")
        print(f'Usage: op prompt {workflow_id} "<prompt text>"')
        raise SystemExit(1)

    inputs = [{"id": node_id, "text": prompt_text}]

    try:
        result = invoke_workflow(config, workflow_id, inputs)
        print(json.dumps(result, indent=2))

        if wait and "notification_id" in result:
            display_info("Waiting for workflow to complete...")
    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"Failed to invoke workflow: {e}")
        display_error(f"Failed to invoke workflow: {e}")
        raise SystemExit(1)


def find_text_inputs(workflow_data):
    inputs = []

    if isinstance(workflow_data, dict):
        for node_id, node_data in workflow_data.items():
            if isinstance(node_data, dict):
                class_type = node_data.get("class_type", "")
                if "CLIPTextEncode" in class_type or "text" in class_type.lower():
                    inputs_data = node_data.get("inputs", {})
                    current_text = inputs_data.get("text", "")
                    inputs.append(
                        {"id": node_id, "type": class_type, "current_value": current_text}
                    )

    return inputs
