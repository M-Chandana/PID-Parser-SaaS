from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Detection(BaseModel):
    """A single detected symbol/component on the P&ID."""
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: List[int] = Field(..., min_length=4, max_length=4, description="[x1, y1, x2, y2]")
    model_source: Optional[str] = None  # which YOLO model detected this


class LineDetection(BaseModel):
    """A detected line segment with type classification."""
    line_type: str = Field(..., description="solid or dashed")
    start: List[int] = Field(..., min_length=2, max_length=2, description="[x, y]")
    end: List[int] = Field(..., min_length=2, max_length=2, description="[x, y]")


class GraphNode(BaseModel):
    """A node in the connectivity graph (detected symbol)."""
    id: str
    label: str
    bbox: List[int]


class GraphEdge(BaseModel):
    """An edge in the connectivity graph (connection between symbols)."""
    source: str
    target: str
    line_type: Optional[str] = None  # solid / dashed


class GraphData(BaseModel):
    """Full graph structure from detection results."""
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []


class GeometrySummary(BaseModel):
    """Summary of extracted geometry from the P&ID image."""
    total_lines: int = 0
    solid_lines: int = 0
    dashed_lines: int = 0
    contour_count: int = 0


class ParserResponse(BaseModel):
    """Full response from the /parse endpoint."""
    job_id: str
    status: JobStatus
    detections: List[Detection] = []
    line_detections: List[LineDetection] = []
    artifacts: Dict[str, str] = {}  # name: relative_path
    graph_data: Optional[GraphData] = None
    geometry_summary: Optional[GeometrySummary] = None
    error: Optional[str] = None
    processing_time_seconds: Optional[float] = None


class HealthResponse(BaseModel):
    """Response from the /health endpoint."""
    status: str
    service: str
    models_loaded: bool = False
    model_count: int = 0
    version: str = "1.0.0"
