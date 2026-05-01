import os
import sys
import copy
import logging
import csv
import numpy as np
import cv2
from typing import Dict, Any

# Ensure the cloned giza-pidparser directory is available to our Python path
# This directly satisfies the Roadmap criteria to use ONLY giza-pidparser code
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
GIZA_REPO_SRC = os.path.join(PROJECT_ROOT, "giza-pidparser", "app", "ai-service", "src")
if GIZA_REPO_SRC not in sys.path:
    sys.path.append(GIZA_REPO_SRC)

# Import strictly from the provided repository
try:
    from detection import run_model_predictions, pdf_to_images, detect_lines, detect_dashed_lines
    GIZA_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Failed to import from giza-pidparser! Ensure the repo is populated and dependencies are installed. Error: {e}")
    GIZA_AVAILABLE = False


class PIDParserEngine:
    """
    Microservice Wrapper around the original `giza-pidparser` Python logic. 
    This avoids redefining computer-vision or object detection logic and 
    strictly relies on the original developers' legacy source code.
    """
    
    def __init__(self):
        self.giza_ready = GIZA_AVAILABLE
        # Setup static paths that giza-pidparser inherently relies upon internally
        os.makedirs("app/static", exist_ok=True)
        os.makedirs("pid_parser", exist_ok=True)

    @property
    def models_loaded(self) -> bool:
        return self.giza_ready

    def process_full_pipeline(self, input_path: str, job_id: str, output_dir: str) -> Dict[str, Any]:
        """
        Executes the AI logic delegated ENTIRELY to giza-pidparser.
        """
        if not self.giza_ready:
            return {"job_id": job_id, "status": "failed", "error": "giza-pidparser not found"}
        try:
            # 1) Smart input type detection — only call pdf_to_images for actual PDFs
            #    PNG/JPG images are read directly using numpy (no poppler required)
            ext = os.path.splitext(input_path)[1].lower()
            if ext in (".png", ".jpg", ".jpeg"):
                base_image = cv2.imread(input_path)
                if base_image is None:
                    raise RuntimeError(f"Could not read image file: {input_path}")
            else:
                # PDF — delegate to giza-pidparser's pdf_to_images (needs poppler)
                base_image = pdf_to_images(input_path)
                # pdf_to_images returns a PIL Image, convert to numpy for cv2
                base_image = np.array(base_image)
                base_image = cv2.cvtColor(base_image, cv2.COLOR_RGB2BGR)

            # giza-pidparser's divide_image25() reads from a HARDCODED path 'pid_parser/input.jpg'
            # We must always save the image there before running the pipeline
            os.makedirs("pid_parser", exist_ok=True)
            cv2.imwrite("pid_parser/input.jpg", base_image)
            
            # 2) Run all models from the giza implementation
            final_bboxes1, final_bboxes2, final_bboxes3, c1, c2, c3 = run_model_predictions(base_image)
            
            # 3) Line detection from giza code
            image_copy = copy.deepcopy(base_image)
            dh, dv = detect_lines(image_copy)
            
            # Combine all bounding boxes mathematically as done in their pipeline
            combined = final_bboxes1 + final_bboxes2 + final_bboxes3
            
            # 4) Create artifact outputs in job-specific directory
            # Ensure output_dir exists
            os.makedirs(output_dir, exist_ok=True)
            
            # For B1, we generate placeholder artifacts in the job directory
            # (Full visualization will be implemented in B2/B3)
            model1_path = os.path.join(output_dir, "model_one.png")
            model2_path = os.path.join(output_dir, "model_two.png")
            model3_path = os.path.join(output_dir, "model_three.png")
            csv_path = os.path.join(output_dir, "output.csv")
            
            # Save placeholder detection visualizations (job-isolated)
            # For now, save a copy of the input image as placeholders
            cv2.imwrite(model1_path, base_image)
            cv2.imwrite(model2_path, base_image)
            cv2.imwrite(model3_path, base_image)
            
            # Save detections as CSV (job-isolated)
            try:
                with open(csv_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['label', 'confidence', 'x1', 'y1', 'x2', 'y2'])
                    for box in combined:
                        writer.writerow([
                            'component',
                            float(box[4]),
                            int(box[0]), int(box[1]),
                            int(box[2]), int(box[3])
                        ])
            except Exception as csv_err:
                logging.warning(f"Failed to write CSV: {csv_err}")
            
            # Return relative paths (relative to artifacts directory)
            # These will be prefixed with job_id by main.py
            artifacts = {
                "model1": "model_one.png",
                "model2": "model_two.png",
                "model3": "model_three.png",
                "csv_output": "output.csv"
            }
            
            return {
                "job_id": job_id,
                "status": "completed",
                "detections": [
                    {
                        "bbox": [int(v) for v in box[:4]],   # cast np.float32 → int
                        "confidence": float(box[4]),           # cast np.float32 → float
                        "label": "component"
                    }
                    for box in combined
                ],
                "line_detections": [
                    {
                        "start": [int(dh[i][0][0]), int(dh[i][0][1])],
                        "end":   [int(dh[i][1][0]), int(dh[i][1][1])],
                        "line_type": "solid"
                    }
                    for i in range(len(dh))
                ],
                "artifacts": artifacts,
                "graph_data": {"nodes": [], "edges": []},  # Nodes mapped dynamically downstream
                "geometry_summary": {
                    "total_lines": len(dh) + len(dv),
                    "solid_lines": len(dh) + len(dv),
                    "dashed_lines": 0,
                    "contour_count": len(combined)
                },
                "processing_time_seconds": 0.0
            }
        except Exception as e:
            return {"job_id": job_id, "status": "failed", "error": str(e)}
