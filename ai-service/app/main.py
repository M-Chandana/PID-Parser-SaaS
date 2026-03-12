from fastapi import FastAPI, UploadFile, File, HTTPException
from app.schemas.parser import ParserResponse
from app.services.parser_engine import PIDParserEngine
import uuid
import os
import shutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PID Parser AI Microservice")
parser_engine = PIDParserEngine()

ARTIFACTS_DIR = "artifacts"

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ai-microservice"}

@app.post("/parse", response_model=ParserResponse)
async def parse_pid(file: UploadFile = File(...)):
    """
    Wraps existing giza-pidparser logic to process PID PDF/image.
    """
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(ARTIFACTS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Save uploaded file
    file_path = os.path.join(job_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # Run the full pipeline
        result = parser_engine.process_full_pipeline(file_path, job_id, job_dir)
        
        # Prepare artifacts dictionary with full relative paths for the schema
        # The schema expects Dict[str, str] (artifact_name: path)
        processed_artifacts = {}
        for name, filename in result["artifacts"].items():
            processed_artifacts[name] = f"{job_id}/{filename}"
            
        return {
            "job_id": job_id,
            "status": "completed",
            "detections": result["detections"],
            "artifacts": processed_artifacts,
            "graph_data": {"nodes": [], "edges": []}
        }
        
    except Exception as e:
        logger.error(f"Pipeline processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
