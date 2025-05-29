// Updated script.js for better alignment and real-time detection
let videoStream;
let detectionInterval;
let cameraStarted = false;
let socket; // Added for WebSocket

function openCamera() {
    const cameraContainer = document.getElementById('cameraContainer');
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const scanContainer = document.getElementById('scanContainer');

    // Hide the scan image and text when camera opens
    const scanImage = scanContainer.querySelector('.scanpng');
    const scanTitle = scanContainer.querySelector('h2');
    if (scanImage) scanImage.style.display = 'none';
    if (scanTitle) scanTitle.style.display = 'none';

    // Show camera container
    cameraContainer.style.display = "block";

    // Initialize Socket.IO connection
    socket = io(); // Connects to the server that served the page

    socket.on('connect', () => {
        console.log('Connected to WebSocket server');
        cameraStarted = true; // Set cameraStarted to true only after connection
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from WebSocket server');
        cameraStarted = false;
    });

    socket.on('detection_results', (data) => {
        // console.log('Detections received:', data);
        if (data.detections && data.detections.length > 0) {
            drawDetections(data); 
            // Assessment saving is now handled by the backend for WebSocket stream
        } else {
            // console.log("No detections in data or detections array is empty.");
            // Optionally, clear previous detections if server sends empty results for no detections
             const canvas = document.getElementById('canvas');
             const ctx = canvas.getContext('2d');
             const video = document.getElementById('video');
             ctx.clearRect(0, 0, canvas.width, canvas.height);
             ctx.drawImage(video, 0, 0, canvas.width, canvas.height); // Redraw video frame
        }
    });

    socket.on('detection_error', (data) => {
        console.error("Detection error from server:", data.error);
        // Optionally, display this error to the user
    });

    // Get user media with constraints
    navigator.mediaDevices.getUserMedia({ 
        video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: 'environment' // Use back camera on mobile devices
        }
    })
    .then(stream => {
        videoStream = stream;
        video.srcObject = stream;
        
        video.onloadedmetadata = () => {
            video.play()
                .then(() => {
                    // Set canvas dimensions after video is playing
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    canvas.style.display = 'block'; // Make sure canvas is visible
                    startRealTimeDetection();
                })
                .catch(err => {
                    console.error("Error playing video:", err);
                });
        };
    })
    .catch(err => {
        console.error("Camera error:", err);
        alert("Error accessing camera. Please make sure you have granted camera permissions.");
        // Show the scan image and text again if camera fails
        if (scanImage) scanImage.style.display = 'block';
        if (scanTitle) scanTitle.style.display = 'block';
    });
}

function closeCamera() {
    const cameraContainer = document.getElementById('cameraContainer');
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const scanContainer = document.getElementById('scanContainer');

    // Show the scan image and text again
    const scanImage = scanContainer.querySelector('.scanpng');
    const scanTitle = scanContainer.querySelector('h2');
    if (scanImage) scanImage.style.display = 'block';
    if (scanTitle) scanTitle.style.display = 'block';

    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        video.srcObject = null;
        videoStream = null;
    }
    
    if (socket && socket.connected) { // Disconnect WebSocket
        socket.disconnect();
        socket = null;
        console.log("WebSocket disconnected by client.");
    }
    
    // Hide both video and canvas
    cameraContainer.style.display = "none";
    canvas.style.display = 'none';
    clearInterval(detectionInterval);
    detectionInterval = null; // Clear interval ID
    cameraStarted = false; // Explicitly set to false
}

function uploadImage() {
    document.getElementById('imageUpload').click();
}

function closeUpload() {
    const uploadPreviewContainer = document.getElementById('uploadPreviewContainer');
    const uploadCanvas = document.getElementById('uploadCanvas');
    uploadPreviewContainer.style.display = 'none';
    
    // Clear the file input so the same file can be uploaded again
    document.getElementById('imageUpload').value = '';
}

async function saveAssessment(imageBlob, detection, source) {
    const formData = new FormData();
    formData.append('image', imageBlob);
    formData.append('assessment', detection.label);
    formData.append('confidence', detection.score);
    formData.append('source', source);

    try {
        const response = await fetch('/save_assessment', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            console.error('Failed to save assessment:', await response.text());
        }
    } catch (error) {
        console.error('Error saving assessment:', error);
    }
}

// Update the captureFrame function for WebSocket
async function captureFrameAndSend() {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');

    if (video.readyState === video.HAVE_ENOUGH_DATA && socket && socket.connected && cameraStarted) {
        // Draw the video frame to a temporary canvas to get data URL
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = video.videoWidth;
        tempCanvas.height = video.videoHeight;
        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);
        
        const imageDataURL = tempCanvas.toDataURL('image/jpeg', 0.8); // Use JPEG and quality 0.8

        // Send frame via WebSocket
        socket.emit('detect_video_frame', { image_data_url: imageDataURL });
        
        // The drawing of detections will happen when 'detection_results' is received.
        // So, we draw the current video frame here to keep the video feed live.
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    } else if (!cameraStarted && detectionInterval) {
        console.log("Camera not fully started or socket not connected, stopping detection interval.");
        clearInterval(detectionInterval);
        detectionInterval = null;
    }
}

function drawDetections(result) {
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const video = document.getElementById('video');

    // Clear previous drawings
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    // Redraw the video frame
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    ctx.lineWidth = 3;
    ctx.font = "18px Arial";
    ctx.strokeStyle = "red";
    ctx.fillStyle = "red";

    if (result.detections) {
        result.detections.forEach(detection => {
            const [x1, y1, x2, y2] = detection.box;
            ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
            // ctx.fillText(`${detection.label} (${(detection.score * 100).toFixed(1)}%)`, x1, y1 - 5);
        });
    }
}

// Add event listener for file upload
document.getElementById('imageUpload').addEventListener('change', async function(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
        alert('Please select an image file');
        return;
    }

    try {
        const uploadPreviewContainer = document.getElementById('uploadPreviewContainer');
        const canvas = document.getElementById('uploadCanvas');
        const ctx = canvas.getContext('2d');
        
        // Clear any previous image data
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Show the upload preview container
        uploadPreviewContainer.style.display = 'block';
        
        // Create a temporary image and load the file
        const img = new Image();
        
        // Create object URL for the file
        const objectUrl = URL.createObjectURL(file);
        console.log('Created object URL:', objectUrl);
        
        // Clean up function to remove old resources
        const cleanup = () => {
            URL.revokeObjectURL(objectUrl);
            img.onload = null;
            img.onerror = null;
        };
        
        img.onload = async function() {
            console.log('Image loaded successfully:', img.width, 'x', img.height);
            try {
                // Create FormData for detection
                const formData = new FormData();
                formData.append('image', file);

                console.log('Sending file:', file.name, 'Size:', file.size, 'Type:', file.type);

                // Send the image to the server for detection
                const response = await fetch('/detect_frame', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                console.log('Detection result:', result);
                
                if (!response.ok) {
                    throw new Error(result.error || 'Detection failed');
                }

                // Set canvas size to match container while maintaining aspect ratio
                const container = canvas.parentElement;
                const containerWidth = container.clientWidth;
                const containerHeight = container.clientHeight;
                
                // Calculate the scale to fit the image
                const scale = Math.min(
                    containerWidth / img.width,
                    containerHeight / img.height
                );
                
                // Calculate the actual dimensions after scaling
                const scaledWidth = img.width * scale;
                const scaledHeight = img.height * scale;
                
                // Set canvas dimensions
                canvas.width = containerWidth;
                canvas.height = containerHeight;
                
                // Calculate position to center the image
                const x = (containerWidth - scaledWidth) / 2;
                const y = (containerHeight - scaledHeight) / 2;
                
                // Clear canvas and draw new image
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, x, y, scaledWidth, scaledHeight);
                
                // Draw detections
                if (result.detections && result.detections.length > 0) {
                    ctx.lineWidth = 3;
                    if (result.detections[0].label == "Unripe") {
                        ctx.strokeStyle = "green";
                        ctx.fillStyle = "green";
                    } else if (result.detections[0].label == "Rotten") {
                        ctx.strokeStyle = "blue";
                        ctx.fillStyle = "blue";
                    } else if (result.detections[0].label == "Ripe") {
                        ctx.strokeStyle = "yellow";
                        ctx.fillStyle = "yellow";
                    }
                    ctx.font = "18px Arial";
                    
                    result.detections.forEach(detection => {
                        // Get original box coordinates
                        const [x1, y1, x2, y2] = detection.box;
                        
                        // Scale and adjust coordinates
                        const boxX = x + (x1 * scale);
                        const boxY = y + (y1 * scale);
                        const boxWidth = (x2 - x1) * scale;
                        const boxHeight = (y2 - y1) * scale;
                        
                        // Draw box
                        ctx.strokeRect(boxX, boxY, boxWidth, boxHeight);
                        
                        // Draw label with background
                        const label = `${detection.label} (${(detection.score * 100).toFixed(1)}%)`;
                        const labelY = boxY > 30 ? boxY - 10 : boxY + 30;
                        
                        // Measure text width
                        const textWidth = ctx.measureText(label).width;
                        
                        // Draw label background
                        // TODO: REDO
                        // ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
                        // ctx.fillRect(boxX, labelY - 20, textWidth + 10, 25);
                        
                        // Draw text
                        ctx.fillStyle = "red";
                        // ctx.fillText(label, boxX + 5, labelY);
                    });
                }
                
                // Clean up resources after successful processing
                cleanup();
                
            } catch (error) {
                console.error("Detection error:", error);
                alert("Error processing image: " + error.message);
                closeUpload();
                cleanup();
            }
        };

        img.onerror = function(err) {
            console.error("Error loading image:", err);
            alert("Error loading the selected image. Please try another file.");
            closeUpload();
            cleanup();
        };
        
        // Set the image source after setting up handlers
        img.src = objectUrl;
        
    } catch (error) {
        console.error("Error handling upload:", error);
        alert("Error uploading image: " + error.message);
        closeUpload();
    }
});

function startRealTimeDetection() {
    if (detectionInterval) {
        clearInterval(detectionInterval); // Clear any existing interval
    }
    // Call captureFrameAndSend instead of captureFrame
    detectionInterval = setInterval(captureFrameAndSend, 200); 
}

document.addEventListener('DOMContentLoaded', () => {
    // Your existing script.js code
});