import os
from pathlib import Path
import sys

dir_path = Path(os.path.dirname(os.path.realpath(__file__))).parents[0]
sys.path.append(dir_path.__str__())

from third_party.hloc.hloc import extract_features, pairs_from_retrieval, match_features
from third_party.hloc.hloc.localize_sfm import QueryLocalizer, pose_from_cluster
import pycolmap
import config


def localize(img_path, dataset_name):
    img_path = Path(img_path)

    local_feature_conf = extract_features.confs[config.LOCAL_FEATURE_EXTRACTOR]
    global_descriptor_conf = extract_features.confs[config.GLOBAL_DESCRIPTOR_EXTRACTOR]
    match_features_conf = match_features.confs[config.MATCHER]

    dataset = Path(os.path.join('data', 'map_data', dataset_name, 'hloc_data'))
    db_global_descriptors_path = (dataset / global_descriptor_conf['output']).with_suffix('.h5')
    db_local_features_path = (dataset / local_feature_conf['output']).with_suffix('.h5')
    db_reconstruction = dataset / 'sfm_reconstruction'

    query_image_name = os.path.basename(img_path)

    # Query data
    query_processing_data_dir = Path(os.path.dirname(img_path))
    query_global_matches_path = query_processing_data_dir / 'global_match_pairs.txt'
    query_local_match_path = query_processing_data_dir / 'local_match_data.h5'
    query_results = query_processing_data_dir / 'query_results.txt'

    # Extarct local features and global descriptor for the new image
    query_local_features_path = extract_features.main(
        conf = local_feature_conf,
        image_dir = query_processing_data_dir,
        export_dir = query_processing_data_dir,
        image_list = [query_image_name]
    )

    query_global_descriptor_path = extract_features.main(
        conf = global_descriptor_conf,
        image_dir = query_processing_data_dir,
        export_dir = query_processing_data_dir,
        image_list = [query_image_name]
    )

    ## Use global descriptor matching to get candidate matches
    nearest_candidate_images = pairs_from_retrieval.save_global_candidates_for_query(
        db_descriptors = db_global_descriptors_path,
        query_descriptor = query_global_descriptor_path,
        query_image_names = [query_image_name],
        num_matched = 10,
        output_file_path = query_global_matches_path
    )

    ## Match the query image against the candidate pairs from above
    match_features.match_from_paths(
        conf = match_features_conf,
        pairs_path = query_global_matches_path,
        match_path = query_local_match_path,
        feature_path_q = query_local_features_path,
        feature_path_ref = db_local_features_path
    )

    ## Now we have global candidate and thier mathces. We use this, along with SfM reconstruction to localize the image.
    reconstruction = pycolmap.Reconstruction(db_reconstruction.__str__())
    camera = pycolmap.infer_camera_from_image(query_processing_data_dir / query_image_name)
    ref_ids = [reconstruction.find_image_with_name(r).image_id for r in nearest_candidate_images]
    conf = {
        'estimation': {'ransac': {'max_error': 12}},
        'refinement': {'refine_focal_length': True, 'refine_extra_params': True},
    }
    localizer = QueryLocalizer(reconstruction, conf)
    ret, log = pose_from_cluster(
        localizer = localizer, 
        qname = query_image_name, 
        query_camera = camera, 
        db_ids = ref_ids, 
        features_path = db_local_features_path, 
        matches_path = query_local_match_path,
        features_q_path = query_local_features_path
    )

    if ret['success']:
        return {
            'success': True,
            'qvec': ret['qvec'].tolist(),
            'tvec': ret['tvec'].tolist(),
            'num_inliers': int(ret['num_inliers']),
        }
    else:
        return {'success': False}
