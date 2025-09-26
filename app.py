"""
Optimized Flask application for Kaong fruit ripeness detection.
Uses service-oriented architecture for better maintainability and performance.
"""
import logging
from typing import Dict, Any
from datetime import datetime

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

from config import FLASK_CONFIG, LOGGING_CONFIG, DATABASE_SAVE_CONFIDENCE_LEVEL, CONFIDENCE_THRESHOLD, ensure_directories
from services.detection_service import DetectionService
from services.database_service import DatabaseService, Assessment
from services.image_service import ImageService, ImageValidationError
from db_config import init_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    filename=LOGGING_CONFIG['filename'] if LOGGING_CONFIG['filename'] else None
)
logger = logging.getLogger(__name__)

# Ensure necessary directories exist
ensure_directories()

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_CONFIG['SECRET_KEY']
socketio = SocketIO(app)

# Initialize services
try:
    detection_service = DetectionService()
    database_service = DatabaseService()
    image_service = ImageService()
    
    # Initialize database tables
    init_db()
    database_service.create_tables()
    
    logger.info("Application services initialized successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize services: {str(e)}")
    raise RuntimeError(f"Service initialization failed: {str(e)}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/detect")
def detect():
    return render_template("detect.html")


@app.route("/data")
def data():
    return render_template("data.html")


@app.route("/detect_frame", methods=["POST"])
def detect_frame() -> Dict[str, Any]:
    """
    Handle image upload and detection for static image analysis.
    
    Returns:
        JSON response with detection results or error message
    """
    try:
        # Validate request
        if "image" not in request.files:
            logger.warning("No image file provided in request")
            return jsonify({"error": "No image file provided"}), 400

        file = request.files["image"]
        if not file or file.filename == "":
            logger.warning("Empty filename in request")
            return jsonify({"error": "No selected file"}), 400

        logger.info(f"Processing upload: {file.filename}, type: {file.content_type}")

        # Validate and process image
        try:
            image, original_filename, original_dimensions = image_service.validate_and_process_upload(file)
        except ImageValidationError as e:
            logger.error(f"Image validation failed: {str(e)}")
            return jsonify({"error": str(e)}), 400

        # Perform detection
        detections, has_valid_detections = detection_service.detect_objects(image)

        # Save assessment if we have valid detections
        if has_valid_detections and detections:
            first_detection = detections[0]
            
            # Save image
            filename = image_service.save_image(image, prefix="kaong", source="upload")
            
            # Create assessment record
            assessment = Assessment(
                image_url=image_service.get_image_url(filename),
                assessment=first_detection.assessment,
                confidence=first_detection.score,
                source="upload",
                timestamp=datetime.now()
            )
            
            # Save to database
            assessment_id = database_service.save_assessment(assessment)
            if assessment_id:
                logger.info(f"Saved assessment {assessment_id} for upload: {filename}")
            else:
                logger.error("Failed to save assessment to database")

        # Prepare response
        detections_dict = [detection.to_dict() for detection in detections]
        logger.info(f"Returning {len(detections_dict)} detections")
        
        return jsonify({"detections": detections_dict})

    except Exception as e:
        logger.error(f"Unexpected error in detect_frame: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error occurred"}), 500


@socketio.on("detect_video_frame")
def handle_video_frame(data: Dict[str, Any]) -> None:
    """
    Handle real-time video frame detection via WebSocket.
    
    Args:
        data: Dictionary containing 'image_data_url' key with base64 image data
    """
    try:
        if "image_data_url" not in data:
            logger.error("No image_data_url provided in WebSocket data")
            emit("detection_error", {"error": "No image data provided"})
            return

        try:
            image = image_service.process_base64_image(data["image_data_url"])
        except ImageValidationError as e:
            logger.error(f"Base64 image processing failed: {str(e)}")
            emit("detection_error", {"error": str(e)})
            return

        detections, has_valid_detections = detection_service.detect_objects(image)

        if has_valid_detections and detections:
            first_detection = detections[0]
            
            import base64
            image_data = data["image_data_url"].split(",")[1]
            image_bytes = base64.b64decode(image_data)
            filename = image_service.save_raw_image_data(image_bytes, prefix="kaong", source="camera")
            
            assessment = Assessment(
                image_url=image_service.get_image_url(filename),
                assessment=first_detection.assessment,
                confidence=first_detection.score,
                source="camera_ws",
                timestamp=datetime.now()
            )
            
            assessment_id = database_service.save_assessment(assessment)
            if assessment_id:
                logger.debug(f"Saved WebSocket assessment {assessment_id}: {filename}")
            else:
                logger.error("Failed to save WebSocket assessment to database")

        # Emit results to client
        detections_dict = [detection.to_dict() for detection in detections]
        emit("detection_results", {"detections": detections_dict})
        
        logger.debug(f"WebSocket detection complete: {len(detections_dict)} objects")
    except Exception as e:
        logger.error(f"Unexpected error in handle_video_frame: {str(e)}", exc_info=True)
        emit("detection_error", {"error": "Internal server error occurred"})


@app.route("/save_assessment", methods=["POST"])
def save_assessment() -> Dict[str, Any]:
    """
    Save a manual assessment with uploaded image.
    
    Returns:
        JSON response indicating success or failure
    """
    try:
        # Validate required form data
        required_fields = ["assessment", "confidence", "source"]
        for field in required_fields:
            if field not in request.form:
                logger.warning(f"Missing required field: {field}")
                return jsonify({"success": False, "error": f"Missing {field}"}), 400

        # Validate file upload
        if "image" not in request.files:
            logger.warning("No image file in save_assessment request")
            return jsonify({"success": False, "error": "No image file provided"}), 400

        file = request.files["image"]
        if not file or file.filename == "":
            logger.warning("Empty filename in save_assessment request")
            return jsonify({"success": False, "error": "No selected file"}), 400

        # Validate and process image
        try:
            image, original_filename, original_dimensions = image_service.validate_and_process_upload(file)
        except ImageValidationError as e:
            logger.error(f"Image validation failed in save_assessment: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 400

        # Parse form data
        try:
            assessment_text = request.form["assessment"]
            confidence = float(request.form["confidence"])
            source = request.form["source"]
        except (ValueError, KeyError) as e:
            logger.error(f"Invalid form data in save_assessment: {str(e)}")
            return jsonify({"success": False, "error": "Invalid form data"}), 400

        # Save image
        filename = image_service.save_image(image, prefix="kaong", source="manual")
        
        # Create assessment record
        assessment = Assessment(
            image_url=image_service.get_image_url(filename),
            assessment=assessment_text,
            confidence=confidence,
            source=source,
            timestamp=datetime.now()
        )
        
        # Save to database
        assessment_id = database_service.save_assessment(assessment)
        if assessment_id:
            logger.info(f"Manual assessment saved with ID: {assessment_id}")
            return jsonify({"success": True, "assessment_id": assessment_id})
        else:
            logger.error("Failed to save manual assessment to database")
            return jsonify({"success": False, "error": "Database save failed"}), 500

    except Exception as e:
        logger.error(f"Unexpected error in save_assessment: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route("/get_assessment_data")
def get_assessment_data() -> Dict[str, Any]:
    """
    Retrieve all assessment data from the database.
    
    Returns:
        JSON response with assessment data or error message
    """
    try:
        # Get optional query parameters
        limit = request.args.get('limit', type=int)
        source = request.args.get('source', type=str)
        
        # Retrieve assessments from database
        if source:
            assessments = database_service.get_assessments_by_source(source, limit)
        else:
            assessments = database_service.get_all_assessments(limit)
        
        # Convert to dictionary format for JSON response
        data = [assessment.to_dict() for assessment in assessments]
        
        logger.info(f"Retrieved {len(data)} assessments (source: {source}, limit: {limit})")
        return jsonify(data)

    except Exception as e:
        logger.error(f"Error retrieving assessment data: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to retrieve assessment data"}), 500


@app.route("/assessment_stats")
def get_assessment_stats() -> Dict[str, Any]:
    """
    Get statistics about assessments in the database.
    
    Returns:
        JSON response with statistics or error message
    """
    try:
        stats = database_service.get_assessment_stats()
        logger.debug(f"Retrieved assessment statistics: {stats}")
        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error retrieving assessment statistics: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to retrieve statistics"}), 500


# Error handlers
@app.errorhandler(404)
def not_found(error) -> Dict[str, Any]:
    """Handle 404 errors."""
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(500)
def internal_error(error) -> Dict[str, Any]:
    """Handle 500 errors."""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(413)
def request_entity_too_large(error) -> Dict[str, Any]:
    """Handle file too large errors."""
    return jsonify({"error": "File too large"}), 413


# Health check endpoint
@app.route("/health")
def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring."""
    try:
        # Test database connection
        db_status = database_service.test_connection()
        
        return jsonify({
            "status": "healthy" if db_status else "degraded",
            "database": "connected" if db_status else "disconnected",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


if __name__ == "__main__":
    logger.info("Starting Kaong Detection Flask application")
    
    try:
        # Run with SocketIO
        socketio.run(
            app, 
            debug=FLASK_CONFIG['DEBUG'],
            host=FLASK_CONFIG['HOST'],
            port=FLASK_CONFIG['PORT']
        )
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
