import os
import shutil
from pathlib import Path
import sys
from collections import defaultdict

import torch
import torch.nn as nn
import torch.optim as optim

from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
import random
import clip
from PIL import Image
import os
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
from torch.cuda.amp import autocast, GradScaler
import pillow_heif
pillow_heif.register_heif_opener()


torch_hub_dir = Path('data/torch_hub')
if not torch_hub_dir.exists():
    torch_hub_dir.mkdir(parents=True)
torch.hub.set_dir(str(torch_hub_dir))


class ContrastiveDataset(Dataset):
    def __init__(self, root_dir, anchor_folder, transform=None):
        self.root_dir = root_dir
        self.anchor_folder = anchor_folder
        self.transform = transform

        self.anchor_images = sorted([f for f in os.listdir(os.path.join(root_dir, anchor_folder)) 
                              if f.lower().endswith(('.png', '.jpg', '.jpeg', '.heif'))])
        # print(self.anchor_images)
        
        self.other_folders = [f for f in os.listdir(root_dir) 
                              if not f.startswith('.') and os.path.isdir(os.path.join(root_dir, f)) and f != anchor_folder]
        # print(self.other_folders)
        
        self.other_images = {}
        for folder in self.other_folders:
            self.other_images[folder] = [f for f in os.listdir(os.path.join(root_dir, folder)) 
                                         if f.lower().endswith(('.png', '.jpg', '.jpeg', '.heif'))]
        # print(self.other_images)

    def __len__(self):
        return len(self.anchor_images)

    def __getitem__(self, idx):
        # Anchor image (always from folder1)
        anchor_img = self.anchor_images[idx]
        anchor_path = os.path.join(self.root_dir, self.anchor_folder, anchor_img)
        anchor = Image.open(anchor_path).convert('RGB')

        # Positive image (different image from folder1)
        positive_img = random.choice([img for img in self.anchor_images if img != anchor_img])
        positive_path = os.path.join(self.root_dir, self.anchor_folder, positive_img)
        positive = Image.open(positive_path).convert('RGB')
        # print(anchor_path, positive_path)

        # Negative image (from a different folder)
        negative_folder = random.choice(self.other_folders)
        negative_img = random.choice(self.other_images[negative_folder])
        negative_path = os.path.join(self.root_dir, negative_folder, negative_img)
        # print(negative_path)
        negative = Image.open(negative_path).convert('RGB')

        if self.transform:
            anchor = self.transform(anchor)
            positive = self.transform(positive)
            negative = self.transform(negative)

        return anchor, positive, negative
    

class CosineSimilarityContrastiveLoss(nn.Module):
    def __init__(self, margin=0.6, negative_weight=1.2):
        super().__init__()
        self.margin = margin
        self.negative_weight = negative_weight

    def forward(self, anchor, positive, negative):
        cos = nn.CosineSimilarity(dim=1)
        
        similarity_positive = cos(anchor, positive)
        similarity_negative = cos(anchor, negative)
        
        losses = torch.relu(self.margin - (similarity_positive - similarity_negative * self.negative_weight))
        return losses.mean()
    

class ProjectionHead(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super().__init__()
        self.projection = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim)
        )
    
    def forward(self, x):
        x = self.projection(x.float())
        return x / x.norm(dim=-1, keepdim=True)


def train_model(map, num_epochs=20, batch_size=16, lr=1e-5):
    # dataset_names = []
    # for dataset in os.listdir("/code/data/map_data/"):
    #     if not dataset.startswith('.'): dataset_names.append(dataset)

    # print(dataset_names)

    # datasets = {}

    # for dataset_name in dataset_names:
    #     paths = {}
    #     paths['querys_path'] = f'/code/data/query_data/{dataset_name}/images'
    #     paths['imgs_path'] = f'/code/data/map_data/{dataset_name}/images'
    #     datasets[dataset_name] = paths

    # print(datasets)

    # Set device
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Load pre-trained CLIP model
    model, preprocess = clip.load("ViT-L/14@336px", device=device)

    # Enable gradient checkpointing
    model.visual.transformer.grad_checkpointing = True

    # Freeze most of the model, only fine-tune the last few layers
    for param in model.parameters():
        param.requires_grad = False

    # Unfreeze the last few layers (adjust as needed)
    for param in model.visual.transformer.resblocks[-2:].parameters():
        param.requires_grad = True

    # Create projection head
    projection_head = ProjectionHead(model.visual.output_dim, 512, 256).to(device)

    # Prepare dataset and dataloader
    root_dir = "Photos_split/train"  # This should contain your folders
    transform = transforms.Compose([
        preprocess,
        transforms.Lambda(lambda x: x.squeeze(0))  # Remove batch dimension added by CLIP's preprocess
    ])
    anchor_folder = map

    dataset = ContrastiveDataset(root_dir, anchor_folder, transform=transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)  # Reduced batch size

    # Initialize contrastive loss
    criterion = CosineSimilarityContrastiveLoss()

    # Adjust optimizer to only update unfrozen parameters
    params_to_optimize = [p for p in list(model.parameters()) + list(projection_head.parameters()) if p.requires_grad]
    optimizer = optim.Adam(params_to_optimize, lr=lr)

    for epoch in range(num_epochs):
        model.train()
        projection_head.train()
        total_loss = 0
        progress_bar = tqdm(enumerate(dataloader), total=len(dataloader), desc=f"Epoch {epoch+1}/{num_epochs}")
        for i, batch in progress_bar:
            anchor, positive, negative = [x.to(device) for x in batch]
            
            with torch.no_grad():
                anchor_features = model.encode_image(anchor)
                positive_features = model.encode_image(positive)
                negative_features = model.encode_image(negative)
            
            anchor_features = projection_head(anchor_features.float())
            positive_features = projection_head(positive_features.float())
            negative_features = projection_head(negative_features.float())
            
            # Normalize features
            anchor_features = anchor_features / anchor_features.norm(dim=-1, keepdim=True)
            positive_features = positive_features / positive_features.norm(dim=-1, keepdim=True)
            negative_features = negative_features / negative_features.norm(dim=-1, keepdim=True)
            
            loss = criterion(anchor_features, positive_features, negative_features)
            
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params_to_optimize, max_norm=1.0)
            optimizer.step()
            
            total_loss += loss.item()
            progress_bar.set_postfix(loss=loss.item())
        
        avg_loss = total_loss / len(dataloader)
        print(f"Epoch [{epoch+1}/{num_epochs}], Average Loss: {avg_loss:.4f}")

    # Save the fine-tuned model
    torch.save(model.state_dict(), f"models/{map}_ViTL14-336px.pth")
    torch.save(projection_head.state_dict(), f"models/{map}_projection_head.pth")

def split_dataset(base_dir='Photos', output_dir='Photos_split', train_ratio=0.8):
    # Ensure reproducibility
    random.seed(42)

    # Create train/test directories
    train_dir = os.path.join(output_dir, 'train')
    test_dir = os.path.join(output_dir, 'test')
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)

    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue

        images = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        random.shuffle(images)

        split_idx = int(len(images) * train_ratio)
        train_images = images[:split_idx]
        test_images = images[split_idx:]

        # Create class folders
        train_class_dir = os.path.join(train_dir, folder_name)
        test_class_dir = os.path.join(test_dir, folder_name)
        os.makedirs(train_class_dir, exist_ok=True)
        os.makedirs(test_class_dir, exist_ok=True)

        # Copy files
        for img in train_images:
            shutil.copy2(os.path.join(folder_path, img), os.path.join(train_class_dir, img))
        for img in test_images:
            shutil.copy2(os.path.join(folder_path, img), os.path.join(test_class_dir, img))

    print("Dataset split complete.")

def convert_heic_to_jpg(folder):
    for root, _, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(".heic"):
                heic_path = os.path.join(root, file)
                jpg_path = os.path.splitext(heic_path)[0] + ".jpg"
                try:
                    img = Image.open(heic_path)
                    img.save(jpg_path, "JPEG")
                    print(f"Converted: {file}")
                except Exception as e:
                    print(f"Failed to convert {file}: {e}")

# convert_heic_to_jpg("Photos_split/test")


# train_model("POS 153")