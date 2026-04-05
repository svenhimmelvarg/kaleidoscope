import re
import meilisearch
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


@router.get("/workflow/{id}/lineage")
async def get_workflow_lineage(id: str, config: Config = Depends(get_config)):
    host = config.meilisearch_host
    if not host.startswith("http"):
        host = f"http://{host}"

    client = meilisearch.Client(host, "password")

    results = []
    current_id = id
    visited = set()
    regex = re.compile(r"([a-f0-9]{32,64})\.(?:png|jpg|jpeg|mp4|webp)$", re.IGNORECASE)

    while current_id and current_id not in visited:
        visited.add(current_id)
        try:
            doc = client.index(config.index_name).get_document(current_id)
            if not doc:
                break
            results.append(doc)

            next_id = None
            inputs = doc.get("inputs", [])
            for i in inputs:
                if isinstance(i, dict) and i.get("type", "").strip() == "image":
                    val = i.get("value", "")
                    match = regex.search(val)
                    if match:
                        next_id = match.group(1)
                        break
            current_id = next_id
        except Exception as e:
            # Document might not exist or Meilisearch error
            break

    return results


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
