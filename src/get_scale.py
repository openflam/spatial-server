import numpy as np
import os
from pathlib import Path
import pickle
import sys

import localizer

def get_scale(img_path_1, img_path_2, dataset_name):
    hloc_camera_matrix_1 = localizer.get_hloc_camera_matrix_from_image(img_path_1, dataset_name)[0]
    hloc_camera_matrix_2 = localizer.get_hloc_camera_matrix_from_image(img_path_2, dataset_name)[0]

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

    # Save the scale to a file
    dataset_path = Path(os.path.join('data', 'map_data', dataset_name))
    scale_file = dataset_path / 'scale.pkl'
    with open(scale_file, 'wb') as f:
        pickle.dump(scale, f)

    return scale

if __name__ == '__main__':
    # Read the image paths and dataset name from the command line
    img_path_1 = sys.argv[1]
    img_path_2 = sys.argv[2]
    dataset_name = sys.argv[3]

    scale = get_scale(img_path_1, img_path_2, dataset_name)

    print("Scale: ", scale)

