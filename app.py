from flask import Flask, render_template, request, jsonify
from PIL import Image
import os
from datetime import datetime

import ultralytics
from db_config import get_db_connection, init_db

app = Flask(__name__)

# Create directories for storing data
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database
init_db()

# Initialize Model
if os.path.exists("model.pt"):
    model = ultralytics.YOLO("model.pt")
else:
    model = ultralytics.YOLO("yolo11n.pt")

# Define the label mapping based on user input
# User: 1. Unripe, 2. Rotten, 3. Ripe
# Assuming 0-indexed model output:
KAONG_LABELS_MAP = {
    0: "Unripe",
    1: "Rotten",
    2: "Ripe"
}

def get_kaong_label(label_id):
    """Maps a numeric label_id to a string representation."""
    return KAONG_LABELS_MAP.get(int(label_id), "Unknown")


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
def detect_frame():
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        file = request.files["image"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        # Print file info for debugging
        print(f"Received file: {file.filename}, Content type: {file.content_type}")

        # Read and process the image
        image = Image.open(file).convert("RGB")

        # Print image info for debugging
        print(f"Image size: {image.size}, Mode: {image.mode}")

        # Move model to CPU explicitly (if needed, ultralytics handles device placement)
        model.cpu()

        # Perform detection using Ultralytics YOLO model
        results = model.predict(source=image, verbose=False)

        final_detections = []
        img_width, img_height = image.size

        if results and len(results) > 0:
            result = results[0]  # Ultralytics results object for the first image
            
            boxes_xyxy = result.boxes.xyxy.tolist() if result.boxes is not None else []
            conf_scores = result.boxes.conf.tolist() if result.boxes is not None else []
            class_indices = result.boxes.cls.tolist() if result.boxes is not None else []

            # Print raw predictions for debugging
            print(
                "Raw predictions (Ultralytics):",
                {
                    "num_boxes": len(boxes_xyxy),
                    "num_scores": len(conf_scores),
                    "num_class_ids": len(class_indices),
                },
            )
            
            processed_detections = []
            if conf_scores: # Check if there are any detections
                for i in range(len(conf_scores)):
                    score = conf_scores[i]
                    if score > 0.3: # Confidence threshold
                        label_id = class_indices[i]
                        label_name = get_kaong_label(label_id) 
                        box_coords = boxes_xyxy[i]
                        processed_detections.append({
                            "label": label_name,
                            "box": box_coords,
                            "score": score
                        })
            
            if processed_detections:
                final_detections = processed_detections
            # If processed_detections is empty, final_detections remains empty,
            # and the default logic below will be triggered.
        else:
            print("Model prediction did not return any results.")
            # Default logic will be triggered as final_detections is empty.

        # If no valid detections were made, provide a default detection
        if not final_detections:
            print("No high confidence detections found or model returned no results, using default detection")
            default_box = [
                img_width * 0.1,  # x1 - 10% from left
                img_height * 0.1,  # y1 - 10% from top
                img_width * 0.9,  # x2 - 90% from left
                img_height * 0.9,  # y2 - 90% from top
            ]
            final_detections.append({
                "label": "Not Ready for Harvesting", # Specific default label
                "box": default_box,
                "score": 0.5,  # Medium confidence for default detection
            })

        print(f"Returning {len(final_detections)} detections: {final_detections}")
        return jsonify({"detections": final_detections})

    except Exception as e:
        import traceback

        print("Error in detect_frame:", str(e))
        print("Traceback:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route("/save_assessment", methods=["POST"])
def save_assessment():
    try:
        file = request.files["image"]
        assessment = request.form["assessment"]
        confidence = float(request.form["confidence"])
        source = request.form["source"]

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"kaong_{timestamp}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Save the image
        image = Image.open(file)
        image.save(filepath)

        # Save to database
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                sql = """INSERT INTO assessments 
                        (image_url, assessment, confidence, source, timestamp) 
                        VALUES (%s, %s, %s, %s, %s)"""
                values = (
                    f"/static/uploads/{filename}",
                    assessment,
                    confidence,
                    source,
                    datetime.now(),
                )
                cursor.execute(sql, values)
                connection.commit()
                return jsonify({"success": True})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
        else:
            return (
                jsonify({"success": False, "error": "Database connection failed"}),
                500,
            )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/get_assessment_data")
def get_assessment_data():
    try:
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT * FROM assessments ORDER BY timestamp DESC")
                data = cursor.fetchall()

                # Convert datetime objects to ISO format strings
                for item in data:
                    item["timestamp"] = item["timestamp"].isoformat()

                return jsonify(data)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
        else:
            return jsonify({"error": "Database connection failed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
