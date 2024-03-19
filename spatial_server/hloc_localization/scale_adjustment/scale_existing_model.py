import argparse
from pathlib import Path
import pickle
import os

import numpy as np

from . import read_write_model

def _scale_image(image, scale_factor):
    image_dict = image._asdict()
    image_dict['tvec'] = image.tvec * scale_factor
    image_changed = read_write_model.Image(**image_dict)
    return image_changed

def _scale_point3D(point3D, scale_factor):
    point3D_dict = point3D._asdict()
    point3D_dict['xyz'] = point3D.xyz * scale_factor
    point3D_changed = read_write_model.Point3D(**point3D_dict)
    return point3D_changed

def _get_scale_factor(data_dir):
    scale_file = Path(data_dir) / 'scale.pkl'

    scale_factor = 1.0
    if scale_file.exists():
        with open(scale_file, 'rb') as f:
            scales = pickle.load(f)
            scale_factor = np.median(scales)
            print(f'Using a scale factor of {scale_factor} from {scale_file}.')
    else:
        print(f'Warning: No scale file found at {scale_file}. Using a scale factor of {scale_factor}.')

    return scale_factor

def scale_existing_model(model_path):
    scale_factor = _get_scale_factor(Path(model_path).parent.parent)
    cameras, images, points3D = read_write_model.read_model(model_path)
    
    # Scale images
    images_updated = {}
    for image_id in images:
        image = images[image_id]
        image_updated = _scale_image(image, scale_factor)
        images_updated[image_id] = image_updated

    # Scale points3D
    points3D_updated = {}
    for point_id in points3D:
        point = points3D[point_id]
        point_updated = _scale_point3D(point, scale_factor)
        points3D_updated[point_id] = point_updated

    # Write the scaled model
    model_path = Path(model_path)
    output_model_path = model_path.parent / 'scaled_sfm_reconstruction'
    os.makedirs(output_model_path, exist_ok=True)
    _ = read_write_model.write_model(cameras, images_updated, points3D_updated, output_model_path)

if __name__ == '__main__':
    # Get command line arguments
    parser = argparse.ArgumentParser(description='Scale an existing COLMAP model')
    parser.add_argument('--model_path', type=str, help='Path to the COLMAP model')
    args = parser.parse_args()

    # Scale the model
    scale_existing_model(args.model_path)
