from typing import Any, Optional
import logging

import requests

from op.config import Config


logger = logging.getLogger(__name__)


def api_get(config: Config, endpoint: str, params: Optional[dict] = None) -> dict[str, Any]:
    url = f"{config.kaleidescope_api_url}/{endpoint.lstrip('/')}"
    logger.debug(f"GET {url}")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        logger.debug(f"GET {url} - {response.status_code}")
        return response.json()
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to kaleidescope API at {config.kaleidescope_api_url}")
        print(f"Error: Cannot connect to kaleidescope API at {config.kaleidescope_api_url}")
        print("Make sure the server is running with: op serve kaleidescope")
        raise SystemExit(1)
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out: GET {url}")
        print("Error: Request timed out")
        raise SystemExit(1)
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        print(f"Error: API request failed: {e}")
        raise SystemExit(1)


def api_post(config: Config, endpoint: str, data: Optional[dict | list] = None) -> dict[str, Any]:
    url = f"{config.kaleidescope_api_url}/{endpoint.lstrip('/')}"
    logger.debug(f"POST {url}")

    try:
        response = requests.post(
            url, json=data, headers={"Content-Type": "application/json"}, timeout=30
        )
        response.raise_for_status()
        logger.debug(f"POST {url} - {response.status_code}")
        return response.json()
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to kaleidescope API at {config.kaleidescope_api_url}")
        print(f"Error: Cannot connect to kaleidescope API at {config.kaleidescope_api_url}")
        print("Make sure the server is running with: op serve kaleidescope")
        raise SystemExit(1)
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out: POST {url}")
        print("Error: Request timed out")
        raise SystemExit(1)
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        print(f"Error: API request failed: {e}")
        raise SystemExit(1)


def get_workflow(config: Config, workflow_id: str) -> dict[str, Any]:
    logger.info(f"Fetching workflow: {workflow_id}")
    return api_get(config, f"/workflow/{workflow_id}")


def invoke_workflow(config: Config, workflow_id: str, inputs: list[dict]) -> dict[str, Any]:
    logger.info(f"Invoking workflow: {workflow_id}")
    return api_post(config, f"/workflow/{workflow_id}/invoke", inputs)


def get_notification(config: Config, notification_id: str) -> dict[str, Any]:
    logger.info(f"Fetching notification: {notification_id}")
    return api_get(config, f"/notifications/{notification_id}")
