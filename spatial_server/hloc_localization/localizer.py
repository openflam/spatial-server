import numpy as np
import os
from pathlib import Path
import pycolmap
from scipy.spatial.transform import Rotation
import torch

from third_party.hloc.hloc import extract_features, pairs_from_retrieval, match_features
from third_party.hloc.hloc.localize_sfm import QueryLocalizer, pose_from_cluster
from third_party.hloc.hloc import fast_localize

from . import config
from .coordinate_transforms import get_arscene_pose_matrix
from spatial_server.server import shared_data

def _homogenize(rotation, translation):
    """
    Combine the (3,3) rotation matrix and (3,) translation matrix to
    one (4,4) transformation matrix
    """
    homogenous_array = np.eye(4)
    homogenous_array[:3, :3] = rotation
    homogenous_array[:3, 3] = translation
    return homogenous_array


def _rot_from_qvec(qvec):
    # Change (w,x,y,z) to (x,y,z,w)
    return Rotation.from_quat([qvec[1], qvec[2], qvec[3], qvec[0]])


def get_hloc_camera_matrix_from_image(img_path, dataset_name, shared_data=shared_data):

    local_feature_conf = extract_features.confs[config.LOCAL_FEATURE_EXTRACTOR]
    global_descriptor_conf = extract_features.confs[config.GLOBAL_DESCRIPTOR_EXTRACTOR]

    # Dataset paths
    dataset = Path(os.path.join('data', 'map_data', dataset_name, 'hloc_data'))
    db_local_features_path = (dataset / local_feature_conf['output']).with_suffix('.h5')
    # Use the scaled reconstruction if it exists
    db_reconstruction = dataset / 'scaled_sfm_reconstruction'
    if not db_reconstruction.exists():
        db_reconstruction = dataset / 'sfm_reconstruction'

    # Query data dirs
    img_path = Path(img_path)
    query_image_name = os.path.basename(img_path)
    query_processing_data_dir = Path(os.path.dirname(img_path))
    
    ret, log = fast_localize.localize(
        query_processing_data_dir = query_processing_data_dir, 
        query_image_name = query_image_name, 
        device = 'cuda' if torch.cuda.is_available() else 'cpu', 
        local_feature_conf = local_feature_conf, 
        local_features_extractor_model = shared_data['local_features_extractor_model'], 
        global_descriptor_conf = global_descriptor_conf, 
        global_descriptor_model = shared_data['global_descriptor_model'], 
        db_global_descriptors = shared_data['db_global_descriptors'][dataset_name], 
        db_image_names = shared_data['db_image_names'][dataset_name],
        db_local_features_path = db_local_features_path, 
        matcher_model = shared_data['matcher_model'], 
        db_reconstruction = db_reconstruction,
    )
    
    ret['confidence'] = float(log['PnP_ret']['num_inliers'] / log['keypoints_query'].shape[0])

    hloc_camera_matrix = None
    if ret['success']:
        hloc_camera_matrix = np.linalg.inv(_homogenize(
            rotation = _rot_from_qvec(ret['qvec']).as_matrix(), 
            translation = ret['tvec'],
        ))

    return hloc_camera_matrix, ret


def localize(img_path, dataset_name, aframe_camera_matrix_world):
    
    hloc_camera_matrix, ret = get_hloc_camera_matrix_from_image(img_path, dataset_name)

    if ret['success']:
        arscene_pose_matrix = get_arscene_pose_matrix(
            aframe_camera_pose = aframe_camera_matrix_world,
            hloc_camera_matrix = hloc_camera_matrix,
            dataset_name = dataset_name
        )
        return {
            'success': True,
            'arscene_pose': arscene_pose_matrix,
            'num_inliers': int(ret['num_inliers']),
            'confidence': int(ret['num_inliers']),
        }
    else:
        return {'success': False}
