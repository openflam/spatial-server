"""
Module to load ML models and map data into a dictionary. Dictionary can be accessed by all requests.
TODO: This is a hack to avoid loading model in every request. Find a better way to do this.
"""
from pathlib import Path
import os

import numpy as np
import torch

from . import config
from third_party.hloc.hloc import extract_features, match_features, extractors, matchers, pairs_from_retrieval
from third_party.hloc.hloc.utils.base_model import dynamic_load
from third_party.hloc.hloc.utils.io import list_h5_names


def load_ml_models(shared_data):
    """
    Load ML models into the shared_data dictionary
    """
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # Set torch hub directory
    torch_hub_dir = Path('data/torch_hub')
    if not torch_hub_dir.exists():
        torch_hub_dir.mkdir(parents=True)
    torch.hub.set_dir(str(torch_hub_dir))

    # Load global memory - Common data across all maps

    # Load local feature extractor model (Superpoint)
    local_feature_conf = extract_features.confs[config.LOCAL_FEATURE_EXTRACTOR]
    Model = dynamic_load(extractors, local_feature_conf['model']['name'])
    local_features_extractor_model = Model(local_feature_conf['model']).eval().to(device)
    shared_data['local_features_extractor_model'] = local_features_extractor_model
    print(f'Loaded {local_feature_conf["model"]["name"]} model')

    # Load global descriptor model (NetVlad)
    global_descriptor_conf = extract_features.confs[config.GLOBAL_DESCRIPTOR_EXTRACTOR]
    Model = dynamic_load(extractors, global_descriptor_conf['model']['name'])
    global_descriptor_model = Model(global_descriptor_conf['model']).eval().to(device)
    shared_data['global_descriptor_model'] = global_descriptor_model
    print(f'Loaded {global_descriptor_conf["model"]["name"]} model')

    # Load matcher model (SuperGlue)
    match_features_conf = match_features.confs[config.MATCHER]
    Model = dynamic_load(matchers, match_features_conf['model']['name'])
    matcher_model = Model(match_features_conf['model']).eval().to(device)
    shared_data['matcher_model'] = matcher_model
    print(f'Loaded {match_features_conf["model"]["name"]} model')

def load_db_data(shared_data):
    """
    Load map data into the shared_data dictionary
    """
    if not os.path.exists('data/map_data'):
        return
    map_names_list = os.listdir('data/map_data')
    shared_data['db_global_descriptors'] = {}
    shared_data['db_image_names'] = {}

    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # Load global descriptors for all maps
    global_descriptor_conf = extract_features.confs[config.GLOBAL_DESCRIPTOR_EXTRACTOR]
    for dataset_name in map_names_list:
        try:
            dataset = Path(os.path.join('data', 'map_data', dataset_name, 'hloc_data'))
            db_global_descriptors_path = (dataset / global_descriptor_conf['output']).with_suffix('.h5')
            db_image_names = np.array(list_h5_names(db_global_descriptors_path))
            db_global_descriptors = pairs_from_retrieval.get_descriptors(db_image_names, db_global_descriptors_path)
            db_global_descriptors = db_global_descriptors.to(device)
            shared_data['db_global_descriptors'][dataset_name] = db_global_descriptors
            shared_data['db_image_names'][dataset_name] = db_image_names
            print(f'Loaded global descriptors for {dataset_name}')
        except Exception as e:
            print(f'Error loading global descriptors for {dataset_name}: {e}')
            continue
