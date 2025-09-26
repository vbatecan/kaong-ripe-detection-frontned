"""
Configuration settings for the Kaong Detection Application.
Contains all constants and configurable parameters.
"""
import os
from typing import Dict, Any

# Device configuration
INFERENCE_DEVICE = "cuda"

# Model configuration  
DEFAULT_MODEL_PATH = "yolo11n.pt"
CUSTOM_MODEL_PATH = "best.pt"

# Detection thresholds
CONFIDENCE_THRESHOLD = 0.2
DATABASE_SAVE_CONFIDENCE_LEVEL = 0.8

# Image processing configuration
MAX_IMAGE_WIDTH = 1920
MAX_IMAGE_HEIGHT = 1080
IMAGE_QUALITY = 95

# File and directory configuration
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'), 
    'password': os.getenv('DB_PASSWORD', '1234'),
    'database': os.getenv('DB_NAME', 'kaong_assessment'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'charset': 'utf8mb4',
    'autocommit': False,
    'pool_size': 10,
    'pool_reset_session': True
}

# Label mapping for kaong detection
# Based on model training: 0=Ripe, 1=Rotten, 2=Unripe
KAONG_LABELS_MAP: Dict[int, str] = {
    0: "Ripe",
    1: "Rotten", 
    2: "Unripe"
}

# Assessment mapping for database storage
ASSESSMENT_MAP: Dict[str, str] = {
    "Ripe": "Ready for Harvesting",
    "Unripe": "Not Ready for Harvesting",
    "Rotten": "Rotten"
}

# Default bounding box coordinates (as fractions of image dimensions)
DEFAULT_BOX_COORDS = {
    'x1_fraction': 0.1,
    'y1_fraction': 0.1, 
    'x2_fraction': 0.9,
    'y2_fraction': 0.9
}

# Flask configuration
FLASK_CONFIG = {
    'SECRET_KEY': os.getenv('SECRET_KEY', 'your_secret_key_change_in_production'),
    'DEBUG': os.getenv('FLASK_DEBUG', 'True').lower() == 'true',
    'HOST': os.getenv('FLASK_HOST', '127.0.0.1'),
    'PORT': int(os.getenv('FLASK_PORT', 5000))
}

# Logging configuration
LOGGING_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'filename': os.getenv('LOG_FILE', 'kaong_detection.log')
}

def get_model_path() -> str:
    """Get the appropriate model path based on availability."""
    if os.path.exists(CUSTOM_MODEL_PATH):
        return CUSTOM_MODEL_PATH
    return DEFAULT_MODEL_PATH

def ensure_directories() -> None:
    """Create necessary directories if they don't exist."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Create logs directory if logging to file
    if LOGGING_CONFIG['filename']:
        log_dir = os.path.dirname(LOGGING_CONFIG['filename'])
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)