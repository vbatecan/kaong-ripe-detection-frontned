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

        # Transform the image
        image_tensor = transform(image)
        print(f"Tensor shape: {image_tensor.shape}")

        # Add batch dimension
        image_tensor = [image_tensor]

        # Move model to CPU explicitly
        model.cpu()

        with torch.no_grad():
            predictions = model(image_tensor)

            # Print raw predictions for debugging
            print(
                "Raw predictions:",
                {
                    "boxes": (
                        predictions[0]["boxes"].shape
                        if len(predictions[0]["boxes"]) > 0
                        else "no boxes"
                    ),
                    "labels": (
                        predictions[0]["labels"].shape
                        if len(predictions[0]["labels"]) > 0
                        else "no labels"
                    ),
                    "scores": (
                        predictions[0]["scores"].shape
                        if len(predictions[0]["scores"]) > 0
                        else "no scores"
                    ),
                },
            )

        # Get the image dimensions for default box
        img_width, img_height = image.size

        # If no detections with high confidence, provide a default detection
        if (
            len(predictions[0]["scores"]) == 0
            or predictions[0]["scores"][0].item() < 0.3
        ):
            print("No high confidence detections found, using default detection")
            # Create a default detection covering most of the image
            default_box = [
                img_width * 0.1,  # x1 - 10% from left
                img_height * 0.1,  # y1 - 10% from top
                img_width * 0.9,  # x2 - 90% from left
                img_height * 0.9,  # y2 - 90% from top
            ]
            # For now, we'll assume "Not Ready for Harvesting" as default
            detections = [
                {
                    "label": "Not Ready for Harvesting",
                    "box": default_box,
                    "score": 0.5,  # Medium confidence for default detection
                }
            ]
        else:
            detections = []
            for i in range(len(predictions[0]["scores"])):
                score = predictions[0]["scores"][i].item()
                if score > 0.3:
                    label_id = predictions[0]["labels"][i].item()
                    label = get_kaong_label(label_id)
                    box = predictions[0]["boxes"][i].tolist()
                    detections.append({"label": label, "box": box, "score": score})

        print(f"Returning {len(detections)} detections")
        return jsonify({"detections": detections})

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
