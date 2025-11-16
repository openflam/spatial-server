import contextlib
import json
import logging
import os
from pathlib import Path
import sqlite3
import sys

import numpy as np
from scipy.spatial.transform import Rotation

from . import map_creator
from spatial_server.utils.run_command import run_command
from spatial_server.utils.print_log import print_log
from spatial_server.hloc_localization.map_creation.map_transforms import transform_map_from_matrix
from third_party.hloc.hloc import logger as hloc_logger, handler as hloc_default_handler


def _prepare_cameras_file(transforms_json, output_directory):
    """
    Prepare the cameras.txt from transforms.json
    """
    # The transforms.json file says "OPENCV" as the camera model by default.
    # But the images used are corrected images (undistorted) so I think the camera model should be "PINHOLE".
    camera_model = "PINHOLE"
    camera_model_id = 1

    # Camera params format from: https://github.com/colmap/colmap/blob/a3967a69eed33e2d3e171ca20832c4dfc907b7bb/src/colmap/sensor/models.h#L196
    param_keys = ["fl_x", "fl_y", "cx", "cy"]

    camera_file_comment = f"""# Camera list with one line of data per camera:
    #   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
    # Number of cameras: {len(transforms_json['frames'])}"""

    imgname_to_cameraid = {}
    camera_info_str_list = []
    cameras_info = []
    for idx, frame in enumerate(transforms_json["frames"]):
        camera_id = idx + 1
        width = frame["w"]
        height = frame["h"]

        params = []
        for key in param_keys:
            params.append(frame[key])
        params_str = " ".join(map(str, params))
        camera_info_str = " ".join(
            map(str, [camera_id, camera_model, width, height, params_str])
        )
        camera_info_str_list.append(camera_info_str)

        imgname = frame["file_path"].split("/")[-1]
        imgname_to_cameraid[imgname] = camera_id

        cameras_info.append(
            {
                "camera_id": camera_id,
                "camera_model_id": camera_model_id,
                "width": width,
                "height": height,
                "params": params,
            }
        )

    camera_file_str = "\n".join([camera_file_comment, *camera_info_str_list]) + "\n"

    # Save the file to cameras.txt
    os.makedirs(output_directory, exist_ok=True)
    output_file_path = f"{output_directory}/cameras.txt"
    with open(output_file_path, "w") as f:
        f.write(camera_file_str)

    return cameras_info, imgname_to_cameraid


def _prepare_images_file(
    transforms_json, output_directory, imgname_to_cameraid, imgname_to_imgid
):
    """
    Prepare images.txt from transforms.json
    """

    image_file_comment = """# Image list with two lines of data per image:
    #   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
    #   POINTS2D[] as (X, Y, POINT3D_ID)"""

    image_info_list = []
    for idx, frame in enumerate(transforms_json["frames"]):
        img_name = frame["file_path"].split("/")[-1]
        c2w = np.array(frame["transform_matrix"])
        c2w[0:3, 1:3] *= -1
        w2c = np.linalg.inv(c2w)
        rotmat = w2c[:3, :3]
        qx, qy, qz, qw = Rotation.from_matrix(rotmat).as_quat()
        tx, ty, tz = w2c[:3, 3]
        image_info_list.append(
            " ".join(
                map(
                    str,
                    [
                        imgname_to_imgid[img_name],
                        qw,
                        qx,
                        qy,
                        qz,
                        tx,
                        ty,
                        tz,
                        imgname_to_cameraid[img_name],
                        img_name,
                    ],
                )
            )
        )
    image_info_str = "\n\n".join(image_info_list)

    stat_comment_line = (
        f"# Number of images: {len(image_info_list)}, mean observations per image: 0.0"
    )

    image_file_str = "\n".join([image_file_comment, stat_comment_line, image_info_str])

    # Save the file to images.txt
    os.makedirs(output_directory, exist_ok=True)
    output_file_path = f"{output_directory}/images.txt"
    with open(output_file_path, "w") as f:
        f.write(image_file_str)


def _update_cameras_db(db_path, cameras_info):
    """
    Update cameras database
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Delete all existing cameras from table
    cur.execute("DELETE from cameras;")

    def array_to_blob(array):
        return array.tobytes()

    for camera in cameras_info:
        params = np.round(np.asarray(camera["params"], np.float64))
        cur.execute(
            "INSERT INTO cameras VALUES (?, ?, ?, ?, ?, ?)",
            (
                camera["camera_id"],
                camera["camera_model_id"],
                camera["width"],
                camera["height"],
                array_to_blob(params),
                False,
            ),
        )

    conn.commit()
    conn.close()


def _update_images_db(db_path, imgname_to_imgid, imgname_to_cameraid):
    """
    Update images in database
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    imgid_to_cameraid = {}
    for imgname in imgname_to_cameraid:
        imgid = imgname_to_imgid[imgname]
        imgid_to_cameraid[imgid] = imgname_to_cameraid[imgname]

    for imgid in imgid_to_cameraid:
        cur.execute(
            f"UPDATE images SET camera_id = {imgid_to_cameraid[imgid]} WHERE image_id = {imgid};"
        )

    conn.commit()
    conn.close()


def _get_pair_and_image_ids(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    sql_query = """SELECT pair_id from two_view_geometries WHERE rows > 0;"""
    cur.execute(sql_query)
    pair_ids = cur.fetchall()

    sql_query = """SELECT image_id from images;"""
    cur.execute(sql_query)
    image_ids = cur.fetchall()

    conn.close()

    pair_ids = [id[0] for id in pair_ids]
    image_ids = [id[0] for id in image_ids]
    return pair_ids, image_ids


def _pair_id_to_image_ids(pair_id):
    image_id2 = pair_id % 2147483647
    image_id1 = (pair_id - image_id2) / 2147483647
    return int(image_id1), int(image_id2)


def _get_images_without_correspondences(db_path):
    pair_ids, img_ids = _get_pair_and_image_ids(db_path)

    images_with_pairs = set()
    for pair_id in pair_ids:
        id1, id2 = _pair_id_to_image_ids(pair_id)
        images_with_pairs.add(id1)
        images_with_pairs.add(id2)
    all_image_ids = set(img_ids)

    imgs_without_correspodences = all_image_ids - images_with_pairs
    return imgs_without_correspodences


def _delete_images_without_correspondences(
    db_path, input_recon_path, output_recon_path, log_filepath=None
):
    image_ids_to_delete = _get_images_without_correspondences(db_path)
    image_ids_to_delete_str = "\n".join(map(str, image_ids_to_delete))

    image_ids_to_delete_filepath = Path(db_path).parent / "images_to_delete.txt"
    with open(image_ids_to_delete_filepath, "w") as f:
        f.write(image_ids_to_delete_str)

    os.makedirs(output_recon_path, exist_ok=True)
    images_deleter_command = [
        "colmap",
        "image_deleter",
        "--input_path",
        f"{input_recon_path}",
        "--output_path",
        f"{output_recon_path}",
        "--image_ids_path",
        f"{image_ids_to_delete_filepath}",
    ]
    run_command(images_deleter_command, log_filepath=log_filepath)

def _permute_transform_matrix_axis(transform_matrix, axis_permutation):
    euler_rotation = Rotation.from_matrix(transform_matrix[:3,:3]).as_euler('xyz', degrees=True)
    translation = transform_matrix[:3,3]
    euler_rotation_axis_change = np.array([euler_rotation[axis_permutation[0]], euler_rotation[axis_permutation[1]], euler_rotation[axis_permutation[2]]])
    rot_mat_axis_change = Rotation.from_euler('xyz', euler_rotation_axis_change, degrees=True).as_matrix()
    
    translation_axis_change = np.array([[translation[axis_permutation[0]]], [translation[axis_permutation[1]]], [translation[axis_permutation[2]]]])
    
    transform_mat_axis_change = np.concatenate((rot_mat_axis_change, translation_axis_change), axis=1)
    transform_mat_axis_change = np.concatenate((transform_mat_axis_change, np.array([[0,0,0,1]])), axis=0)

    return transform_mat_axis_change

def _transform_hloc_reconstruction(hloc_data_directory, alignment_transform_matrix, negate_y_rotation=True):
    # For some reason, I have to 1. Negate the y rotation in Euler, and 2. Permute the axis x,y,z to z,x,y
    # to get the correct alignment.

    # Negate the y rotation in Euler
    if negate_y_rotation:
        print("Negating y rotation in Euler...")
        euler_rotation = Rotation.from_matrix(alignment_transform_matrix[:3,:3]).as_euler('xyz', degrees=True)
        euler_rotation_y_neg = np.array([euler_rotation[0], -euler_rotation[1], euler_rotation[2]])
        rot_mat_y_neg = Rotation.from_euler('xyz', euler_rotation_y_neg, degrees=True).as_matrix()

        translation = alignment_transform_matrix[:3,3]
        translation = np.array([[translation[0]], [translation[1]], [translation[2]]])

        transform_mat_y_neg = np.concatenate((rot_mat_y_neg, translation), axis=1)
        transform_mat_y_neg = np.concatenate((transform_mat_y_neg, np.array([[0,0,0,1]])), axis=0)
        alignment_transform_matrix = transform_mat_y_neg

    # Permute the axis x,y,z to z,x,y
    transform_mat_axis_permute = _permute_transform_matrix_axis(alignment_transform_matrix, [2,0,1])
    
    # Transform the hloc reconstruction
    transform_map_from_matrix(hloc_data_directory / "sfm_reconstruction", transform_mat_axis_permute[:3,:])


def build_map_from_polycam_output(polycam_data_directory, log_filepath=None, negate_y_mesh_align=True):
    # Define directories
    ns_data_directory = Path(polycam_data_directory).parent / "ns_data"
    images_directory = ns_data_directory / "images"

    colmap_directory = Path(polycam_data_directory).parent / "colmap_known_poses"
    # Initial dummy reconstruction with just the camera poses
    init_recon_output_directory = f"{colmap_directory}/sparse/0"
    # Initial dummy reconstruction where images with no correspondences are removed
    init_recon_with_deleted_imgs_directory = (
        f"{colmap_directory}/sparse/0_with_deleted_imgs"
    )
    # Final reconstruction with triangulated points
    final_recon_output_directory = f"{colmap_directory}/sparse/1"

    hloc_data_directory = Path(polycam_data_directory).parent / "hloc_data"

    # Call nsprocess data
    run_command(
        [
            "ns-process-data",
            "polycam",
            "--data",
            f"{polycam_data_directory}",
            "--output-dir",
            f"{ns_data_directory}",
            "--min-blur-score",
            "0",
            "--max-dataset-size",
            "-1",
        ],
        log_filepath=log_filepath,
    )

    # Read transforms.json file
    json_file_path = f"{ns_data_directory}/transforms.json"
    with open(json_file_path, "r") as f:
        transforms_json = json.load(f)

    # ns-process-data removes some images that have low blur scores from transforms.json.
    # Remove these images from the images directory.
    existing_images = os.listdir(images_directory)
    images_in_transforms = [
        frame["file_path"].split("/")[-1] for frame in transforms_json["frames"]
    ]
    removed_images = set(existing_images) - set(images_in_transforms)
    for img in removed_images:
        os.remove(images_directory / img)

    # Extract features and create database
    os.makedirs(colmap_directory, exist_ok=True)
    extract_features_command = [
        "colmap",
        "feature_extractor",
        "--database_path",
        f"{colmap_directory}/database.db",
        "--image_path",
        f"{ns_data_directory}/images",
    ]
    print_log("Extracting features...", log_filepath)
    run_command(extract_features_command, log_filepath=log_filepath)

    # Get mapping from name to image_id
    conn = sqlite3.connect(f"{colmap_directory}/database.db")
    cur = conn.cursor()
    cur.execute("SELECT * from images;")
    images_db = cur.fetchall()

    imgname_to_imgid = {}
    for row in images_db:
        imgname_to_imgid[row[1]] = row[0]
    conn.close()

    # Prepare cameras file
    cameras_info, imgname_to_cameraid = _prepare_cameras_file(
        transforms_json, init_recon_output_directory
    )

    # Prepare images file
    _prepare_images_file(
        transforms_json,
        init_recon_output_directory,
        imgname_to_imgid,
        imgname_to_cameraid,
    )

    # Update cameras database
    _update_cameras_db(f"{colmap_directory}/database.db", cameras_info)

    # Update images database
    _update_images_db(
        f"{colmap_directory}/database.db", imgname_to_imgid, imgname_to_cameraid
    )

    # Prepare points3d file - empty file
    points3D_file_str = ""
    output_file_path = f"{init_recon_output_directory}/points3D.txt"
    with open(output_file_path, "w") as f:
        f.write(points3D_file_str)

    # Run matching
    os.makedirs(final_recon_output_directory, exist_ok=True)
    matcher_command = [
        "colmap",
        "exhaustive_matcher",
        "--database_path",
        f"{colmap_directory}/database.db",
    ]
    print_log("Matching features...", log_filepath)
    run_command(matcher_command, log_filepath=log_filepath)

    # Delete images without correspondences
    _delete_images_without_correspondences(
        db_path=f"{colmap_directory}/database.db",
        input_recon_path=init_recon_output_directory,
        output_recon_path=init_recon_with_deleted_imgs_directory,
    )

    # Run triangulation
    triangulation_command = [
        "colmap",
        "point_triangulator",
        "--database_path",
        f"{colmap_directory}/database.db",
        "--image_path",
        f"{ns_data_directory}/images",
        "--input_path",
        f"{init_recon_with_deleted_imgs_directory}",
        "--output_path",
        f"{final_recon_output_directory}",
    ]
    print_log("Triangulating points...", log_filepath)
    run_command(triangulation_command, log_filepath=log_filepath)

    # Create hloc map from the final reconstruction
    # Redirect its output to a log file if log_filepath is provided
    output_file_obj = sys.stdout if log_filepath is None else open(log_filepath, "a")

    # Redirect hloc logger output to the log file
    if log_filepath is not None:
        hloc_logger.removeHandler(hloc_default_handler)
        hloc_logger.addHandler(logging.FileHandler(log_filepath))

    with contextlib.redirect_stdout(output_file_obj), contextlib.redirect_stderr(
        output_file_obj
    ):
        try:
            print("Creating hloc map from the colmap reconstruction...")
            map_creator.create_map_from_colmap_data(
                colmap_model_path=final_recon_output_directory,
                image_dir=f"{ns_data_directory}/images",
                output_dir=hloc_data_directory,
                manhattan_align=False,
                elevate=False,
            )

            # Transform the map to the correct orientation using the mesh_info.json file
            print("Transforming the map using mesh_info.json...")
            # Read alignment transform
            with open(Path(polycam_data_directory) / "mesh_info.json") as f:
                mesh_info = json.load(f)

            alignment_transform = np.array(mesh_info["alignmentTransform"])
            alignment_transform = alignment_transform.reshape((4,4)).T
            _transform_hloc_reconstruction(
                hloc_data_directory, alignment_transform,
                negate_y_rotation=negate_y_mesh_align
            )

            print("Map creation COMPLETED...")
        except Exception as e:
            print("Map creation FAILED...ERROR:")
            print(e)
    if log_filepath is not None:
        output_file_obj.close()
