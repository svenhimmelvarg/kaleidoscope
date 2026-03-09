from convex import ConvexClient
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


def get_client(url: str) -> ConvexClient:
    return ConvexClient(url)


def get_notification(client: ConvexClient, notification_id: str) -> Optional[Dict[str, Any]]:
    try:
        return client.query("notifications:get", {"notificationId": notification_id})
    except Exception as e:
        logger.error(f"Error fetching notification {notification_id}: {e}")
        return None


def get_notifications_by_prompt(client: ConvexClient, prompt_id: str) -> List[Dict[str, Any]]:
    try:
        notifications = client.query("notifications:getByPrompt", {"prompt_id": prompt_id})
        return notifications or []
    except Exception as e:
        logger.error(f"Error fetching notifications for prompt {prompt_id}: {e}")
        return []


def create_notification(client: ConvexClient, data: Dict[str, Any]) -> Optional[str]:
    try:
        return client.mutation("notifications:create", data)
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        return None


def update_notification(client: ConvexClient, notification_id: str, data: Dict[str, Any]) -> bool:
    try:
        # Merge id into data for the mutation if not present, though mutation likely expects id in args
        # Based on main.py: convex_client.mutation("notifications:update", {"id": notification_id, ...})
        payload = {"id": notification_id, **data}
        client.mutation("notifications:update", payload)
        return True
    except Exception as e:
        logger.error(f"Error updating notification {notification_id}: {e}")
        return False
