from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import os
import json
from sentence_transformers import SentenceTransformer

router = APIRouter(prefix="/api/embed", tags=["embed"])

# Load release.json to check feature flag
RELEASE_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "release.json")

# Lazy loading of model to avoid slow startup if feature is disabled
_model = None

def get_model():
    global _model
    if _model is None:
        # Load the model and cache it
        # Setting cache_folder to ./models relative to the project root
        model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
        os.makedirs(model_dir, exist_ok=True)
        # Using clip-ViT-B-32 as requested
        _model = SentenceTransformer('clip-ViT-B-32', cache_folder=model_dir)
    return _model

def is_indexing_experimental_enabled():
    try:
        with open(RELEASE_JSON_PATH, "r") as f:
            data = json.load(f)
            return data.get("experimental.indexing", {}).get("defaultValue", False)
    except Exception:
        return False

@router.get("")
async def embed_text(text: str = Query(..., description="Text to embed")):
    if not is_indexing_experimental_enabled():
        raise HTTPException(status_code=403, detail="Vector indexing feature is currently disabled.")
    
    try:
        model = get_model()
        # SentenceTransformer returns numpy array, convert to list
        vector = model.encode(text).tolist()
        return {"vector": vector}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {str(e)}")
