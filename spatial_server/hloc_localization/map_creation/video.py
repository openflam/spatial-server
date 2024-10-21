import contextlib
from pathlib import Path
import logging
import sys

import ffmpeg

from . import map_creator
from spatial_server.utils.run_command import run_command
from spatial_server.utils.print_log import print_log
from third_party.hloc.hloc import logger as hloc_logger, handler as hloc_default_handler


def create_map_from_video(video_path, num_frames_perc=25, log_filepath=None):
    # Define directories
    map_directory = Path(video_path).parent
    ns_data_directory = map_directory / "ns_data"
    hloc_data_directory = map_directory / "hloc_data"

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
    print_log(
        f"Estimated number of frames to extract: {num_frames_to_extract} / {int(num_frames_estimate)}",
        log_filepath,
    )

    # Call ns-process-data
    ns_process_data_command = [
        "ns-process-data",
        "video",
        "--data",
        str(video_path),
        "--output_dir",
        str(ns_data_directory),
        "--num-frames-target",
        str(num_frames_to_extract),
    ]
    print_log("Running ns-process-data (takes 10-15 mins)...", log_filepath)
    run_command(
        ns_process_data_command,
        log_filepath=log_filepath,
    )

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
                ns_process_output_dir=ns_data_directory,
                output_dir=hloc_data_directory,
            )
            print("Map creation COMPLETED...")
        except Exception as e:
            print("Map creation from colmap FAILED...ERROR:")
            print(e)
    if log_filepath is not None:
        output_file_obj.close()
