from PIL import Image
import io
import ultralytics
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Model
if os.path.exists("trained_model.pt"):
    model = ultralytics.YOLO("trained_model.pt")
else:
    model = ultralytics.YOLO("yolo11n.pt")


@app.route('/detect_frame', methods=['POST'])
def detect_frame():
    # Get the image from the request form data named "image"
    image = request.form['image']
    # Convert the image to a PIL image
    image = Image.open(io.BytesIO(image))
    # Detect the objects in the image
    results = model(image)
    # Return the results
    return jsonify(results)


    pass
    # if 'image' not in request.files:
    #     return jsonify({"error": "No image provided"}), 400
    
    # file = request.files['image']
    # image = Image.open(io.BytesIO(file.read())).convert("RGB")
    # image = transform(image).unsqueeze(0)
    
    # with torch.no_grad():
    #     predictions = model(image)
    
    # detections = []
    # for i in range(len(predictions[0]['scores'])):
    #     score = predictions[0]['scores'][i].item()
    #     if score > 0.5:
    #         label = predictions[0]['labels'][i].item()
    #         box = predictions[0]['boxes'][i].tolist()
    #         detections.append({"label": label, "box": box, "score": score})
    
    # return jsonify({"detections": detections})

if __name__ == '__main__':
    app.run(debug=True)
