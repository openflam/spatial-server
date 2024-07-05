import json
import os
from pathlib import Path
import sqlite3
import subprocess

import numpy as np
from scipy.spatial.transform import Rotation

from . import map_creator


def _prepare_cameras_file(transforms_json, output_directory):
    """
    Prepare the cameras.txt from transforms.json
    """
    # The transforms.json file says "OPENCV" as the camera model by default.
    # But the images used are corrected images (undistorted) so I think the camera model should be "PINHOLE".
    camera_model = "PINHOLE"
    camera_model_id = 1

    # Camera params format from: https://github.com/colmap/colmap/blob/a3967a69eed33e2d3e171ca20832c4dfc907b7bb/src/colmap/sensor/models.h#L196
    param_keys = ['fl_x', 'fl_y', 'cx', 'cy']

    camera_file_comment = f"""# Camera list with one line of data per camera:
    #   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
    # Number of cameras: {len(transforms_json['frames'])}"""

    imgname_to_cameraid = {}
    camera_info_str_list = []
    cameras_info = []
    for idx, frame in enumerate(transforms_json['frames']):
        camera_id = idx + 1
        width = frame['w']
        height = frame['h']
        
        params = []
        for key in param_keys:
            params.append(frame[key])
        params_str = ' '.join(map(str, params))
        camera_info_str = ' '.join(
            map(str, [camera_id, camera_model, width, height, params_str])
        )
        camera_info_str_list.append(camera_info_str)

        imgname = frame['file_path'].split('/')[-1]
        imgname_to_cameraid[imgname] = camera_id

        cameras_info.append({
            'camera_id': camera_id,
            'camera_model_id': camera_model_id,
            'width': width,
            'height': height,
            'params': params,
        })

    camera_file_str = '\n'.join([camera_file_comment, *camera_info_str_list]) + '\n'

    # Save the file to cameras.txt
    os.makedirs(output_directory, exist_ok = True)
    output_file_path = f'{output_directory}/cameras.txt'
    with open(output_file_path, 'w') as f:
        f.write(camera_file_str)

    return cameras_info, imgname_to_cameraid


def _prepare_images_file(transforms_json, output_directory, imgname_to_cameraid, imgname_to_imgid):
    """
    Prepare images.txt from transforms.json
    """

    image_file_comment = """# Image list with two lines of data per image:
    #   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
    #   POINTS2D[] as (X, Y, POINT3D_ID)"""

    image_info_list = []
    for idx, frame in enumerate(transforms_json['frames']):
        img_name = frame['file_path'].split('/')[-1]
        c2w = np.array(frame['transform_matrix'])
        c2w[0:3, 1:3] *= -1
        w2c = np.linalg.inv(c2w)
        rotmat = w2c[:3,:3]
        qx, qy, qz, qw = Rotation.from_matrix(rotmat).as_quat()
        tx, ty, tz = w2c[:3, 3]
        image_info_list.append(' '.join(
            map(str, [imgname_to_imgid[img_name], qw, qx, qy, qz, tx, ty, tz, imgname_to_cameraid[img_name], img_name])
        ))
    image_info_str = '\n\n'.join(image_info_list)

    stat_comment_line = f'# Number of images: {len(image_info_list)}, mean observations per image: 0.0'

    image_file_str = '\n'.join([image_file_comment, stat_comment_line, image_info_str])

    # Save the file to images.txt
    os.makedirs(output_directory, exist_ok = True)
    output_file_path = f'{output_directory}/images.txt'
    with open(output_file_path, 'w') as f:
        f.write(image_file_str)


def _update_cameras_db(db_path, cameras_info):
    """
    Update cameras database
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Delete all existing cameras from table
    cur.execute('DELETE from cameras;')

    def array_to_blob(array):
        return array.tobytes()

    for camera in cameras_info:
        params = np.round(np.asarray(camera['params'], np.float64))
        cur.execute(
            "INSERT INTO cameras VALUES (?, ?, ?, ?, ?, ?)",
            (
                camera['camera_id'],
                camera['camera_model_id'],
                camera['width'],
                camera['height'],
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
        cur.execute(f"UPDATE images SET camera_id = {imgid_to_cameraid[imgid]} WHERE image_id = {imgid};")

    conn.commit()
    conn.close()


def build_map_from_polycam_output(polycam_data_directory):
    # Define directories
    ns_data_directory = Path(polycam_data_directory).parent / 'ns_data'

    colmap_directory = Path(polycam_data_directory).parent / 'colmap_known_poses'
     # Initial dummy reconstruction with just the camera poses
    init_recon_output_directory = f'{colmap_directory}/sparse/0'
     # Final reconstruction with triangulated points
    final_recon_output_directory = f'{colmap_directory}/sparse/1'

    hloc_data_directory = Path(polycam_data_directory).parent / 'hloc_data'

    # Call nsprocess data
    subprocess.run([
        'ns-process-data', 'polycam',
        '--data', polycam_data_directory,
        '--output-dir', ns_data_directory
    ])

    # Extract features and create database
    os.makedirs(colmap_directory, exist_ok = True)
    subprocess.run([
        'colmap', 'feature_extractor',
        '--database_path', f'{colmap_directory}/database.db',
        '--image_path', f'{ns_data_directory}/images'
    ])

    # Get mapping from name to image_id
    conn = sqlite3.connect(f'{colmap_directory}/database.db')
    cur = conn.cursor()
    cur.execute('SELECT * from images;')
    images_db = cur.fetchall()

    imgname_to_imgid = {}
    for row in images_db:
        imgname_to_imgid[row[1]] = row[0]
    conn.close()

    # Read transforms.json file
    json_file_path = f'{ns_data_directory}/transforms.json'
    with open(json_file_path, 'r') as f:
        transforms_json = json.load(f)
    
    # Prepare cameras file
    cameras_info, imgname_to_cameraid = _prepare_cameras_file(transforms_json, init_recon_output_directory)

    # Prepare images file
    _prepare_images_file(transforms_json, init_recon_output_directory, imgname_to_imgid, imgname_to_cameraid)

    # Update cameras database
    _update_cameras_db(f'{colmap_directory}/database.db', cameras_info)

    # Update images database
    _update_images_db(f'{colmap_directory}/database.db', imgname_to_imgid, imgname_to_cameraid)

    # Prepare points3d file - empty file
    points3D_file_str = ''
    output_file_path = f'{init_recon_output_directory}/points3D.txt'
    with open(output_file_path, 'w') as f:
        f.write(points3D_file_str)
    
    # Run matching
    os.makedirs(final_recon_output_directory, exist_ok = True)
    subprocess.run([
        'colmap', 'exhaustive_matcher',
        '--database_path', f'{colmap_directory}/database.db'
    ])

    # Run triangulation
    subprocess.run([
        'colmap', 'point_triangulator',
        '--database_path', f'{colmap_directory}/database.db',
        '--image_path', f'{ns_data_directory}/images',
        '--input_path', init_recon_output_directory,
        '--output_path', final_recon_output_directory
    ])

    # Create hloc map from the final reconstruction
    map_creator.create_map_from_colmap_data(
        colmap_model_path=final_recon_output_directory,
        image_dir=f'{ns_data_directory}/images',
        output_dir = hloc_data_directory
    )
