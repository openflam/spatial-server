import numpy as np
import os
from pathlib import Path
import pickle

from scipy.spatial.transform import Rotation

def convert_hloc_to_blender_frame(matrix):
    # Add 180 degrees to X - change in convention
    matrix = np.array(matrix)
    euler_xyz = Rotation.from_matrix(matrix[:3, :3]).as_euler("xyz", degrees = True)
    euler_xyz[0] += 180
    rotmat = Rotation.from_euler('xyz', euler_xyz, degrees = True).as_matrix()
    matrix[:3, :3] = rotmat
    return matrix

def convert_blender_to_aframe_frame(matrix):
    # Rotate -90 degrees along x-axis
    T_B_to_A = np.eye(4)
    T_B_to_A[:3,:3] = Rotation.from_euler('xyz', [-90,0,0], degrees = True).as_matrix()
    return T_B_to_A @ matrix

def get_arscene_pose_matrix(aframe_camera_pose, hloc_camera_matrix, dataset_name):
    blender_camera_matrix = convert_hloc_to_blender_frame(hloc_camera_matrix)
    blender_camera_matrix_in_aframe = convert_blender_to_aframe_frame(blender_camera_matrix)

    aframe_camera_matrix = np.array(aframe_camera_pose).reshape((4,4)).T

    arscene_pose_aframe = aframe_camera_matrix @ np.linalg.inv(blender_camera_matrix_in_aframe)

    # Apply the scale transformation from the scale file if it exists
    dataset_path = Path(os.path.join('data', 'map_data', dataset_name))
    scale_file = dataset_path / 'scale.pkl'
    if scale_file.exists():
        with open(scale_file, 'rb') as f:
            scales = pickle.load(f)
            scale_median = np.median(scales)
            scale_matrix = np.eye(4)
            for i in range(3):
                scale_matrix[i,i] = scale_median
            arscene_pose_aframe = scale_matrix @ arscene_pose_aframe
            print("Scale applied: ", scale_median)

    return arscene_pose_aframe.T.flatten().tolist()