from fastapi import APIRouter, HTTPException, Depends
from kaleidescope.config import Config, load_config
from kaleidescope.services import convex, comfy

router = APIRouter()


def get_config():
    return load_config()


def get_convex_client(config: Config = Depends(get_config)):
    return convex.get_client(config.convex_url)


@router.get("/notifications/{id}")
async def get_notification(id: str, client=Depends(get_convex_client)):
    notification = convex.get_notification(client, id)
    if notification is None:
        # In main.py it returns {"error": ...} dict, but 404 is more RESTful
        # sticking to main.py behavior slightly but wrapped in return
        return {"error": "Notification not found"}
    return notification


@router.post("/cancel/{notification_id}")
async def cancel_notification(
    notification_id: str, config: Config = Depends(get_config), client=Depends(get_convex_client)
):
    notification = convex.get_notification(client, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    workflow_id = notification.get("workflow_id")
    if not workflow_id:
        raise HTTPException(status_code=400, detail="No workflow_id associated")

    # Assuming ComfyUI is at default location or derived from config
    # Since config has host/port for THIS app, I'll use the hardcoded/default one for Comfy as per my earlier decision
    comfy_url = "http://127.0.0.1:8188"

    success = comfy.cancel_workflow(comfy_url, workflow_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to cancel ComfyUI task")

    convex.update_notification(client, notification_id, {"status": "cancelled"})

    return {"status": "cancelled", "notification_id": notification_id}
