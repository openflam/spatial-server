import argparse
import os
from pathlib import Path
import subprocess

import numpy as np
import pycolmap
from scipy.spatial.transform import Rotation

def align_colmap_model_manhattan(image_dir, colmap_model_path, method = "MANHATTAN-WORLD", output_path = None):
    if output_path is None:
        print("Output path not provided. Overwriting input model.")
        output_path = colmap_model_path

    if not output_path.exists():
        os.makedirs(output_path)

    align_command = [
        'colmap', 'model_orientation_aligner',
        '--image_path', f'{image_dir}',
        '--input_path', f'{colmap_model_path}',
        '--output_path', f'{output_path}',
        '--method', f'{method}'
    ]
    subprocess.run(align_command)
    rotate_existing_model(output_path)  # Rotate by -90 degrees x axis by default

    return output_path


def rotate_existing_model(model_path, output_path = None):
    if output_path is None:
        output_path = model_path
    reconstruction = pycolmap.Reconstruction(model_path)

    # Rotate by -90 degrees x axis by default
    rotate_90_x_matrix = Rotation.from_euler('xyz', [-90, 0, 0], degrees = True).as_matrix() 
    translate_matrix = np.array([[0],[0],[0]])
    transform_matrix = np.concatenate((rotate_90_x_matrix, translate_matrix), axis = 1)
    reconstruction.transform(transform_matrix)

    reconstruction.write(model_path)

if __name__ == '__main__':
    # Get command line arguments
    parser = argparse.ArgumentParser(description='Align existing COLMAP model')
    parser.add_argument('--model_path', type=str, help='Path to the COLMAP model')
    parser.add_argument('--images_path', type=str, help='Path to the images directory')
    args = parser.parse_args()

    # Align model using Manhattan
    align_colmap_model_manhattan(args.images_path, args.model_path)
