from fastapi import APIRouter, Request, Depends, HTTPException
from kaleidescope.config import Config, load_config
from kaleidescope.services import publish, convex, publish_hf

router = APIRouter()


def get_config():
    return load_config()


def get_convex_client(config: Config = Depends(get_config)):
    return convex.get_client(config.convex_url)


@router.post("/publish-gh/{id}")
async def publish_workflow_gh_endpoint(
    id: str,
    request: Request,
    config: Config = Depends(get_config),
    convex_client=Depends(get_convex_client),
):
    body = await request.json()

    overrides_content = body if isinstance(body, list) else []

    result = publish.publish_workflow(
        config=config,
        convex_client=convex_client,
        workflow_id=id,
        overrides_content=overrides_content,
    )

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.post("/publish-hf/{id}")
async def publish_workflow_hf_endpoint(
    id: str,
    request: Request,
    config: Config = Depends(get_config),
    convex_client=Depends(get_convex_client),
):
    body = await request.json()

    overrides_content = body if isinstance(body, list) else []

    result = publish_hf.publish_workflow_hf(
        config=config,
        convex_client=convex_client,
        workflow_id=id,
        overrides_content=overrides_content,
    )

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.post("/publish/{id}")
async def publish_workflow_endpoint(
    id: str,
    request: Request,
    config: Config = Depends(get_config),
    convex_client=Depends(get_convex_client),
):
    body = await request.json()

    overrides_content = body if isinstance(body, list) else []

    gh_result = publish.publish_workflow(
        config=config,
        convex_client=convex_client,
        workflow_id=id,
        overrides_content=overrides_content,
    )

    hf_result = publish_hf.publish_workflow_hf(
        config=config,
        convex_client=convex_client,
        workflow_id=id,
        overrides_content=overrides_content,
    )

    return [gh_result, hf_result]
