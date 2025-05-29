import torch
import torchvision
import torchvision.transforms as transforms
import torchvision.models.detection as detection
from torch.utils.data import DataLoader, Dataset
import os
import cv2
import numpy as np
from PIL import Image

# Custom Dataset Class for Kaong Images
class KaongDataset(Dataset):
    def __init__(self, image_folder, transform=None):
        self.image_folder = image_folder
        self.transform = transform
        self.image_files = [f for f in os.listdir(image_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        img_path = os.path.join(self.image_folder, self.image_files[idx])
        image = Image.open(img_path).convert("RGB")

        if self.transform:
            image = self.transform(image)

        return image

# Load a Pretrained RetinaNet Model
def load_retinanet():
    model = detection.retinanet_resnet50_fpn(pretrained=True)
    model.eval()  # Set to evaluation mode (since we're fine-tuning)
    return model

# Define Image Transformations
transform = transforms.Compose([
    transforms.Resize((400, 400)),  # Smaller resolution for faster processing
    transforms.ToTensor(),
])

# Load Dataset
image_folder = "dataset"  # Change this to your dataset folder
dataset = KaongDataset(image_folder, transform=transform)
dataloader = DataLoader(dataset, batch_size=4, shuffle=True)

# Load Model
model = load_retinanet()

# Save Model
model_path = "model.pth"
torch.jit.save(torch.jit.script(model), model_path)
print(f"Model saved to {model_path}")
