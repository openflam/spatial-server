##########################################################
# Performs the following steps:
# 1. Calls ns-process-data which uses:
#   a. ffmpeg to extract frames from the video and,
#   b. COLMAP to create an SfM model
# 2. Uses hloc (Hierarchical-localization) to build a map of the place
##########################################################

import os
import subprocess
from pathlib import Path

import ffmpeg

from third_party.hloc.hloc import (
    extract_features,
    pairs_from_covisibility,
    match_features,
    triangulation,
    pairs_from_retrieval,
    localize_sfm,
    visualization,
)

from .. import config, load_cache
from spatial_server.server import shared_data
from . import map_aligner, map_cleaner, kiri_engine, polycam


def create_map_from_colmap_data(
    ns_process_output_dir=None, colmap_model_path=None, image_dir=None, output_dir=None
):

    # Build the hloc map and features
    assert ns_process_output_dir is not None or (
        colmap_model_path is not None and image_dir is not None
    ), "Either ns_process_output_dir or (colmap_model_path and image_dir) must be provided"

    ## Define directories
    if ns_process_output_dir is not None:
        dataset = Path(ns_process_output_dir)
        image_dir = dataset / "images"
        colmap_model_path = dataset / "colmap/sparse/0"
    else:
        colmap_model_path = Path(colmap_model_path)
        image_dir = Path(image_dir)
        dataset = Path(image_dir).parent

    if output_dir is not None:
        hloc_output_dir = Path(output_dir)
    else:
        hloc_output_dir = dataset / "hloc_data/"
    sfm_pairs_path = (
        hloc_output_dir / "sfm-pairs-covis20.txt"
    )  # Pairs used for SfM reconstruction
    sfm_reconstruction_path = (
        hloc_output_dir / "sfm_reconstruction"
    )  # Path to reconstructed SfM

    # Feature extraction
    ## Extract local features in each data set image using Superpoint
    print("Extracting local features using Superpoint..")
    local_feature_conf = extract_features.confs[config.LOCAL_FEATURE_EXTRACTOR]
    local_features_path = extract_features.main(
        conf=local_feature_conf, image_dir=image_dir, export_dir=hloc_output_dir
    )

    print("Extracting global descriptors using NetVLad..")
    ## Extract global descriptors from each image using NetVLad
    global_descriptor_conf = extract_features.confs[config.GLOBAL_DESCRIPTOR_EXTRACTOR]
    global_descriptors_path = extract_features.main(
        conf=global_descriptor_conf, image_dir=image_dir, export_dir=hloc_output_dir
    )

    # Create SfM model using the local features just extracted

    ## Note: There is already an SfM model created using Colmap available. However, that is created using the RootSIFT features.
    ## SfM model needs to be created using the new features.

    ## Create matching pairs:
    ## Instead of creating image pairs by exhaustively searching through all possible pairs, we leverage the
    ## existing colmap model and form pairs by selecting the top 20 most covisibile neighbors for each image
    print("Forming pairs from covisibility..")
    pairs_from_covisibility.main(
        model=colmap_model_path, output=sfm_pairs_path, num_matched=20
    )

    ## Use the created pairs to match images and store the matching result in a match file
    print("Matching features using SuperGlue")
    match_features_conf = match_features.confs[config.MATCHER]
    sfm_matches_path = match_features.main(
        conf=match_features_conf,
        pairs=sfm_pairs_path,
        features=local_feature_conf[
            "output"
        ],  # This contains the file name where lcoal features are stored
        export_dir=hloc_output_dir,
    )

    try:
        ## Use the matches to reconstruct an SfM model
        print("Reconstructing Model..")
        reconstruction = triangulation.main(
            sfm_dir=sfm_reconstruction_path,
            reference_model=colmap_model_path,
            image_dir=image_dir,
            pairs=sfm_pairs_path,
            features=local_features_path,
            matches=sfm_matches_path,
        )
    # If the reconstruction fails, print the error trace
    except Exception as e:
        print("Reconstruction failed..Error trace:")
        print(e)
        return

    # Align the model using Manhattan
    print("Aligning the model using Manhattan..")
    map_aligner.align_colmap_model_manhattan(image_dir, sfm_reconstruction_path)

    # Elevate the model to ground level
    print("Elevate map to ground level..")
    map_cleaner.elevate_existing_reconstruction(sfm_reconstruction_path)

    # Clean the map by removing outliers and save it as a PCD
    print("Cleaning the map..")
    map_cleaner.clean_map(sfm_reconstruction_path)


def create_map_from_video(video_path, num_frames_perc=25):
    # Estimate the number of frames to extract
    probe = ffmpeg.probe(video_path)
    video_stream = next(
        stream for stream in probe["streams"] if stream["codec_type"] == "video"
    )
    frame_rate_num, frame_rate_den = video_stream["avg_frame_rate"].split("/")
    frame_rate = float(frame_rate_num) / float(frame_rate_den)
    duration = float(video_stream["duration"])
    num_frames_estimate = duration * frame_rate
    num_frames_to_extract = num_frames_estimate * (num_frames_perc / 100)
    num_frames_to_extract = int(min(num_frames_to_extract, num_frames_estimate))
    print(
        f"Estimated number of frames to extract: {num_frames_to_extract} / {int(num_frames_estimate)}"
    )

    # Call ns-process-data
    ns_process_output_dir = os.path.dirname(video_path)
    subprocess.run(
        [
            "ns-process-data",
            "video",
            "--data",
            str(video_path),
            "--output_dir",
            str(ns_process_output_dir),
            "--num-frames-target",
            str(num_frames_to_extract),
        ]
    )

    # Build the hloc map and features
    create_map_from_colmap_data(ns_process_output_dir)

    # Add the map to shared data
    load_cache.load_db_data(shared_data)


def create_map_from_reality_capture(data_dir):
    # TODO: Use reality capture poses

    image_dir = os.path.join(data_dir, "images")

    # Copy all images with pose information to a new directory
    image_copy_dir = os.path.join(data_dir, "images_with_pose")
    os.makedirs(image_copy_dir, exist_ok=True)
    for file in os.listdir(image_dir):
        if file.endswith(".xmp"):
            image_file = file.replace(".xmp", ".jpg")
            subprocess.run(
                ["cp", f"{os.path.join(image_dir, image_file)}", str(image_copy_dir)]
            )

    create_map_from_images(image_copy_dir)


def create_map_from_images(image_dir):
    # Call ns-process-data
    ns_process_output_dir = os.path.dirname(image_dir)
    subprocess.run(
        [
            "ns-process-data",
            "images",
            "--data",
            str(image_dir),
            "--output_dir",
            str(ns_process_output_dir),
        ]
    )

    # Build the hloc map and features
    create_map_from_colmap_data(ns_process_output_dir)

    # Add the map to shared data
    load_cache.load_db_data(shared_data)


def create_map_from_kiri_engine_output(data_dir):
    kiri_engine.build_map_from_kiri_output(data_dir)

    # Add the map to shared data
    load_cache.load_db_data(shared_data)


def create_map_from_polycam_output(data_dir):
    polycam.build_map_from_polycam_output(data_dir)

    # Add the map to shared data
    load_cache.load_db_data(shared_data)
