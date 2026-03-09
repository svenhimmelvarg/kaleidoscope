import os
import json
import shutil
import logging
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, cast
from jinja2 import Template
from urllib.parse import urlparse

from kaleidescope.config import Config
from kaleidescope.services import git_ops, convex
from convex import ConvexClient
from op.config import get_config_value, get_env_path

logger = logging.getLogger(__name__)

GITHUB_USER = get_config_value("GITHUB_USER")
GITHUB_API_KEY = get_config_value("GITHUB_API_KEY")
GITHUB_REPO_URL = get_config_value("GITHUB_REPO_URL")

REPO_URL = GITHUB_REPO_URL or ""
BRANCH = get_config_value("GITHUB_BRANCH") or "dev"

WORKFLOW_README_TEMPLATE = Template("""![](./render.png)

{% if resolution_info %}
{{ resolution_info }}

{% endif %}
{% if text_inputs %}
{% for text_inp in text_inputs -%}
> {{ text_inp | replace('\n', '\n> ') }}

{% endfor %}
{% endif %}

{% if examples %}
## Examples

{% for example in examples %}
![](./examples/{{ example.image }})

> {{ example.text | replace('\n', '\n> ') }}

{% endfor %}
{% endif %}
""")


MAIN_README_TEMPLATE = Template("""# Kaleidescope Workflows

|   |   |   |
|---|---|---|
{% for row in workflows|batch(3, None) -%}
| {% for item in row %}{% if item %}<a href="./{{ item.id }}/README.md"><img src="./{{ item.id }}/render.png" width="512" height="512" /></a>{% else %} {% endif %} | {% endfor %}
{% endfor %}
""")


def _get_meilisearch_cache_path(config: Config, id: str, key: str) -> str:
    return os.path.join(config.data_dir, "output", config.index_name, id, key)


def _read_meilisearch_data(config: Config, id: str, key: str) -> Optional[Dict[str, Any]]:
    path = _get_meilisearch_cache_path(config, id, key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading meilisearch data from {path}: {e}")
        return None


def get_text_prompts_from_inputs(inputs: List[Dict[str, Any]]) -> str:
    text_prompts = []
    for inp in inputs:
        if "text" in inp:
            text_prompts.append(str(inp["text"]))
    return " | ".join(text_prompts).replace("\n", " ")


def prepare(
    config: Config,
    convex_client: ConvexClient,
    workflow_id: str,
    overrides_content: List[Dict[str, Any]],
    staging_dir: str,
) -> Tuple[int, List[str]]:
    """
    Sets up the staging directory with README.md, render.png, overrides.json, and examples.
    Returns the number of examples found.
    """
    meilisearch_path = os.path.join(
        config.data_dir, "output", config.index_name, workflow_id, "milliesearch_write"
    )

    if not os.path.exists(meilisearch_path):
        raise ValueError(f"milliesearch_write not found at {meilisearch_path}")

    with open(meilisearch_path, "r") as f:
        doc_data = json.load(f)

    examples_dir = os.path.join(staging_dir, "examples")
    os.makedirs(staging_dir, exist_ok=True)
    os.makedirs(examples_dir, exist_ok=True)

    overrides_path = os.path.join(staging_dir, "overrides.json")
    with open(overrides_path, "w") as f:
        json.dump(overrides_content, f, indent=2)

    image_url = doc_data.get("image_url")
    if not image_url:
        raise ValueError("image_url not found in meilisearch_write data")

    full_image_path = os.path.join(config.comfyui_instance_base_path, image_url)
    if not os.path.exists(full_image_path):
        raise ValueError(f"Image file not found at {full_image_path}")

    main_image_dest = os.path.join(staging_dir, "render.png")
    shutil.copy2(full_image_path, main_image_dest)

    text_docs = doc_data.get("text", [])
    text_inputs = []
    for txt in text_docs:
        value = txt.get("value", "")
        if value:
            text_inputs.append(str(value))

    # Extract resolution and aspect ratio
    resolution_info = ""
    aspect_ratio = ""
    for inp in doc_data.get("inputs", []):
        if inp.get("type") == "res.aspectratio":
            val = str(inp.get("value", ""))
            aspect_ratio = val.split(" ")[0] if val else ""
            break

    resolution = doc_data.get("resolution", "")
    if not resolution and doc_data.get("width") and doc_data.get("height"):
        resolution = f"{doc_data.get('width')}x{doc_data.get('height')}"

    res_parts = []
    if aspect_ratio:
        res_parts.append(f"**{aspect_ratio}**")
    if resolution:
        res_parts.append(resolution)

    # Check for prompt.json and workflow.json
    source_dir = os.path.join(config.data_dir, "output", config.index_name, workflow_id)

    png_prompt_src = os.path.join(source_dir, "png_prompt.json")
    if os.path.exists(png_prompt_src):
        shutil.copy2(png_prompt_src, os.path.join(staging_dir, "prompt.json"))
        res_parts.append("[prompt.json](./prompt.json)")

    png_workflow_src = os.path.join(source_dir, "png_workflow.json")
    if os.path.exists(png_workflow_src):
        shutil.copy2(png_workflow_src, os.path.join(staging_dir, "workflow.json"))
        res_parts.append("[workflow.json](./workflow.json)")

    if res_parts:
        resolution_info = " | ".join(res_parts)

    logger.info(f"Fetching notifications for prompt_id={workflow_id}")
    notifications = convex.get_notifications_by_prompt(convex_client, workflow_id)

    examples_data = []
    child_ids = []

    if notifications:
        for notification in notifications:
            if len(examples_data) >= 3:
                break

            notification_id = notification.get("_id")
            if not notification_id:
                continue

            notification_payload = notification.get("payload", {})
            input_data = notification_payload.get("input", [])
            output_data = notification_payload.get("output", {})

            # Write child overrides JSON
            child_overrides_path = os.path.join(examples_dir, f"{notification_id}.json")
            with open(child_overrides_path, "w") as f:
                json.dump(input_data, f, indent=2)

            first_image = None
            child_text_inputs = []

            if output_data and "images" in output_data:
                images = output_data.get("images", [])
                for img in images:
                    img_id = img.get("_id")
                    if not img_id:
                        continue

                    img_data = _read_meilisearch_data(config, img_id, "milliesearch_write")
                    if not img_data:
                        continue

                    text_docs = img_data.get("text", [])
                    for txt in text_docs:
                        val = txt.get("value", "")
                        if val:
                            child_text_inputs.append(str(val))

                    full_img_path = os.path.join(
                        config.comfyui_instance_base_path, img_data.get("image_url", "")
                    )

                    if img_data.get("image_url") and os.path.exists(full_img_path):
                        filename = f"{notification_id}.png"
                        dest_path = os.path.join(examples_dir, filename)
                        shutil.copy2(full_img_path, dest_path)
                        first_image = filename
                        break  # Only take the first valid image

            if first_image and child_text_inputs:
                examples_data.append({"image": first_image, "text": "\n\n".join(child_text_inputs)})
                child_ids.append(notification_id)

    readme_content = WORKFLOW_README_TEMPLATE.render(
        text_inputs=text_inputs,
        resolution_info=resolution_info,
        examples=examples_data,
    )

    readme_path = os.path.join(staging_dir, "README.md")
    with open(readme_path, "w") as f:
        f.write(readme_content)

    return len(examples_data), child_ids


def commit_gh(
    workflow_id: str, staging_dir: str, examples_count: int, child_ids: List[str]
) -> Dict[str, Any]:
    """
    Commits the staging directory to the GitHub repository.
    Assumes staging_dir contains the files that need to be committed in `repo_dir / workflow_id`.
    """
    repo = None
    try:
        logger.info("Preparing git repository")
        repo = git_ops.prepare(REPO_URL, branch=BRANCH)
        git_ops.clone(repo)
        repo_dir = repo.path

        # Move the staging directory contents to the git repo workflow folder
        dest_dir = os.path.join(repo_dir, workflow_id)
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)

        # Copy everything over from staging_dir to the git repository
        shutil.copytree(staging_dir, dest_dir)

        logger.debug(f"Copied staging directory {staging_dir} to git repo path {dest_dir}")

        # Update index.json
        index_path = os.path.join(repo_dir, "index.json")
        index_data: Dict[str, Any] = {"metadata": {}}
        if os.path.exists(index_path):
            try:
                with open(index_path, "r") as f_idx:
                    index_data = cast(Dict[str, Any], json.load(f_idx))
            except Exception as e:
                logger.warning(f"Failed to read existing index.json: {e}")

        # Ensure metadata exists
        if "metadata" not in index_data:
            index_data["metadata"] = {}

        # Update last_updated_at
        index_data["metadata"]["last_updated_at"] = datetime.now(timezone.utc).isoformat()

        # Add/update workflow_id -> child_ids
        index_data[workflow_id] = child_ids

        with open(index_path, "w") as f_idx:
            json.dump(index_data, f_idx, indent=2)

        logger.debug(f"Updated index.json with workflow {workflow_id}")

        # Render and write root README.md
        workflows = [{"id": k} for k in index_data.keys() if k != "metadata"]
        main_readme_content = MAIN_README_TEMPLATE.render(workflows=workflows)
        main_readme_path = os.path.join(repo_dir, "README.md")
        with open(main_readme_path, "w") as f_readme:
            f_readme.write(main_readme_content)

        logger.debug("Updated root README.md")

        commit_message = (
            f"Add workflow {workflow_id} with {examples_count} examples"
            if examples_count > 0
            else f"Add workflow {workflow_id}"
        )

        git_ops.commit(repo, commit_message)

        # Authenticate before pushing
        if not GITHUB_USER or not GITHUB_API_KEY or not GITHUB_REPO_URL:
            raise ValueError(
                "Missing GitHub credentials. Required: GITHUB_USER, GITHUB_API_KEY and GITHUB_REPO_URL in .env"
            )

        parsed = urlparse(GITHUB_REPO_URL)
        auth_remote = f"https://{GITHUB_USER}:{GITHUB_API_KEY}@{parsed.netloc}{parsed.path}"

        subprocess.run(
            ["git", "remote", "set-url", "origin", auth_remote],
            cwd=repo.path,
            check=True,
            capture_output=True,
        )
        logger.info("Updated remote URL with authentication")

        git_ops.publish(repo)
        git_ops.gc(repo)

        logger.info(f"Successfully published workflow {workflow_id}")

        return {
            "status": "success",
            "message": f"Successfully published workflow {workflow_id}",
            "repository": REPO_URL,
            "branch": BRANCH,
            "examples_count": examples_count,
        }

    except Exception as e:
        if repo:
            git_ops.gc(repo)
        raise e


def publish_workflow(
    config: Config,
    convex_client: ConvexClient,
    workflow_id: str,
    overrides_content: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Main entrypoint for publishing a workflow to GitHub.
    """
    logger.info(f"Starting publish for workflow id={workflow_id}")

    missing_gh_keys = []
    if not GITHUB_USER:
        missing_gh_keys.append("GITHUB_USER")
    if not GITHUB_API_KEY:
        missing_gh_keys.append("GITHUB_API_KEY")
    if not GITHUB_REPO_URL:
        missing_gh_keys.append("GITHUB_REPO_URL")

    if missing_gh_keys:
        env_name = get_env_path().name
        error_msg = f"Missing GitHub configuration in {env_name}: {', '.join(missing_gh_keys)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}

    staging_dir = f"/tmp/{workflow_id}_gh_stage"

    try:
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)

        examples_count, child_ids = prepare(
            config, convex_client, workflow_id, overrides_content, staging_dir
        )
        return commit_gh(workflow_id, staging_dir, examples_count, child_ids)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Failed to publish workflow: {e}")
        import traceback

        return {
            "error": f"Failed to publish workflow: {str(e)}",
            "details": traceback.format_exc(),
        }
