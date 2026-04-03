"""
PID Parser AI Microservice — FastAPI Application
=================================================
Endpoints:
  GET  /health  — Service health & model status
  POST /parse   — Upload PDF/image, run full pipeline, return results
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from app.schemas.parser import (
    ParserResponse, HealthResponse, Detection, LineDetection,
    GraphData, GraphNode, GraphEdge, GeometrySummary, JobStatus,
)
from app.services.parser_engine import PIDParserEngine
from app.core.config import settings
import uuid
import os
import shutil
import logging
import traceback

# ---------- Logging ----------
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ---------- App ----------
app = FastAPI(
    title="PID Parser AI Microservice",
    description="Wraps the giza-pidparser pipeline as a REST API",
    version="1.0.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve artifacts directory for result downloads
ARTIFACTS_DIR = os.path.abspath(settings.ARTIFACTS_PATH)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=ARTIFACTS_DIR), name="artifacts")

# Global exception handler — surfaces exact error for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": traceback.format_exc()},
    )

# ---------- Engine ----------
parser_engine = PIDParserEngine()

# Allowed file extensions & max size
ALLOWED_EXT = {f".{e}" for e in settings.ALLOWED_EXTENSIONS}
MAX_FILE_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024


# ==========================================================
# GET /health
# ==========================================================
@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        service="ai-microservice",
        models_loaded=parser_engine.models_loaded,
        model_count=1 if parser_engine.models_loaded else 0,
        version="1.0.0",
    )


# ==========================================================
# POST /parse
# ==========================================================
@app.post("/parse", response_model=ParserResponse)
async def parse_pid(file: UploadFile = File(...)):
    """
    Upload a P&ID file (PDF, JPG, JPEG, PNG — max 5 MB).
    Returns detection results, line classifications, graph data,
    and paths to generated artifacts.
    """

    # --- Validate file extension ---
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    # --- Validate file size ---
    contents = await file.read()
    if len(contents) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(contents)} bytes). Max allowed: {settings.MAX_FILE_SIZE_MB} MB",
        )

    # --- Save to job directory ---
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(ARTIFACTS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    file_path = os.path.join(job_dir, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    # --- Run pipeline ---
    try:
        result = parser_engine.process_full_pipeline(file_path, job_id, job_dir)
    except Exception as exc:
        logger.exception("Pipeline crashed")
        raise HTTPException(status_code=500, detail=str(exc))

    # --- Handle pipeline-level failure ---
    if result["status"] == "failed":
        return ParserResponse(
            job_id=job_id,
            status=JobStatus.failed,
            error=result.get("error", "Unknown pipeline error"),
            processing_time_seconds=result.get("processing_time_seconds"),
        )

    # --- Build response ---
    detections = [
        Detection(
            label=d["label"],
            confidence=d["confidence"],
            bbox=d["bbox"],
            model_source=d.get("model_source"),
        )
        for d in result["detections"]
    ]

    line_detections = [
        LineDetection(
            line_type=l["line_type"],
            start=l["start"],
            end=l["end"],
        )
        for l in result.get("line_detections", [])
    ]

    # Artifacts: prefix with job_id for download URL
    artifacts = {
        name: f"{job_id}/{filename}"
        for name, filename in result["artifacts"].items()
    }

    # Graph
    gd = result.get("graph_data", {})
    graph_data = GraphData(
        nodes=[
            GraphNode(id=n["id"], label=n["label"], bbox=n["bbox"])
            for n in gd.get("nodes", [])
        ],
        edges=[
            GraphEdge(source=e["source"], target=e["target"], line_type=e.get("line_type"))
            for e in gd.get("edges", [])
        ],
    )

    # Geometry summary
    gs = result.get("geometry_summary", {})
    geometry_summary = GeometrySummary(
        total_lines=gs.get("total_lines", 0),
        solid_lines=gs.get("solid_lines", 0),
        dashed_lines=gs.get("dashed_lines", 0),
        contour_count=gs.get("contour_count", 0),
    )

    return ParserResponse(
        job_id=job_id,
        status=JobStatus.completed,
        detections=detections,
        line_detections=line_detections,
        artifacts=artifacts,
        graph_data=graph_data,
        geometry_summary=geometry_summary,
        processing_time_seconds=result.get("processing_time_seconds"),
    )
