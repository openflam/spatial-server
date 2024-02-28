##########################################################
# Performs the following steps:
# 1. Calls ns-process-data which uses: 
#   a. ffmpeg to extract frames from the video and,
#   b. COLMAP to create an SfM model
# 2. Uses hloc (Hierarchical-localization) to build a map of the place
##########################################################

import os
from pathlib import Path

import ffmpeg

from third_party.hloc.hloc import extract_features, pairs_from_covisibility, match_features, triangulation, pairs_from_retrieval, localize_sfm, visualization

from . import config

def create_map_from_video(video_path):
    # Estimate the number of frames to extract
    probe = ffmpeg.probe(video_path)
    video_stream = next(stream for stream in probe['streams'] if stream['codec_type'] == 'video')
    frame_rate_num, frame_rate_den = video_stream['avg_frame_rate'].split('/')
    frame_rate = float(frame_rate_num) / float(frame_rate_den)
    duration = float(video_stream['duration'])
    num_frames_estimate = duration * frame_rate
    num_frames_to_extract = int(num_frames_estimate / 4) # Extract 1 frame in every 4 frames
    print(f"Estimated number of frames to extract: {num_frames_to_extract}")

    # Call ns-process-data
    ns_process_output_dir = os.path.dirname(video_path)
    os.system((
        f'ns-process-data video ' 
        f'--data {video_path} ' 
        f'--output_dir {ns_process_output_dir} '
        f'--num-frames-target {num_frames_to_extract} '
    ))

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
    local_feature_conf = extract_features.confs[config.LOCAL_FEATURE_EXTRACTOR]
    local_features_path = extract_features.main(
        conf = local_feature_conf,
        image_dir = image_dir,
        export_dir = hloc_output_dir
    )

    print("Extracting global descriptors using NetVLad..")
    ## Extract global descriptors from each image using NetVLad
    global_descriptor_conf = extract_features.confs[config.GLOBAL_DESCRIPTOR_EXTRACTOR]
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
    match_features_conf = match_features.confs[config.MATCHER]
    sfm_matches_path = match_features.main(
        conf = match_features_conf,
        pairs = sfm_pairs_path,
        features = local_feature_conf['output'], # This contains the file name where lcoal features are stored
        export_dir = hloc_output_dir
    )

    try:
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
    # If the reconstruction fails, print the error trace
    except Exception as e:
        print("Reconstruction failed..Error trace:")
        print(e)

