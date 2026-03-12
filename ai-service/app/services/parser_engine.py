import os
import cv2
import numpy as np
import logging
import json
from typing import Dict, Any, List, Tuple
from pdf2image import convert_from_path
from PIL import Image

logger = logging.getLogger(__name__)

class PIDParserEngine:
    """
    Generic implementation of P&ID parsing steps. 
    Ready to be tuned with specific giza-pidparser logic.
    """
    
    def __init__(self):
        self.dpi = 300
        logger.info("Parser Engine Initialized with Generic Pipeline")

    def convert_pdf_to_image(self, pdf_path: str, output_dir: str) -> str:
        """Step 1: PDF to image conversion (high DPI)"""
        logger.info(f"Converting PDF to Image: {pdf_path}")
        try:
            images = convert_from_path(pdf_path, dpi=self.dpi)
            # For simplicity, we process only the first page for now
            image_path = os.path.join(output_dir, "base_image.png")
            images[0].save(image_path, "PNG")
            return image_path
        except Exception as e:
            logger.error(f"PDF Conversion failed: {str(e)}")
            # If it's already an image, return original path
            if pdf_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                return pdf_path
            raise e

    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Step 2: Image preprocessing (thresholding, noise removal)"""
        logger.info("Preprocessing image")
        img = cv2.imread(image_path)
        if img is None:
            raise Exception("Failed to load image for preprocessing")
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Adaptive thresholding for better extraction of technical drawings
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Skeletonization (simplified version using morphological thinning)
        kernel = np.ones((3,3), np.uint8)
        processed = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        return processed

    def extract_contours_and_lines(self, processed_img: np.ndarray) -> Dict[str, Any]:
        """Step 3 & 6: Contour and line detection"""
        logger.info("Extracting contours and lines")
        
        # Detect lines using Probabilistic Hough Transform
        lines_data = []
        lines = cv2.HoughLinesP(processed_img, 1, np.pi/180, threshold=100, minLineLength=50, maxLineGap=10)
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                lines_data.append({"type": "line", "coords": [int(x1), int(y1), int(x2), int(y2)]})

        # Detect contours (symbols usually appear as closed contours)
        contours, _ = cv2.findContours(processed_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contour_data = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 100: # Filter small noise
                x, y, w, h = cv2.boundingRect(cnt)
                contour_data.append({"bbox": [int(x), int(y), int(x+w), int(y+h)], "area": float(area)})
                
        return {"lines": lines_data, "contours": contour_data}

    def detect_objects(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Step 4: Placeholder for the legacy detection models"""
        # In a real scenario, this would call specialized YOLO/ResNet models
        # For now, we return a mock detection based on generic logic
        return [{"label": "generic_component", "confidence": 0.5, "bbox": [150, 150, 250, 250]}]

    def generate_graph(self, lines: List[Dict], symbols: List[Dict]):
        """Step 7: Basic connectivity graph building based on proximity"""
        logger.info("Building connectivity graph")
        # Logic to connect symbols based on lines touching their bounding boxes
        return {"nodes": len(symbols), "edges": 0}

    def generate_artifacts(self, base_image_path: str, detections: List[Dict], output_dir: str) -> Dict[str, str]:
        """Step 8: Generate overlay image and metadata files"""
        img = cv2.imread(base_image_path)
        if img is None:
            return {}
            
        # Draw detections on image
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(img, det["label"], (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
        overlay_path = os.path.join(output_dir, "overlay.png")
        cv2.imwrite(overlay_path, img)
        
        results_path = os.path.join(output_dir, "results.json")
        with open(results_path, "w") as f:
            json.dump({"detections": detections}, f)
            
        return {
            "overlay": "overlay.png",
            "results": "results.json"
        }

    def process_full_pipeline(self, input_path: str, job_id: str, output_dir: str) -> Dict[str, Any]:
        """Main entry point for the integrated pipeline"""
        logger.info(f"Running full pipeline for {job_id}")
        
        # 1. Convert
        img_path = self.convert_pdf_to_image(input_path, output_dir)
        
        # 2. Preprocess
        processed = self.preprocess_image(img_path)
        
        # 3. Geometry
        geometry = self.extract_contours_and_lines(processed)
        
        # 4. Objects (Generic for now)
        detections = self.detect_objects(processed)
        
        # 5. Artifacts
        artifacts = self.generate_artifacts(img_path, detections, output_dir)
        
        return {
            "job_id": job_id,
            "status": "completed",
            "detections": detections,
            "artifacts": artifacts,
            "geometry_summary": {
                "line_count": len(geometry["lines"]),
                "contour_count": len(geometry["contours"])
            }
        }
