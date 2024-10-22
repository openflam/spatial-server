import glob
import numpy as np
import os
from pathlib import Path
import pickle
import sys

from .. import localizer
from .. import load_cache
from spatial_server.utils.print_log import print_log


def get_scale_two_images(img_path_1, img_path_2, dataset_name, shared_data, pose_cache):
    if img_path_1 not in pose_cache:
        hloc_camera_matrix_1 = localizer.get_hloc_camera_matrix_from_image(
            img_path_1, dataset_name, shared_data
        )[0]
        pose_cache[img_path_1] = hloc_camera_matrix_1
    else:
        hloc_camera_matrix_1 = pose_cache[img_path_1]

    if img_path_2 not in pose_cache:
        hloc_camera_matrix_2 = localizer.get_hloc_camera_matrix_from_image(
            img_path_2, dataset_name, shared_data
        )[0]
        pose_cache[img_path_2] = hloc_camera_matrix_2
    else:
        hloc_camera_matrix_2 = pose_cache[img_path_2]

    hloc_location_1 = hloc_camera_matrix_1[:3, 3]
    hloc_location_2 = hloc_camera_matrix_2[:3, 3]

    hloc_distance = np.linalg.norm(hloc_location_1 - hloc_location_2)

    # Read aframe camera matrix from the saved file
    location_data_1_file = Path(img_path_1).parent / "location_data.pkl"
    with open(location_data_1_file, "rb") as f:
        location_data_1 = pickle.load(f)
        aframe_camera_matrix_1 = location_data_1["aframe_camera_matrix_world"]
        aframe_camera_matrix_1 = np.array(aframe_camera_matrix_1).reshape((4, 4)).T

    location_data_2_file = Path(img_path_2).parent / "location_data.pkl"
    with open(location_data_2_file, "rb") as f:
        location_data_2 = pickle.load(f)
        aframe_camera_matrix_2 = location_data_2["aframe_camera_matrix_world"]
        aframe_camera_matrix_2 = np.array(aframe_camera_matrix_2).reshape((4, 4)).T

    aframe_location_1 = aframe_camera_matrix_1[:3, 3]
    aframe_location_2 = aframe_camera_matrix_2[:3, 3]

    aframe_distance = np.linalg.norm(aframe_location_1 - aframe_location_2)

    scale = aframe_distance / hloc_distance

    return scale


def get_scale_from_query_dir(query_dir, dataset_name):
    all_queries_dirs = glob.glob(query_dir + "/*")
    img_paths = []
    for dir in all_queries_dirs:
        img_paths.append(dir + "/query_image.png")

    # Load ML models
    shared_data = {}
    load_cache.load_ml_models(shared_data)
    load_cache.load_db_data(shared_data)

    # Get scale for each pair of images
    scales = []
    pose_cache = {}
    for i in range(len(img_paths)):
        for j in range(i + 1, len(img_paths)):
            scales.append(
                get_scale_two_images(
                    img_paths[i], img_paths[j], dataset_name, shared_data, pose_cache
                )
            )

    print("Scales: ", scales)

    # Get the median scale
    scale = np.median(scales)

    # Save the scale to a file
    dataset_path = Path(os.path.join("data", "map_data", dataset_name))
    scale_file = dataset_path / "scale.pkl"
    with open(scale_file, "wb") as f:
        pickle.dump(scales, f)

    return scale


def get_scale_from_image_pose_data(mapname, shared_data=None):
    # Load the image pose data
    map_path = Path(os.path.join("data", "map_data", mapname))
    log_filepath = map_path / "log.txt"
    image_pose_data_path = map_path / "images_with_pose"
    if not image_pose_data_path.exists():
        print_log(
            "No image pose data found. Please save the image pose data first.",
            log_filepath=log_filepath,
        )
        return 1.0
    image_pose_dirs = glob.glob(str(image_pose_data_path) + "/*")
    img_paths = []
    for dir in image_pose_dirs:
        img_paths.append(dir + "/query_image.png")

    # Load ML models
    if shared_data is None:
        shared_data = {}
        load_cache.load_ml_models(shared_data)
        load_cache.load_db_data(shared_data)

    print_log(
        "Scaling the map...",
        log_filepath=log_filepath,
    )
    # Get scale for each pair of images
    scales = []
    pose_cache = {}
    for i in range(len(img_paths)):
        for j in range(i + 1, len(img_paths)):
            scales.append(
                get_scale_two_images(
                    img_paths[i], img_paths[j], mapname, shared_data, pose_cache
                )
            )

    # Get the median scale
    median_scale = np.median(scales)

    print_log(
        f"Scales: {scales}\nMedian scale: {median_scale}",
        log_filepath=log_filepath,
    )

    # Save the scale to a file
    scale_file = map_path / "scale.pkl"
    with open(scale_file, "wb") as f:
        pickle.dump(scales, f)

    return median_scale


if __name__ == "__main__":
    # Read the image paths and dataset name from the command line
    mapname = sys.argv[1]

    get_scale_from_image_pose_data(mapname)
