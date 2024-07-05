import os
import json
import sqlite3
import subprocess

import numpy as np
from scipy.spatial.transform import Rotation

from . import map_creator, map_cleaner, map_aligner


def _prepare_cameras_file(transforms_json, output_directory):
    """
    Prepare the cameras.txt from transforms.json
    """
    camera_id = 1
    camera_model = transforms_json['camera_model']
    width, height = transforms_json['w'], transforms_json['h']

    # Camera params format from: https://github.com/colmap/colmap/blob/a3967a69eed33e2d3e171ca20832c4dfc907b7bb/src/colmap/sensor/models.h#L196
    # TODO: Add other camera models
    param_keys = None
    if camera_model == "OPENCV":
        param_keys = ['fl_x', 'fl_y', 'cx', 'cy', 'k1', 'k2', 'p1', 'p2']
    else:
        raise NotImplementedError("Only OPENCV camera model is implemented. Feel free to implement.")

    params = []
    for key in param_keys:
        params.append(transforms_json[key])
    params_str = ' '.join(map(str, params))

    camera_file_comment = """# Camera list with one line of data per camera:
    #   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
    # Number of cameras: 1"""

    camera_info_str = ' '.join(
        map(str, [camera_id, camera_model, width, height, params_str])
    )
    camera_file_str = '\n'.join([camera_file_comment, camera_info_str]) + '\n'

    # Save the file to cameras.txt
    os.makedirs(output_directory, exist_ok = True)
    output_file_path = f'{output_directory}/cameras.txt'
    with open(output_file_path, 'w') as f:
        f.write(camera_file_str)
    
    return camera_id, camera_model, width, height, params

def _update_cameras_database(camera_id, camera_model, width, height, params, db_path):
    """
    Add the camera to the database
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Delete all existing cameras from table
    cur.execute('DELETE from cameras;')

    def array_to_blob(array):
        return array.tobytes()

    camera_model_id = None
    if camera_model == "OPENCV":
        camera_model_id = 4
    else:
        raise NotImplementedError("Only OPENCV camera model is implemented. Feel free to implement.")

    params = np.round(np.asarray(params, np.float64))
    cur.execute(
        "INSERT INTO cameras VALUES (?, ?, ?, ?, ?, ?)",
        (
            camera_id,
            camera_model_id,
            width,
            height,
            array_to_blob(params),
            False,
        ),
    )
    conn.commit()
    conn.close()
    

def _update_images_database(camera_id, db_path):
    """
    Update the camera_id of all images in the database
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(f"UPDATE images SET camera_id = {camera_id};")

    conn.commit()
    conn.close()


def _prepare_images_file(transforms_json, output_directory, 
                         imgname_to_imgid, imgname_to_cameraid):
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


def build_map_from_kiri_output(input_directory):
    output_directory = f'{input_directory}/colmap_known_poses'
    
    # Initial dummy reconstruction with just the camera poses
    init_recon_output_directory = f'{output_directory}/sparse/0'
    
    # Final reconstruction with triangulated points
    final_recon_output_directory = f'{output_directory}/sparse/1'
    
    # Extract features and create database
    os.makedirs(output_directory, exist_ok = True)
    subprocess.run([
        'colmap', 'feature_extractor',
        '--database_path', f'{output_directory}/database.db',
        '--image_path', f'{input_directory}/images'
    ])

    # Get mapping from name to image_id
    conn = sqlite3.connect(f'{output_directory}/database.db')
    cur = conn.cursor()
    cur.execute('SELECT * from images;')
    images_db = cur.fetchall()

    imgname_to_imgid = {}
    for row in images_db:
        imgname_to_imgid[row[1]] = row[0]
    conn.close()
    
    # Read transforms.json file
    json_file_path = f'{input_directory}/transforms.json'
    with open(json_file_path, 'r') as f:
        transforms_json = json.load(f)
    
    # Prepare cameras file
    camera_id, camera_model, width, height, params = _prepare_cameras_file(transforms_json, init_recon_output_directory)
    _update_cameras_database(
        camera_id, camera_model, width, height, params,
        db_path = f'{output_directory}/database.db', 
    )
    
    # Prepare images file
    # In Kiri engine, all images are assumed to be taken by the same camera
    imgname_to_cameraid = {img_name: 1 for img_name in imgname_to_imgid.keys()}
    _prepare_images_file(transforms_json, init_recon_output_directory, imgname_to_imgid, imgname_to_cameraid)
    _update_images_database(camera_id, db_path = f'{output_directory}/database.db')
    
    # Prepare points3d file - empty file
    points3D_file_str = ''
    output_file_path = f'{init_recon_output_directory}/points3D.txt'
    with open(output_file_path, 'w') as f:
        f.write(points3D_file_str)

    # Run matching
    os.makedirs(final_recon_output_directory, exist_ok = True)
    subprocess.run([
        'colmap', 'exhaustive_matcher',
        '--database_path', f'{output_directory}/database.db'
    ])

    # Run triangulation
    subprocess.run([
        'colmap', 'point_triangulator',
        '--database_path', f'{output_directory}/database.db',
        '--image_path', f'{input_directory}/images',
        '--input_path', init_recon_output_directory,
        '--output_path', final_recon_output_directory
    ])
    
    # Create hloc map from the final reconstruction
    map_creator.create_map_from_colmap_data(
        colmap_model_path=final_recon_output_directory,
        image_dir=f'{input_directory}/images'
    )
