from fastapi import APIRouter, Form, HTTPException, Depends, Response
from kaleidescope.config import Config, load_config
from kaleidescope.services import image
import json
import os

router = APIRouter()


def get_config():
    return load_config()


@router.post("/download/{id}")
async def download_jpg(id: str, doc: str = Form(...), config: Config = Depends(get_config)):
    try:
        doc_data = json.loads(doc)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in doc parameter")

    source_path_rel = doc_data.get("image_url")
    if not source_path_rel:
        raise HTTPException(status_code=400, detail="No image_url found in doc")

    source_path = os.path.join(config.comfyui_instance_base_path, source_path_rel)

    content = image.prepare_jpg_download(source_path, doc_data)
    if not content:
        raise HTTPException(status_code=404, detail="Image file not found or error processing")

    return Response(
        content=content,
        media_type="image/jpeg",
        headers={"Content-Disposition": f"attachment; filename={id}.jpg"},
    )


@router.post("/download/png/{id}")
async def download_png(id: str, doc: str = Form(...), config: Config = Depends(get_config)):
    try:
        doc_data = json.loads(doc)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in doc parameter")

    source_path_rel = doc_data.get("image_url")
    if not source_path_rel:
        raise HTTPException(status_code=400, detail="No image_url found in doc")

    source_path = os.path.join(config.comfyui_instance_base_path, source_path_rel)

    content = image.prepare_png_download(source_path, doc_data)
    if not content:
        raise HTTPException(status_code=404, detail="Image file not found or error processing")

    return Response(
        content=content,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={id}.png"},
    )
