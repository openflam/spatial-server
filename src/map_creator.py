##########################################################
# Performs the following steps:
# 1. Calls ns-process-data which uses: 
#   a. ffmpeg to extract frames from the video and,
#   b. COLMAP to create an SfM model
# 2. Uses hloc (Hierarchical-localization) to build a map of the place
##########################################################

import os
from pathlib import Path
import sys

dir_path = Path(os.path.dirname(os.path.realpath(__file__))).parents[0]
sys.path.append(dir_path.__str__())

from third_party.hloc.hloc import extract_features, pairs_from_covisibility, match_features, triangulation, pairs_from_retrieval, localize_sfm, visualization
from third_party.hloc.hloc.utils import viz_3d, io
from third_party.hloc.hloc.localize_sfm import QueryLocalizer, pose_from_cluster

def create_map_from_video(video_path):
    # Call ns-process-data
    ns_process_output_dir = os.path.dirname(video_path)
    os.system(f'ns-process-data video --data {video_path} --output_dir {ns_process_output_dir}')

    # Build the hloc map and features

    ## Define directories
    dataset = Path(ns_process_output_dir)
    image_dir = dataset / 'images'
    colmap_model_path = dataset / 'colmap/sparse/0'

    hloc_output_dir = dataset / 'hloc_data/'
    sfm_pairs_path = hloc_output_dir / 'sfm-pairs-covis20.txt' # Pairs used for SfM reconstruction
    sfm_reconstruction_path = hloc_output_dir / 'sfm_reconstruction' # Path to reconstructed SfM

    # Feature extraction
    ## Extract local features in each data set image using Superpoint
    print("Extracting local features using Superpoint..")
    local_feature_conf = extract_features.confs['superpoint_aachen']
    local_features_path = extract_features.main(
        conf = local_feature_conf,
        image_dir = image_dir,
        export_dir = hloc_output_dir
    )

    print("Extracting global descriptors using NetVLad..")
    ## Extract global descriptors from each image using NetVLad
    global_descriptor_conf = extract_features.confs['netvlad']
    global_descriptors_path = extract_features.main(
        conf = global_descriptor_conf,
        image_dir = image_dir,
        export_dir = hloc_output_dir
    )

    # Create SfM model using the local features just extracted

    ## Note: There is already an SfM model created using Colmap available. However, that is created using the RootSIFT features.
    ## SfM model needs to be created using the new features.

    ## Create matching pairs:
    ## Instead of creating image pairs by exhaustively searching through all possible pairs, we leverage the 
    ## existing colmap model and form pairs by selecting the top 20 most covisibile neighbors for each image
    print("Forming pairs from covisibility..")
    pairs_from_covisibility.main(
        model = colmap_model_path,
        output = sfm_pairs_path,
        num_matched = 20
    )

    ## Use the created pairs to match images and store the matching result in a match file
    print("Matching features using SuperGlue")
    match_features_conf = match_features.confs['superglue']
    sfm_matches_path = match_features.main(
        conf = match_features_conf,
        pairs = sfm_pairs_path,
        features = local_feature_conf['output'], # This contains the file name where lcoal features are stored
        export_dir = hloc_output_dir
    )

    ## Use the matches to reconstruct an SfM model
    print("Reconstructing Model..")
    reconstruction = triangulation.main(
        sfm_dir = sfm_reconstruction_path,
        reference_model = colmap_model_path,
        image_dir = image_dir,
        pairs = sfm_pairs_path,
        features = local_features_path,
        matches = sfm_matches_path
    )
