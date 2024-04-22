import glob
import numpy as np
import os
from pathlib import Path
import pickle
import sys

from .. import localizer
from .. import load_cache

def get_scale_two_images(img_path_1, img_path_2, dataset_name, shared_data):
    hloc_camera_matrix_1 = localizer.get_hloc_camera_matrix_from_image(img_path_1, dataset_name, shared_data)[0]
    hloc_camera_matrix_2 = localizer.get_hloc_camera_matrix_from_image(img_path_2, dataset_name, shared_data)[0]

    hloc_location_1 = hloc_camera_matrix_1[:3, 3]
    hloc_location_2 = hloc_camera_matrix_2[:3, 3]

    hloc_distance = np.linalg.norm(hloc_location_1 - hloc_location_2)

    # Read aframe camera matrix from the saved file
    aframe_camera_1_file = Path(img_path_1).parent / 'aframe_camera_matrix_world.pkl'
    with open(aframe_camera_1_file, 'rb') as f:
        aframe_camera_matrix_1 = pickle.load(f)
        aframe_camera_matrix_1 = np.array(aframe_camera_matrix_1).reshape((4,4)).T
    
    aframe_camera_2_file = Path(img_path_2).parent / 'aframe_camera_matrix_world.pkl'
    with open(aframe_camera_2_file, 'rb') as f:
        aframe_camera_matrix_2 = pickle.load(f)
        aframe_camera_matrix_2 = np.array(aframe_camera_matrix_2).reshape((4,4)).T
    
    aframe_location_1 = aframe_camera_matrix_1[:3, 3]
    aframe_location_2 = aframe_camera_matrix_2[:3, 3]

    aframe_distance = np.linalg.norm(aframe_location_1 - aframe_location_2)

    scale = aframe_distance / hloc_distance

    return scale

def get_scale_from_query_dir(query_dir):
    dataset_name = query_dir.split('/')[-1]
    all_queries_dirs = glob.glob(query_dir + '/*')
    img_paths = []
    for dir in all_queries_dirs:
        img_paths.append(dir + '/query_image.png')
    
    # Load ML models
    shared_data = {}
    load_cache.load_ml_models(shared_data)
    load_cache.load_db_data(shared_data)

    # Get scale for each pair of images
    scales = []
    for i in range(len(img_paths)):
        for j in range(i+1, len(img_paths)):
            scales.append(get_scale_two_images(img_paths[i], img_paths[j], dataset_name, shared_data))
    
    print("Scales: ", scales)

    # Get the median scale
    scale = np.median(scales)
    
    # Save the scale to a file
    dataset_path = Path(os.path.join('data', 'map_data', dataset_name))
    scale_file = dataset_path / 'scale.pkl'
    with open(scale_file, 'wb') as f:
        pickle.dump(scales, f)
    
    return scale


if __name__ == '__main__':
    # Read the image paths and dataset name from the command line
    query_dir = sys.argv[1]

    scale = get_scale_from_query_dir(query_dir)

    print("Scale: ", scale)

