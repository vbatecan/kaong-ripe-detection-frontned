# Kaong Detection Application - Optimized Version

## Overview
This is an optimized Flask application for detecting the ripeness of Kaong fruit using YOLO (You Only Look Once) computer vision models. The application has been refactored from a monolithic structure to a service-oriented architecture for better maintainability, performance, and scalability.

## Key Optimizations Made

### 1. Service-Oriented Architecture
- **DetectionService**: Handles all YOLO model operations and inference
- **DatabaseService**: Manages database connections with connection pooling
- **ImageService**: Handles image processing, validation, and file operations

### 2. Configuration Management
- Centralized configuration in `config.py`
- Environment variable support for production deployments
- Proper separation of constants and configurable parameters

### 3. Performance Improvements
- Database connection pooling for better resource management
- Image resizing to prevent memory issues with large files
- Proper error handling and logging throughout
- Type hints for better code documentation and IDE support

### 4. Code Quality Enhancements
- Eliminated code duplication between upload and WebSocket handlers
- Added comprehensive input validation
- Implemented proper exception handling
- Added health check endpoint for monitoring

## Project Structure

```
kaong-ripe-detection-frontend/
├── app.py                      # Main Flask application (optimized)
├── config.py                   # Configuration management
├── db_config.py               # Database initialization
├── requirements.txt           # Python dependencies
├── services/                  # Service layer
│   ├── __init__.py
│   ├── detection_service.py   # YOLO detection logic
│   ├── database_service.py    # Database operations
│   └── image_service.py       # Image processing
├── static/                    # Static assets
│   ├── uploads/              # Image upload directory
│   ├── *.css                # Stylesheets
│   ├── *.js                 # JavaScript files
│   └── image/               # Static images
├── templates/                # HTML templates
│   ├── index.html
│   ├── detect.html
│   └── data.html
└── models/                   # YOLO model files
    ├── best.pt              # Custom trained model
    └── yolo11n.pt           # Default YOLO model
```

## API Endpoints

### Core Detection Endpoints
- `POST /detect_frame` - Upload and analyze static images
- `WebSocket /detect_video_frame` - Real-time video frame analysis

### Data Management
- `GET /get_assessment_data` - Retrieve assessment history
- `GET /assessment_stats` - Get assessment statistics
- `POST /save_assessment` - Save manual assessments
- `GET /health` - Health check for monitoring

### Pages
- `GET /` - Main landing page
- `GET /detect` - Detection interface
- `GET /data` - Data visualization page

## Configuration Options

### Environment Variables
```bash
# Database Configuration
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=kaong_detection
DB_PORT=3306

# Flask Configuration
SECRET_KEY=your_secret_key_change_in_production
FLASK_DEBUG=False
FLASK_HOST=127.0.0.1
FLASK_PORT=5000

# Logging
LOG_LEVEL=INFO
LOG_FILE=kaong_detection.log
```

### Detection Settings (config.py)
- `CONFIDENCE_THRESHOLD = 0.7` - Minimum confidence for detections
- `DATABASE_SAVE_CONFIDENCE_LEVEL = 0.8` - Threshold for saving to database
- `MAX_IMAGE_WIDTH = 1920` - Maximum image width for processing
- `MAX_IMAGE_HEIGHT = 1080` - Maximum image height for processing
- `MAX_FILE_SIZE = 10MB` - Maximum upload file size

## Installation and Setup

### 1. Clone and Setup Environment
```bash
git clone <repository-url>
cd kaong-ripe-detection-frontend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Database
```bash
# Setup MySQL database
mysql -u root -p
CREATE DATABASE kaong_detection;
```

### 4. Environment Configuration
```bash
# Create .env file or set environment variables
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=kaong_detection
```

### 5. Run Application
```bash
python app.py
```

## Usage Examples

### Static Image Detection
```bash
curl -X POST -F "image=@kaong_sample.jpg" http://localhost:5000/detect_frame
```

### Get Assessment Data
```bash
curl http://localhost:5000/get_assessment_data
```

### Health Check
```bash
curl http://localhost:5000/health
```

## Model Information

The application supports two YOLO models:
- `best.pt` - Custom trained model (preferred if available)
- `yolo11n.pt` - Default YOLO11 nano model

### Label Mapping
- `0: "Ripe"` - Ready for harvesting
- `1: "Rotten"` - Spoiled fruit
- `2: "Unripe"` - Not ready for harvesting

## Error Handling

The optimized application includes comprehensive error handling:
- Input validation with descriptive error messages
- Database connection error handling with automatic retry
- Image processing error handling with size and format validation
- Logging of all errors for debugging

## Performance Considerations

### Database
- Connection pooling reduces overhead
- Indexed columns for faster queries
- Proper transaction management

### Image Processing
- Automatic image resizing for large uploads
- EXIF orientation handling
- Memory-efficient processing

### Logging
- Configurable log levels
- Structured logging with timestamps
- Error tracking with stack traces

## Security Features

- File type validation for uploads
- File size limits to prevent DoS attacks
- Input sanitization and validation
- Proper error message handling (no sensitive information exposure)

## Monitoring and Health Checks

The `/health` endpoint provides:
- Application status
- Database connectivity status
- Timestamp for monitoring systems

## Development Notes

### Code Quality
- Type hints throughout codebase
- Comprehensive docstrings
- Separation of concerns
- SOLID principles implementation

### Testing Considerations
- Service classes are easily unit testable
- Database operations are isolated
- Image processing logic is independent
- Mock-friendly architecture

## Future Improvements

1. **Caching**: Add Redis for model prediction caching
2. **Async Processing**: Implement Celery for heavy operations
3. **API Versioning**: Add versioning for backward compatibility
4. **Authentication**: Add user authentication and authorization
5. **Metrics**: Add Prometheus metrics for monitoring
6. **File Cleanup**: Implement automatic cleanup of old uploaded files

## Troubleshooting

### Common Issues
1. **Model Loading Errors**: Ensure CUDA is available or set `INFERENCE_DEVICE = "cpu"`
2. **Database Connection**: Verify MySQL service is running and credentials are correct
3. **Permission Issues**: Ensure write permissions for upload directory
4. **Memory Issues**: Reduce `MAX_IMAGE_WIDTH` and `MAX_IMAGE_HEIGHT` for lower memory usage

### Logging
Check application logs for detailed error information:
```bash
tail -f kaong_detection.log
```

## License
[Add your license information here]

## Contributing
[Add contributing guidelines here]