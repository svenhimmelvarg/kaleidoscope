# Support Image Uploads for `op workflow:invoke`

## Overview
Currently, the `op workflow:invoke` command accepts a JSON payload for node overrides, but it lacks support for dynamically uploading local images. This issue extends the command to support image inputs dynamically. 

If the user provides a local file path (e.g., `./myimage.jpg`) as an image input in their JSON payload:
```bash
op workflow:invoke <workflow_id> input.json
```
Where `input.json` might look like:
```json
[
  {
    "id": "273",
    "image": "./myimage.jpg"
  }
]
```

The CLI should intercept the path, compute its hash, upload the image to Convex (mimicking the upload scheme in `@kaleidescope.ui/src/lib/Asset.svelte`), and replace the path in the JSON payload so the final input JSON resembles:
`"image": "<hash of /path/to/my/image>.(jpg|png)"`

## Architecture Guidelines
- Create appropriate pure functions in `op/workflow/core.py` (or a dedicated `op/workflow/image.py`) to handle file hashing, path detection, and JSON payload transformation to keep the core logic clean.
- Isolate side effects (reading the local file, uploading via HTTP/Convex, modifying the payload) within the CLI command logic.
- Follow the upload sequence established in the UI:
  1. Generate upload URL via Convex mutation (`assets:generateUploadUrl`).
  2. POST the image data to the generated URL.
  3. Retrieve the `storageId` and save the asset metadata via Convex mutation (`assets:save`).

## Data Structures & Pure Functions (`op/workflow/core.py`)
Add the following pure functions:
```python
def compute_file_hash(file_bytes: bytes) -> str:
    """Computes the hash (e.g., SHA256) of the file bytes."""
    ...

def construct_hashed_filename(original_path: str, file_hash: str) -> str:
    """Combines the file hash with the original extension (e.g., <hash>.jpg)."""
    ...

def is_local_image_path(value: str) -> bool:
    """Determines if a string value is a valid local path to an image file."""
    ...

def replace_image_paths_in_payload(payload: list[dict], replacements: dict[str, str]) -> list[dict]:
    """Returns a new payload with local paths replaced by the final hashed filenames."""
    ...
```

## Command Logic (`op/workflow/cli.py`)
- Parse the input JSON payload.
- Scan the payload for any fields containing local image paths (using `is_local_image_path`).
- For each local image path found:
  - Read the file bytes and compute its hash (`compute_file_hash`).
  - Generate a new filename: `<hash>.<ext>` (`construct_hashed_filename`).
  - Use the Convex client to fetch an upload URL (`assets:generateUploadUrl`).
  - Upload the file to the URL via `requests.post`.
  - Call the `assets:save` mutation with the returned `storageId` and the new hashed filename.
  - Map the local path to the required final input format: `"<hash>.<ext>"`.
- Rewrite the local paths in the payload using `replace_image_paths_in_payload`.
- Proceed with the existing workflow invocation (`requests.post(invoke_url, json=updated_payload)`).
- Update the help text of the `workflow:invoke` command to include formatted examples illustrating text input overrides and local image uploads to help guide agents.

## TODO Checklist
- [x] Implement pure functions for hashing and payload manipulation in `op/workflow/core.py`.
- [x] Ensure Convex upload logic is available using the Python client (`kaleidescope/services/convex.py`).
- [x] Update `op/workflow/cli.py` to intercept local image paths, trigger uploads, and rewrite the payload.
- [x] Test uploading an image and verifying the final injected JSON matches `"image": "<hash>.<ext>"`.
- [x] Add descriptive help text to `op/workflow/cli.py` containing formatted markdown examples.
