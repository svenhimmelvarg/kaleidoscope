import requests
import logging

logger = logging.getLogger(__name__)


def fetch_workflow_from_meilisearch(
    base_url: str, index_name: str, doc_id: str, api_key: str = "password"
) -> dict:
    """Fetches a single document by ID from the Meilisearch index."""
    if not base_url.startswith("http"):
        base_url = f"http://{base_url}"

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    url = f"{base_url}/indexes/{index_name}/documents/{doc_id}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching workflow {doc_id} from Meilisearch: {e}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Response: {e.response.text}")
        raise


def extract_workflow_fields(doc: dict) -> dict:
    """Extracts only the 'id', 'inputs', and 'text' fields from the Meilisearch document."""
    return {"id": doc.get("id"), "inputs": doc.get("inputs", []), "text": doc.get("text", [])}
