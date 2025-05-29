from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from PIL import Image
import os
from datetime import datetime

import ultralytics
from db_config import get_db_connection, init_db

app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key"  # Important for SocketIO
socketio = SocketIO(app)

# --- Configuration ---
INFERENCE_DEVICE = "cuda"  # Options: "cpu", "cuda", "cuda:0", "mps", etc.
CONFIDENCE_THRESHOLD = 0.7 # Adjustable confidence threshold for detections
# -------------------

# Create directories for storing data
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database
init_db()

# Initialize Model
if os.path.exists("best.pt"):
    model = ultralytics.YOLO("best.pt")
else:
    model = ultralytics.YOLO("yolo11n.pt")

# Define the label mapping based on user input
# User: 1. Unripe, 2. Rotten, 3. Ripe
# Assuming 0-indexed model output:
KAONG_LABELS_MAP = {2: "Unripe", 1: "Rotten", 0: "Ripe"}

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

        print(f"Received file: {file.filename}, Content type: {file.content_type}")
        image_pil = Image.open(file.stream).convert("RGB")  # Use file.stream for PIL
        print(f"Image size: {image_pil.size}, Mode: {image_pil.mode}")

        results = model.predict(
            source=image_pil, verbose=False, device=INFERENCE_DEVICE
        )

        final_detections = []
        img_width, img_height = image_pil.size

        if results and len(results) > 0:
            result = results[0]
            boxes_xyxy = result.boxes.xyxy.tolist() if result.boxes is not None else []
            conf_scores = result.boxes.conf.tolist() if result.boxes is not None else []
            class_indices = (
                result.boxes.cls.tolist() if result.boxes is not None else []
            )
            print(result.names)

            print(
                "Raw predictions (Ultralytics):",
                {
                    "num_boxes": len(boxes_xyxy),
                    "num_scores": len(conf_scores),
                    "num_class_ids": len(class_indices),
                },
            )

            processed_detections = []
            if conf_scores:
                for i in range(len(conf_scores)):
                    score = conf_scores[i]
                    if score > CONFIDENCE_THRESHOLD:
                        label_id = class_indices[i]
                        label_name = get_kaong_label(label_id)
                        box_coords = boxes_xyxy[i]
                        processed_detections.append(
                            {"label": label_name, "box": box_coords, "score": score}
                        )

            if processed_detections:
                final_detections = processed_detections
        else:
            print("Model prediction did not return any results.")

        if not final_detections:
            print(
                "No high confidence detections found or model returned no results, using default detection"
            )
            default_box = [
                img_width * 0.1,
                img_height * 0.1,
                img_width * 0.9,
                img_height * 0.9,
            ]
            final_detections.append(
                {
                    "label": "Not Ready for Harvesting",
                    "box": default_box,
                    "score": 0.0,
                }
            )

        # Save assessment for the first (or default) detection from uploaded image
        if final_detections:
            timestamp_val = datetime.now()
            # Generate unique filename using timestamp
            filename = f"kaong_upload_{timestamp_val.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
            filepath = os.path.join(UPLOAD_FOLDER, filename)

            # Save the PIL image object
            image_pil.save(filepath)
            print(f"Uploaded image saved to {filepath}")

            # Save to database
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    sql = """INSERT INTO assessments 
                            (image_url, assessment, confidence, source, timestamp) 
                            VALUES (%s, %s, %s, %s, %s)"""
                    first_detection = final_detections[0]
                    if first_detection["label"] == "Ripe":
                        assessment = "Ready for Harvesting"
                    elif first_detection["label"] == "Unripe":
                        assessment = "Not Ready for Harvesting"
                    else:
                        assessment = "Rotten"
                    
                    values = (
                        f"/static/uploads/{filename}",
                        assessment,
                        first_detection["score"],
                        "upload",  # Source is 'upload'
                        timestamp_val,
                    )
                    cursor.execute(sql, values)
                    connection.commit()
                    print(f"Saved assessment from uploaded image: {filename}")
                except Exception as db_e:
                    print(f"DB Error in /detect_frame for upload: {db_e}")
                finally:
                    if connection.is_connected():
                        cursor.close()
                        connection.close()
            else:
                print("DB connection failed in /detect_frame for upload")

        print(f"Returning {len(final_detections)} detections: {final_detections}")
        return jsonify({"detections": final_detections})

    except Exception as e:
        import traceback

        print("Error in detect_frame:", str(e))
        print("Traceback:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@socketio.on("detect_video_frame")
def handle_video_frame(data):
    try:
        image_data = data["image_data_url"].split(",")[1]  # Get base64 part
        import base64

        image_bytes = base64.b64decode(image_data)

        from io import BytesIO

        image = Image.open(BytesIO(image_bytes)).convert("RGB")

        # Perform detection using Ultralytics YOLO model
        results = model.predict(source=image, verbose=False, device=INFERENCE_DEVICE)

        final_detections = []
        img_width, img_height = image.size

        if results and len(results) > 0:
            result = results[0]
            boxes_xyxy = result.boxes.xyxy.tolist() if result.boxes is not None else []
            conf_scores = result.boxes.conf.tolist() if result.boxes is not None else []
            class_indices = (
                result.boxes.cls.tolist() if result.boxes is not None else []
            )

            processed_detections = []
            if conf_scores:
                for i in range(len(conf_scores)):
                    score = conf_scores[i]
                    if score > CONFIDENCE_THRESHOLD:
                        label_id = class_indices[i]
                        label_name = get_kaong_label(label_id)
                        box_coords = boxes_xyxy[i]
                        processed_detections.append(
                            {
                                "label": label_name,
                                "box": box_coords,
                                "score": score,
                            }
                        )

            if processed_detections:
                final_detections = processed_detections

        if not final_detections:
            default_box = [
                img_width * 0.1,
                img_height * 0.1,
                img_width * 0.9,
                img_height * 0.9,
            ]
            final_detections.append(
                {"label": "Not Ready for Harvesting", "box": default_box, "score": 0.0}
            )

        # Save assessment for the first (or default) detection
        if final_detections:
            # To save the image, we need to write the bytes to a file temporarily
            # or modify save_assessment logic if it can take bytes directly.
            # For simplicity, let's make a unique filename for the frame
            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S_%f"
            )  # Added microseconds for uniqueness
            filename = f"kaong_frame_{timestamp}.jpg"
            filepath = os.path.join(UPLOAD_FOLDER, filename)

            # Save the image from bytes
            with open(filepath, "wb") as f_img:
                f_img.write(image_bytes)

            # Save to database
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    sql = """INSERT INTO assessments 
                            (image_url, assessment, confidence, source, timestamp) 
                            VALUES (%s, %s, %s, %s, %s)"""
                    # Use the first detection for saving, similar to how it was in fetch
                    first_detection = final_detections[0]
                    if first_detection["label"] == "Ripe":
                        assessment = "Ready for Harvesting"
                    elif first_detection["label"] == "Unripe":
                        assessment = "Not Ready for Harvesting"
                    else:
                        assessment = "Rotten"
                    
                    values = (
                        f"/static/uploads/{filename}",
                        assessment,
                        first_detection["score"],
                        "camera_ws",  # Indicate source as camera via WebSocket
                        datetime.now(),
                    )
                    cursor.execute(sql, values)
                    connection.commit()
                    print(f"Saved assessment from WebSocket: {filename}")
                except Exception as db_e:
                    print(f"DB Error in WebSocket handler: {db_e}")
                finally:
                    if connection.is_connected():
                        cursor.close()
                        connection.close()
            else:
                print("DB connection failed in WebSocket handler")

        emit("detection_results", {"detections": final_detections})

    except Exception as e:
        import traceback

        print(f"Error in handle_video_frame: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        # Optionally emit an error back to the client
        emit("detection_error", {"error": str(e)})


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
    # app.run(debug=True)
    socketio.run(app, debug=True)  # Use socketio.run
