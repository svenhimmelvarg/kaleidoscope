import os
import shutil
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, cast
from huggingface_hub import login, upload_folder, hf_hub_download
from huggingface_hub.errors import RepositoryNotFoundError, EntryNotFoundError

from kaleidescope.config import Config
from convex import ConvexClient
from op.config import get_config_value, get_env_path
from kaleidescope.services.publish import prepare, MAIN_README_TEMPLATE

logger = logging.getLogger(__name__)

HF_TOKEN = get_config_value("HF_TOKEN")
HF_REPO_NAME = get_config_value("HF_REPO_NAME")
HF_USER = get_config_value("HF_USER")


def commit_hf(
    workflow_id: str, upload_staging_dir: str, examples_count: int, child_ids: List[str]
) -> Dict[str, Any]:
    """
    Commits the staging directory to HuggingFace hub.
    Assumes all files in upload_staging_dir are ready to be uploaded to the root of the repo.
    """
    repo_id = f"{HF_USER}/{HF_REPO_NAME}"
    login(token=HF_TOKEN)

    logger.info(f"Downloading existing index.json from HF repo {repo_id}...")
    index_data: Dict[str, Any] = {"metadata": {}}
    try:
        index_path = hf_hub_download(repo_id=repo_id, repo_type="model", filename="index.json")
        with open(index_path, "r") as f_idx:
            index_data = cast(Dict[str, Any], json.load(f_idx))
    except (RepositoryNotFoundError, EntryNotFoundError):
        logger.warning("No existing index.json found on HuggingFace Hub. Creating a new one.")
    except Exception as e:
        logger.warning(f"Failed to read existing index.json from HuggingFace Hub: {e}")

    # Ensure metadata exists
    if "metadata" not in index_data:
        index_data["metadata"] = {}

    # Update last_updated_at
    index_data["metadata"]["last_updated_at"] = datetime.now(timezone.utc).isoformat()

    # Add/update workflow_id -> child_ids
    index_data[workflow_id] = child_ids

    local_index_path = os.path.join(upload_staging_dir, "index.json")
    with open(local_index_path, "w") as f_idx:
        json.dump(index_data, f_idx, indent=2)

    logger.debug(f"Updated index.json with workflow {workflow_id}")

    # Render and write root README.md
    workflows = [{"id": k} for k in index_data.keys() if k != "metadata"]
    main_readme_content = MAIN_README_TEMPLATE.render(workflows=workflows)
    main_readme_path = os.path.join(upload_staging_dir, "README.md")
    with open(main_readme_path, "w") as f_readme:
        f_readme.write(main_readme_content)

    logger.debug("Updated root README.md")

    logger.info(f"Uploading to HF repo {repo_id}...")
    commit_message = (
        f"Add workflow {workflow_id} with {examples_count} examples"
        if examples_count > 0
        else f"Add workflow {workflow_id}"
    )

    upload_folder(
        folder_path=upload_staging_dir,
        repo_id=repo_id,
        repo_type="model",
        commit_message=commit_message,
    )

    logger.info(f"Successfully published workflow {workflow_id} to HuggingFace")

    return {
        "status": "success",
        "message": f"Successfully published workflow {workflow_id} to HuggingFace",
        "repository": f"https://huggingface.co/{repo_id}",
        "branch": "main",
        "examples_count": examples_count,
    }


def publish_workflow_hf(
    config: Config,
    convex_client: ConvexClient,
    workflow_id: str,
    overrides_content: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Main entrypoint for publishing a workflow to HuggingFace.
    """
    logger.info(f"Starting HF publish for workflow id={workflow_id}")

    missing_hf_keys = []
    if not HF_TOKEN:
        missing_hf_keys.append("HF_TOKEN")
    if not HF_REPO_NAME:
        missing_hf_keys.append("HF_REPO_NAME")
    if not HF_USER:
        missing_hf_keys.append("HF_USER")

    if missing_hf_keys:
        env_name = get_env_path().name
        error_msg = f"Missing HuggingFace configuration in {env_name}: {', '.join(missing_hf_keys)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}

    try:
        # For HuggingFace, we want the files uploaded to `/{workflow_id}/...` in the repo.
        # So we create a staging directory that contains a subfolder named `workflow_id`.
        # When `upload_folder` is called on the root staging directory, it preserves the `workflow_id/` folder structure.
        upload_staging_dir = f"/tmp/{workflow_id}_hf_upload"
        if os.path.exists(upload_staging_dir):
            shutil.rmtree(upload_staging_dir)
        os.makedirs(upload_staging_dir, exist_ok=True)

        workflow_staging_dir = os.path.join(upload_staging_dir, workflow_id)

        examples_count, child_ids = prepare(
            config, convex_client, workflow_id, overrides_content, workflow_staging_dir
        )
        return commit_hf(workflow_id, upload_staging_dir, examples_count, child_ids)

    except Exception as e:
        logger.error(f"Failed to publish workflow to HF: {e}")
        import traceback

        return {
            "error": f"Failed to publish workflow to HF: {str(e)}",
            "details": traceback.format_exc(),
        }
