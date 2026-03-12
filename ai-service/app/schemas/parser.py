from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Detection(BaseModel):
    label: str
    confidence: float
    bbox: List[int] # [x1, y1, x2, y2]

class ParserResponse(BaseModel):
    job_id: str
    status: str
    detections: List[Detection]
    artifacts: Dict[str, str] # name: relative_path
    graph_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
