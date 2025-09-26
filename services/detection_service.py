"""
Detection service for YOLO-based kaong fruit detection.
Handles all model loading and inference operations.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import ultralytics
from dataclasses import dataclass

from config import (
    get_model_path,
    CONFIDENCE_THRESHOLD,
    KAONG_LABELS_MAP,
    ASSESSMENT_MAP,
    DEFAULT_BOX_COORDS,
    INFERENCE_DEVICE
)

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """Data class representing a single detection result."""
    label: str
    box: List[float]  # [x1, y1, x2, y2] absolute coordinates
    box_relative: List[float]  # [x1, y1, x2, y2] relative coordinates (0-1 range)
    score: float
    assessment: str
    image_width: int  # Width of image that coordinates are based on
    image_height: int  # Height of image that coordinates are based on
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert detection to dictionary format for JSON serialization."""
        return {
            'label': self.label,
            'box': self.box,
            'box_relative': self.box_relative,
            'score': self.score,
            'assessment': self.assessment,
            'image_width': self.image_width,
            'image_height': self.image_height
        }
class DetectionService:
    """Service class for handling YOLO model operations and kaong detection."""

    def __init__(self):
        """Initialize the detection service with YOLO model."""
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the YOLO model with error handling."""
        try:
            model_path = get_model_path()
            logger.info(f"Loading YOLO model from: {model_path}")
            self._model = ultralytics.YOLO(model_path)
            logger.info("YOLO model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {str(e)}")
            raise RuntimeError(f"Model loading failed: {str(e)}")

    @property
    def model(self) -> ultralytics.YOLO:
        """Get the loaded YOLO model."""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call _load_model() first.")
        return self._model

    def _get_kaong_label(self, label_id: int) -> str:
        """Map numeric label ID to kaong label string."""
        return KAONG_LABELS_MAP.get(int(label_id), "Unknown")

    def _get_assessment(self, label: str) -> str:
        """Map kaong label to assessment string."""
        return ASSESSMENT_MAP.get(label, "Unknown Assessment")

    def _create_default_detection(self, img_width: int, img_height: int) -> Detection:
        """Create a default detection when no objects are detected."""
        # Calculate absolute coordinates
        x1 = img_width * DEFAULT_BOX_COORDS['x1_fraction']
        y1 = img_height * DEFAULT_BOX_COORDS['y1_fraction']
        x2 = img_width * DEFAULT_BOX_COORDS['x2_fraction']
        y2 = img_height * DEFAULT_BOX_COORDS['y2_fraction']
        
        default_box = [x1, y1, x2, y2]
        
        # Calculate relative coordinates (0-1 range)
        default_box_relative = [
            DEFAULT_BOX_COORDS['x1_fraction'],
            DEFAULT_BOX_COORDS['y1_fraction'],
            DEFAULT_BOX_COORDS['x2_fraction'],
            DEFAULT_BOX_COORDS['y2_fraction']
        ]
        
        return Detection(
            label="Unknown",
            box=default_box,
            box_relative=default_box_relative,
            score=0.0,
            assessment="Not Ready for Harvesting",
            image_width=img_width,
            image_height=img_height
        )

    def _process_model_results(self, results: List[Any], img_width: int, img_height: int) -> List[Detection]:
        """Process raw YOLO model results into Detection objects."""
        detections = []

        if not results or len(results) == 0:
            logger.warning("Model prediction returned no results")
            return [self._create_default_detection(img_width, img_height)]

        result = results[0]

        # Extract detection data
        boxes_xyxy = result.boxes.xyxy.tolist() if result.boxes is not None else []
        conf_scores = result.boxes.conf.tolist() if result.boxes is not None else []
        class_indices = result.boxes.cls.tolist() if result.boxes is not None else []

        logger.debug(
            f"Raw predictions: {len(boxes_xyxy)} boxes, {len(conf_scores)} scores, {len(class_indices)} classes")

        # Process each detection
        for i in range(len(conf_scores)):
            score = conf_scores[i]
            
            if score > CONFIDENCE_THRESHOLD:
                label_id = class_indices[i]
                label = self._get_kaong_label(label_id)
                assessment = self._get_assessment(label)
                box_coords = boxes_xyxy[i]  # [x1, y1, x2, y2] absolute coordinates
                
                # Calculate relative coordinates (0-1 range)
                x1, y1, x2, y2 = box_coords
                box_relative = [
                    x1 / img_width,   # x1 relative
                    y1 / img_height,  # y1 relative  
                    x2 / img_width,   # x2 relative
                    y2 / img_height   # y2 relative
                ]
                
                detections.append(Detection(
                    label=label,
                    box=box_coords,
                    box_relative=box_relative,
                    score=score,
                    assessment=assessment,
                    image_width=img_width,
                    image_height=img_height
                ))        # Return default detection if no high-confidence detections found
        if not detections:
            logger.info("No high confidence detections found, using default")
            detections = [self._create_default_detection(img_width, img_height)]

        return detections

    def detect_objects(self, image: Image.Image) -> Tuple[List[Detection], bool]:
        """
        Perform object detection on an image.
        
        Args:
            image: PIL Image object to analyze
            
        Returns:
            Tuple of (detections_list, has_valid_detections)
            has_valid_detections is True if any detection has score > CONFIDENCE_THRESHOLD
        """
        try:
            if not isinstance(image, Image.Image):
                raise ValueError("Input must be a PIL Image object")

            logger.debug(f"Processing image: size={image.size}, mode={image.mode}")

            # Perform prediction
            results = self.model.predict(
                source=image,
                verbose=True,
                device=INFERENCE_DEVICE
            )

            # Process results
            img_width, img_height = image.size
            detections = self._process_model_results(results, img_width, img_height)

            # Check if we have valid detections (score > threshold)
            has_valid_detections = any(d.score > CONFIDENCE_THRESHOLD for d in detections)

            logger.info(f"Detection complete: {len(detections)} objects found, valid: {has_valid_detections}")
            return detections, has_valid_detections
        except Exception as e:
            logger.error(f"Error during object detection: {str(e)}")
            img_width, img_height = image.size if hasattr(image, 'size') else (640, 480)
            default_detection = self._create_default_detection(img_width, img_height)
            return [default_detection], False

    def detect_objects_dict(self, image: Image.Image) -> Dict[str, Any]:
        """
        Convenience method that returns detections in dictionary format.
        
        Args:
            image: PIL Image object to analyze
            
        Returns:
            Dictionary with 'detections' key containing list of detection dictionaries
        """
        detections, _ = self.detect_objects(image)
        return {
            'detections': [detection.to_dict() for detection in detections]
        }
