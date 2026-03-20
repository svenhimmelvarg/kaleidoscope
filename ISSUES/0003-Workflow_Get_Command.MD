# Implement `op workflow:get` Command

## Overview
Currently, there is no command to retrieve a specific indexed workflow directly from Meilisearch via the CLI. This issue introduces a new CLI command `op workflow:get <workflow_id>`, which queries Meilisearch for a given workflow ID and extracts specific fields (`id`, `inputs`, and `text`), formatting them as JSON output.

If the user provides a workflow ID:
```bash
op workflow:get 1e11af0abd47a164eb008b4caeab57af7a8f064151c6f24f82cfd290da6f6d09
```

The CLI will fetch the corresponding document from Meilisearch and print a JSON object resembling:
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

## Architecture Guidelines
- Create appropriate pure functions in `op/workflow/meilisearch.py` to handle the extraction logic and Meilisearch HTTP interaction, keeping the core CLI logic clean.
- Ensure the command seamlessly retrieves the `meilisearch_host` and `index_name` from the shared `op.config.ensure_config()` context.
- Output should be formatted as clean JSON to standard out (`stdout`), allowing it to be piped or consumed by other CLI tools and agents.

## Data Structures & Pure Functions (`op/workflow/meilisearch.py`)
Add the following pure functions:
```python
import requests
import logging

logger = logging.getLogger(__name__)

def fetch_workflow_from_meilisearch(base_url: str, index_name: str, doc_id: str, api_key: str = "password") -> dict:
    """Fetches a single document by ID from the Meilisearch index."""
    ...

def extract_workflow_fields(doc: dict) -> dict:
    """Extracts only the 'id', 'inputs', and 'text' fields from the Meilisearch document."""
    return {
        "id": doc.get("id"),
        "inputs": doc.get("inputs", []),
        "text": doc.get("text", [])
    }
```

## Command Logic (`op/workflow/cli.py`)
- Create a new `@click.command(name="workflow:get")` accepting `workflow_id` as an argument.
- Read configuration via `ensure_config()` to get `meilisearch_host` and `index_name`.
- Normalize the `meilisearch_host` to ensure it starts with `http://`.
- Fetch the document from Meilisearch using `fetch_workflow_from_meilisearch`.
- Handle any HTTP errors (e.g., 404 if the document doesn't exist) and print a helpful error message to stderr.
- Pass the document to `extract_workflow_fields` to pull out `id`, `inputs`, and `text`.
- Output the resulting dictionary as a JSON string (`json.dumps(..., indent=2)`) using `click.echo`.

## Registration Logic
- Export the `workflow_get` command in `op/workflow/__init__.py`.
- Register the command globally by appending `cli.add_command(workflow_get)` in `op/cli.py`.

## TODO Checklist
- [x] Add `fetch_workflow_from_meilisearch` and `extract_workflow_fields` helper functions to `op/workflow/meilisearch.py`.
- [x] Implement `workflow_get` command in `op/workflow/cli.py` with proper error handling.
- [x] Add descriptive help text to `op/workflow/cli.py` containing formatted markdown examples.
- [x] Register `workflow_get` in `op/workflow/__init__.py` and `op/cli.py`.
- [x] Test the command with a known workflow ID to verify valid JSON output containing only the desired fields.
- [x] Test error handling for invalid or missing workflow IDs.
