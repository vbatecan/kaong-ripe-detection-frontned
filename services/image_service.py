"""
Image service for handling image processing, validation, and file operations.
Provides image resizing, validation, and file management capabilities.
"""
import os
import logging
from typing import Optional, Tuple, Union, BinaryIO
from datetime import datetime
from PIL import Image, ImageOps
import base64
from io import BytesIO
from werkzeug.datastructures import FileStorage

from config import (
    UPLOAD_FOLDER,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    MAX_IMAGE_WIDTH,
    MAX_IMAGE_HEIGHT,
    IMAGE_QUALITY
)

logger = logging.getLogger(__name__)

class ImageValidationError(Exception):
    """Custom exception for image validation errors."""
    pass

class ImageService:
    """Service class for handling image processing and file operations."""
    
    def __init__(self):
        """Initialize the image service."""
        self._ensure_upload_directory()
    
    def _ensure_upload_directory(self) -> None:
        """Ensure the upload directory exists."""
        try:
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            logger.debug(f"Upload directory ensured: {UPLOAD_FOLDER}")
        except Exception as e:
            logger.error(f"Failed to create upload directory: {str(e)}")
            raise RuntimeError(f"Upload directory creation failed: {str(e)}")
    
    def _is_allowed_file(self, filename: str) -> bool:
        """Check if the file extension is allowed."""
        if not filename:
            return False
        
        return ('.' in filename and 
                filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS)
    
    def _validate_file_size(self, file: FileStorage) -> None:
        """Validate that the file size is within limits."""
        # Get file size by seeking to end
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)     # Reset to beginning
        
        if size > MAX_FILE_SIZE:
            raise ImageValidationError(
                f"File size ({size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes)"
            )
    
    def _resize_image_if_needed(self, image: Image.Image) -> Image.Image:
        """
        Resize image if it exceeds maximum dimensions while maintaining aspect ratio.
        
        Args:
            image: PIL Image object
            
        Returns:
            Resized PIL Image object if resizing was needed, otherwise original image
        """
        width, height = image.size
        
        if width <= MAX_IMAGE_WIDTH and height <= MAX_IMAGE_HEIGHT:
            return image
        
        # Calculate new size maintaining aspect ratio
        ratio = min(MAX_IMAGE_WIDTH / width, MAX_IMAGE_HEIGHT / height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        
        logger.info(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
        
        # Use high-quality resampling
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return resized_image
    
    def validate_and_process_upload(self, file: FileStorage) -> Tuple[Image.Image, str, Tuple[int, int]]:
        """
        Validate and process an uploaded file.
        
        Args:
            file: Flask FileStorage object from request.files
            
        Returns:
            Tuple of (processed PIL Image, original filename, original dimensions (width, height))
            
        Raises:
            ImageValidationError: If validation fails
        """
        try:
            # Basic validation
            if not file or not file.filename:
                raise ImageValidationError("No file provided or empty filename")
            
            if not self._is_allowed_file(file.filename):
                raise ImageValidationError(
                    f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
                )
            
            # Validate file size
            self._validate_file_size(file)
            
            # Try to open as image
            try:
                image = Image.open(file.stream).convert("RGB")
            except Exception as e:
                raise ImageValidationError(f"Invalid image file: {str(e)}")
            
            # Store original dimensions before any processing
            original_dimensions = image.size  # (width, height)
            
            # Auto-orient the image (handle EXIF rotation)
            image = ImageOps.exif_transpose(image)
            
            # Resize if needed
            image = self._resize_image_if_needed(image)
            
            logger.info(f"Successfully processed upload: {file.filename}, original: {original_dimensions}, processed: {image.size}")
            return image, file.filename, original_dimensions
            
        except ImageValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing upload: {str(e)}")
            raise ImageValidationError(f"Failed to process image: {str(e)}")
    
    def process_base64_image(self, data_url: str) -> Image.Image:
        """
        Process a base64-encoded image from a data URL.
        
        Args:
            data_url: Base64 data URL string (e.g., "data:image/jpeg;base64,...")
            
        Returns:
            Processed PIL Image object
            
        Raises:
            ImageValidationError: If processing fails
        """
        try:
            # Extract base64 data
            if "," not in data_url:
                raise ImageValidationError("Invalid data URL format")
            
            image_data = data_url.split(",")[1]
            
            # Decode base64
            try:
                image_bytes = base64.b64decode(image_data)
            except Exception as e:
                raise ImageValidationError(f"Failed to decode base64 data: {str(e)}")
            
            # Validate size
            if len(image_bytes) > MAX_FILE_SIZE:
                raise ImageValidationError("Image data exceeds maximum size limit")
            
            # Create PIL Image
            try:
                image = Image.open(BytesIO(image_bytes)).convert("RGB")
            except Exception as e:
                raise ImageValidationError(f"Invalid image data: {str(e)}")
            
            # Auto-orient and resize if needed
            image = ImageOps.exif_transpose(image)
            image = self._resize_image_if_needed(image)
            
            logger.debug(f"Successfully processed base64 image, size: {image.size}")
            return image
            
        except ImageValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing base64 image: {str(e)}")
            raise ImageValidationError(f"Failed to process base64 image: {str(e)}")
    
    def save_image(self, image: Image.Image, prefix: str = "kaong", 
                   source: str = "upload") -> str:
        """
        Save a PIL Image to the upload directory with a unique filename.
        
        Args:
            image: PIL Image object to save
            prefix: Filename prefix
            source: Source identifier for filename
            
        Returns:
            The saved filename (relative to upload folder)
        """
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{prefix}_{source}_{timestamp}.jpg"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # Save with high quality
            image.save(filepath, "JPEG", quality=IMAGE_QUALITY, optimize=True)
            
            logger.info(f"Image saved successfully: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to save image: {str(e)}")
            raise RuntimeError(f"Image saving failed: {str(e)}")
    
    def save_raw_image_data(self, image_data: bytes, prefix: str = "kaong", 
                           source: str = "camera") -> str:
        """
        Save raw image bytes to the upload directory.
        
        Args:
            image_data: Raw image bytes
            prefix: Filename prefix
            source: Source identifier for filename
            
        Returns:
            The saved filename (relative to upload folder)
        """
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{prefix}_{source}_{timestamp}.jpg"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # Save raw data
            with open(filepath, "wb") as f:
                f.write(image_data)
            
            logger.info(f"Raw image data saved successfully: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to save raw image data: {str(e)}")
            raise RuntimeError(f"Raw image saving failed: {str(e)}")
    
    def get_image_path(self, filename: str) -> str:
        """
        Get the full file path for a given filename.
        
        Args:
            filename: The filename
            
        Returns:
            Full file path
        """
        return os.path.join(UPLOAD_FOLDER, filename)
    
    def get_image_url(self, filename: str) -> str:
        """
        Get the web-accessible URL for a given filename.
        
        Args:
            filename: The filename
            
        Returns:
            Web-accessible URL path
        """
        return f"/static/uploads/{filename}"
    
    def delete_image(self, filename: str) -> bool:
        """
        Delete an image file from the upload directory.
        
        Args:
            filename: The filename to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = self.get_image_path(filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Image deleted successfully: {filename}")
                return True
            else:
                logger.warning(f"Image file not found for deletion: {filename}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete image {filename}: {str(e)}")
            return False
    
    def cleanup_old_images(self, days_old: int = 30) -> int:
        """
        Clean up old image files from the upload directory.
        
        Args:
            days_old: Delete files older than this many days
            
        Returns:
            Number of files deleted
        """
        try:
            if not os.path.exists(UPLOAD_FOLDER):
                return 0
            
            import time
            current_time = time.time()
            cutoff_time = current_time - (days_old * 24 * 60 * 60)
            
            deleted_count = 0
            for filename in os.listdir(UPLOAD_FOLDER):
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                
                if os.path.isfile(filepath):
                    file_time = os.path.getctime(filepath)
                    
                    if file_time < cutoff_time:
                        try:
                            os.remove(filepath)
                            deleted_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to delete old file {filename}: {str(e)}")
            
            logger.info(f"Cleanup completed: {deleted_count} old files deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during image cleanup: {str(e)}")
            return 0