import torch
import torchvision.models.detection as detection
from PIL import Image
import torchvision.transforms as transforms

# Load RetinaNet model
model = detection.retinanet_resnet50_fpn(weights=detection.RetinaNet_ResNet50_FPN_Weights.DEFAULT)
model.eval()

# Image transformation
transform = transforms.Compose([
    transforms.ToTensor()
])

# Test image path
image_path = "test_image.jpg"
image = Image.open(image_path).convert("RGB")
image = transform(image).unsqueeze(0)

# Perform inference
with torch.no_grad():
    predictions = model(image)

# Process predictions
for i in range(len(predictions[0]['scores'])):
    score = predictions[0]['scores'][i].item()
    if score > 0.5:
        label = predictions[0]['labels'][i].item()
        box = predictions[0]['boxes'][i].tolist()
        print(f"Detected: Label {label}, Score: {score}, Box: {box}")
