from fastapi import APIRouter, Request, BackgroundTasks, Depends, HTTPException
from kaleidescope.config import Config, load_config
from kaleidescope.services import storage, comfy, convex

router = APIRouter()


def get_config():
    return load_config()


def get_convex_client(config: Config = Depends(get_config)):
    return convex.get_client(config.convex_url)


@router.get("/workflow/{id}")
async def get_workflow(id: str, config: Config = Depends(get_config)):
    data = storage.store_get_json(config, id, "png_prompt")
    if not data:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return data


@router.post("/workflow/{id}/invoke")
async def invoke(
    id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    config: Config = Depends(get_config),
    convex_client=Depends(get_convex_client),
):
    body = await request.json()

    # Create notification
    notification_id = convex.create_notification(
        convex_client,
        {
            "user_id": "test",  # Hardcoded in main.py
            "prompt_id": id,
            "workflow_id": "",
            "status": "pending",
            "payload": {"input": body, "output": None},
        },
    )

    if not notification_id:
        raise HTTPException(status_code=500, detail="Failed to create notification")

    # Get workflow data
    png_prompt = storage.store_get_json(config, id, "png_prompt")
    png_workflow = storage.store_get_json(config, id, "png_workflow")

    if not png_prompt or not png_workflow:
        # Update notification to error
        convex.update_notification(
            convex_client,
            notification_id,
            {"status": "ERROR", "payload": {"error": "Workflow data not found"}},
        )
        raise HTTPException(status_code=404, detail="Workflow data not found")

    background_tasks.add_task(
        comfy.invoke_workflow,
        config,
        convex_client,
        id,
        notification_id,
        body,
        png_prompt,
        png_workflow,
    )

    return {
        "message": "Workflow invocation started",
        "notification_id": notification_id,
        "status": "pending",
    }


@router.post("/workflow/{id}/invoke2")
async def invoke2(
    id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    config: Config = Depends(get_config),
    convex_client=Depends(get_convex_client),
):
    body = await request.json()

    # Create notification
    notification_id = convex.create_notification(
        convex_client,
        {
            "user_id": "test",  # Hardcoded in main.py
            "prompt_id": id,
            "workflow_id": "",
            "status": "pending",
            "payload": {"input": body, "output": None},
        },
    )

    if not notification_id:
        raise HTTPException(status_code=500, detail="Failed to create notification")

    # Get workflow data
    png_prompt = storage.store_get_json(config, id, "png_prompt")
    png_workflow = storage.store_get_json(config, id, "png_workflow")

    if not png_prompt or not png_workflow:
        # Update notification to error
        convex.update_notification(
            convex_client,
            notification_id,
            {"status": "ERROR", "payload": {"error": "Workflow data not found"}},
        )
        raise HTTPException(status_code=404, detail="Workflow data not found")

    background_tasks.add_task(
        comfy.invoke_workflow_v2,
        config,
        convex_client,
        id,
        notification_id,
        body,
        png_prompt,
        png_workflow,
    )

    return {
        "message": "Workflow invocation started",
        "notification_id": notification_id,
        "status": "pending",
    }
