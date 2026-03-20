import json
import hashlib
import os
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass(frozen=True)
class WorkflowOutput:
    file_path: str
    url: str

    def to_dict(self) -> Dict[str, str]:
        return {"file_path": self.file_path, "url": self.url}


def build_invoke_url(api_url: str, workflow_id: str) -> str:
    return f"{api_url.rstrip('/')}/workflow/{workflow_id}/invoke"


def build_notification_url(api_url: str, notification_id: str) -> str:
    return f"{api_url.rstrip('/')}/notifications/{notification_id}"


def construct_file_path(base_path: str, uri: str) -> str:
    """
    Constructs the absolute file path by replacing the prefix from the URI.
    URI typically looks like /images/{instance_name}/output/release/filename.png
    We map this to {base_path}/output/release/filename.png
    """
    parts = uri.split("/")
    # typically ['', 'images', '{instance_name}', 'output', ...]
    # we want to reconstruct everything from 'output' onwards
    if "output" in parts:
        output_idx = parts.index("output")
        rel_path = "/".join(parts[output_idx:])
        return f"{base_path.rstrip('/')}/{rel_path}"
    return uri


def construct_asset_url(ui_url: str, uri: str) -> str:
    return f"{ui_url.rstrip('/')}{uri}"


def extract_outputs(payload: Dict[str, Any], base_path: str, ui_url: str) -> List[WorkflowOutput]:
    """
    Maps the completed notification payload to a list of WorkflowOutput records.
    """
    outputs = []
    output_data = payload.get("output", {})
    images = output_data.get("images", [])

    for img in images:
        uri = img.get("uri")
        if uri:
            file_path = construct_file_path(base_path, uri)
            url = construct_asset_url(ui_url, uri)
            outputs.append(WorkflowOutput(file_path=file_path, url=url))

    return outputs


def compute_file_hash(file_bytes: bytes) -> str:
    """Computes the SHA256 hash of the file bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


def construct_hashed_filename(original_path: str, file_hash: str) -> str:
    """Combines the file hash with the original extension (e.g., <hash>.jpg)."""
    _, ext = os.path.splitext(original_path)
    return f"{file_hash}{ext}"


def is_local_image_path(value: str) -> bool:
    """Determines if a string value is a valid local path to an image file."""
    if not isinstance(value, str):
        return False
    # Check if it looks like a local path (starts with . or / or has typical image extension)
    lower_val = value.lower()
    if lower_val.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff")):
        # Must actually exist to be treated as a local path override
        if os.path.isfile(value):
            return True
    return False


def replace_image_paths_in_payload(
    payload: List[Dict[str, Any]], replacements: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Returns a new payload with local paths replaced by the final hashed filenames."""
    new_payload = []
    for node in payload:
        new_node = dict(node)
        for key, val in new_node.items():
            if isinstance(val, str) and val in replacements:
                new_node[key] = replacements[val]
        new_payload.append(new_node)
    return new_payload
