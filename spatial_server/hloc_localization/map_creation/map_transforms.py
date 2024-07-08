"""
Module to be run as a script to rotate and elevate the map.
"""
import argparse

from . import map_aligner, map_cleaner

def rotate_and_elevate(model_path, rotation, elevate, create_pcd):
    if rotation is not None:
        map_aligner.rotate_existing_model(model_path=model_path, rotation=rotation)
        print(f"Rotated model by {rotation}")
    if elevate:
        map_cleaner.elevate_existing_reconstruction(model_path=model_path)
        print(f"Elevating model")
    if create_pcd:
        map_cleaner.clean_map(model_path=model_path)
        print(f"Created cleaned PCD file")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Rotate and elevate the COLMAP model')
    parser.add_argument('--model_path', type=str, help='Path to the COLMAP model')
    parser.add_argument('--rotation', type=str, help='Rotation to apply to the model. Example: x-90, y90, z180', default=None)
    parser.add_argument('--elevate', action='store_true', help='Elevate the model', default=True)
    parser.add_argument('--create_pcd', action='store_true', help='Create a PCD file from the model', default=True)
    args = parser.parse_args()

    rotate_and_elevate(args.model_path, args.rotation, args.elevate, args.create_pcd)
