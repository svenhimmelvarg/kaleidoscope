from typing import List, Optional
from pydantic import BaseModel


class TextItem(BaseModel):
    _id: str
    value: str


class Workflow(BaseModel):
    id: str
    text: List[TextItem]
    models: List[str]
    image_url: str
    loras: Optional[List[str]] = None
    schedulers: Optional[List[str]] = None
    workflow_structure_id: Optional[str] = None
    workflow_structure_signature_id: Optional[str] = None
    source: Optional[str] = None
    dd: Optional[int] = None
    dayOfWeek: Optional[str] = None
    mm: Optional[int] = None
    yy: Optional[int] = None
    week: Optional[str] = None
    weekday: Optional[str] = None
    workflow_id: Optional[str] = None
    resolution: Optional[str] = None
    orientation: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
