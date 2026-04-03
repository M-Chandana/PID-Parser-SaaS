import os
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Server
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    
    # Model paths — directory containing YOLO .pt weight files
    MODEL_DIR: str = os.path.join(os.path.dirname(__file__), "..", "..", "models", "yolo_weights")
    
    # Artifacts output
    ARTIFACTS_PATH: str = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts")
    
    # Processing
    PDF_DPI: int = 300
    MAX_FILE_SIZE_MB: int = 5
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "jpg", "jpeg", "png"]
    
    # Detection thresholds
    DETECTION_CONFIDENCE_THRESHOLD: float = 0.25
    NMS_IOU_THRESHOLD: float = 0.45
    
    # Line detection
    HOUGH_THRESHOLD: int = 80
    MIN_LINE_LENGTH: int = 40
    MAX_LINE_GAP: int = 10
    
    # Contour filtering
    MIN_CONTOUR_AREA: int = 100
    
    # Graph generation
    LINE_SYMBOL_PROXIMITY_PX: int = 20  # max distance (px) for a line endpoint to "touch" a symbol

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
