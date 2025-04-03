import os
from pathlib import Path
import sys
import h5py
from collections import defaultdict

import pycolmap
import numpy as np
from scipy.spatial.transform import Rotation
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
from train_model import ProjectionHead

from tqdm import tqdm

import pickle

torch_hub_dir = Path('data/torch_hub')
if not torch_hub_dir.exists():
    torch_hub_dir.mkdir(parents=True)
torch.hub.set_dir(str(torch_hub_dir))

def encode_map(map, device, model, preprocess, train):
    # model, preprocess = clip.load("ViT-L/14@336px", device=device)
    if train:
        model.load_state_dict(torch.load(f"models/{map}_ViTL14-336px.pth", weights_only=True))
        # Create and load the projection head
        projection_head = ProjectionHead(model.visual.output_dim, 512, 256).to(device)
        projection_head.load_state_dict(torch.load(f"models/{map}_projection_head.pth", weights_only=True))

    map_path = f"Photos_split/train/{map}"

    image_list = []
    image_names = []

    for filename in os.listdir(map_path):
        if filename.endswith(".jpg") or filename.endswith(".png") or filename.endswith(".jpeg"):  # Adjust file extensions as needed
            image_path = os.path.join(map_path, filename)
            processed_image = preprocess(Image.open(image_path).convert('RGB'))
            image_list.append(processed_image)
            image_names.append(filename)

    image_batch = torch.stack(image_list, dim=0).to(device)
    
    with torch.no_grad():
        features = model.encode_image(image_batch)
        if train:
            projected_features = projection_head(features.float())
            features = projected_features / projected_features.norm(dim=-1, keepdim=True)

    #Save embeddings
    embeddings = {"image_names": image_names, "projected_features": features}
    torch.save(embeddings, f"embeddings/{map}_embeddings.pt" if train else f"untrain_embeddings/{map}_embeddings.pt")

def get_confidence(map, query_path, device, model, preprocess, train):
    if train:
        model.load_state_dict(torch.load(f"models/{map}_ViTL14-336px.pth", weights_only=True))
        # Create and load the projection head
        projection_head = ProjectionHead(model.visual.output_dim, 512, 256).to(device)
        projection_head.load_state_dict(torch.load(f"models/{map}_projection_head.pth", weights_only=True))

    embeddings = torch.load(f"embeddings/{map}_embeddings.pt") if train else torch.load(f"untrain_embeddings/{map}_embeddings.pt")

    image = preprocess(Image.open(query_path)).unsqueeze(0).to(device)
    with torch.no_grad():
        img_features = model.encode_image(image)

    if train:
        projected_img_features = projection_head(img_features.float())
        img_features = projected_img_features / projected_img_features.norm(dim=-1, keepdim=True)
    # print(projected_img_features.shape)
    # print(datasets[data_set_name]['images_features'].shape)
    similarity = torch.nn.functional.cosine_similarity(img_features, embeddings["projected_features"])
    top1, idx = torch.topk(similarity, 1, dim=0)
    return top1.tolist()[0], embeddings["image_names"][idx.tolist()[0]]


rooms = ['HOA 107', 'POS 145', 'POS 146', 'POS 147', 'POS 151', 'POS 153']
model, preprocess = clip.load("ViT-L/14@336px", device='cpu')

for room in rooms:
    confidences = {room: [] for room in rooms}
    print(f"\nProcessing room: {room}")

    image_files = [f for f in os.listdir(os.path.join('Photos_split/test', room)) if f.endswith(".jpg")]
    for f in tqdm(image_files, desc=f"{room} images", leave=False):
        img_path = os.path.join('Photos_split/test', room, f)
        for roomm in rooms:
            confidence, _ = get_confidence(roomm, img_path, 'cpu', model, preprocess, False)
            confidences[roomm].append(confidence)

    # Save the confidences dict as a pickle file
    output_path = os.path.join('untrain_confidence_data', f'{room}_confidences.pkl')
    os.makedirs('untrain_confidence_data', exist_ok=True)
    with open(output_path, 'wb') as f:
        pickle.dump(confidences, f)

    # --- Create a boxplot after finishing this room ---
    plt.figure(figsize=(10, 6))
    plt.boxplot(confidences.values(), labels=confidences.keys())
    plt.title(f'Confidence scores for images in "{room}" vs other rooms')
    plt.xlabel('Other Rooms')
    plt.ylabel('Confidence Score')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join('untrain_plots', room))


# for f in os.listdir('Photos_split/train'):
#     encode_map(f, 'cpu', model, preprocess, False)

        