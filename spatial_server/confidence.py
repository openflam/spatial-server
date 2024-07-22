import os
from pathlib import Path
import sys
import h5py
from collections import defaultdict

from . import extract_features, extractors, matchers, pairs_from_retrieval, match_features, visualization
from .extract_features import ImageDataset
from .localize_sfm import QueryLocalizer, pose_from_cluster
from .fast_localize import localize
from .utils import viz_3d, io
from .utils.base_model import dynamic_load
from .utils.io import list_h5_names
from .utils.parsers import names_to_pair

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
from .train_model import ProjectionHead

torch_hub_dir = Path('data/torch_hub')
if not torch_hub_dir.exists():
    torch_hub_dir.mkdir(parents=True)
torch.hub.set_dir(str(torch_hub_dir))

def encode_map(map, device, preprocess, model):
    model.load_state_dict(torch.load(f"models/{map}_ViTL14-336px.pth"))
    # Create and load the projection head
    projection_head = ProjectionHead(model.visual.output_dim, 512, 256).to(device)
    projection_head.load_state_dict(torch.load(f"models/{map}_projection_head.pth"))

    map_path = f"/code/data/map_data/{map}/images"

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
        features = model.encode_image(map_path)
        projected_features = projection_head(features.float())
        projected_features = projected_features / projected_features.norm(dim=-1, keepdim=True)

    #Save embeddings
    embeddings = {"image_names": image_names, "projected_features": projected_features}
    torch.save(embeddings, f"embeddings/{map}_embeddings.pt")

def get_confidence(map, query_path, preprocess, model, device):
    model.load_state_dict(torch.load(f"models/{map}_ViTL14-336px.pth"))
    # Create and load the projection head
    projection_head = ProjectionHead(model.visual.output_dim, 512, 256).to(device)
    projection_head.load_state_dict(torch.load(f"models/{map}_projection_head.pth"))

    embeddings = torch.load(f"embeddings/{map}_embeddings.pt")

    image = preprocess(Image.open(query_path)).unsqueeze(0).to(device)
    with torch.no_grad():
        img_features = model.encode_image(image)

    projected_img_features = projection_head(img_features.float())
    projected_img_features = projected_img_features / projected_img_features.norm(dim=-1, keepdim=True)
    # print(projected_img_features.shape)
    # print(datasets[data_set_name]['images_features'].shape)
    similarity = torch.nn.functional.cosine_similarity(projected_img_features, embeddings["projected_features"])
    top1, idx = torch.topk(similarity, 1, dim=0)
    return top1.tolist()[0], embeddings["image_names"][idx.tolist()[0]]






        