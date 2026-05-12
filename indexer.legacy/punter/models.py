from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict


class TextItem(BaseModel):
    _id: str
    value: str

    model_config = ConfigDict(extra="allow")


class Workflow(BaseModel):
    id: str
    text: Optional[List[TextItem]] = None
    models: Optional[List[str]] = None
    image_url: str
    loras: Optional[List[Any]] = None
    schedulers: Optional[List[str]] = None
    workflow_structure_id: Optional[str] = None
    workflow_structure_signature_id: Optional[str] = None
    source: Optional[str] = None
    dd: Optional[int] = None
    dayOfWeek: Optional[str] = None
    mm: Optional[int] = None
    yy: Optional[int] = None
    ym: Optional[str] = None
    week: Optional[str] = None
    weekday: Optional[str] = None
    workflow_id: Optional[str] = None
    resolution: Optional[str] = None
    orientation: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    categories: Optional[List[str]] = None
    caption: Optional[str] = None
    vector_embedding: Optional[List[float]] = None

    model_config = ConfigDict(extra="allow")
