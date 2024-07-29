import numpy as np
import os
from pathlib import Path
import pickle

from scipy.spatial.transform import Rotation


def convert_hloc_to_blender_frame(matrix):
    # Add 180 degrees to X - change in convention
    matrix = np.array(matrix)
    euler_xyz = Rotation.from_matrix(matrix[:3, :3]).as_euler("xyz", degrees=True)
    euler_xyz[0] += 180
    rotmat = Rotation.from_euler("xyz", euler_xyz, degrees=True).as_matrix()
    matrix[:3, :3] = rotmat
    return matrix


def convert_blender_to_aframe_frame(matrix):
    # Rotate -90 degrees along x-axis
    T_B_to_A = np.eye(4)
    T_B_to_A[:3, :3] = Rotation.from_euler("xyz", [-90, 0, 0], degrees=True).as_matrix()
    return T_B_to_A @ matrix


def get_aframe_pose_matrix(hloc_camera_matrix, dataset_name):
    blender_camera_matrix = convert_hloc_to_blender_frame(hloc_camera_matrix)
    blender_camera_matrix_in_aframe = convert_blender_to_aframe_frame(
        blender_camera_matrix
    )

    return blender_camera_matrix_in_aframe.tolist()
