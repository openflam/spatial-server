import contextlib
import os
from pathlib import Path
from threading import Thread

from flask import Blueprint, render_template

from .. import shared_data
from spatial_server.hloc_localization.map_creation.map_transforms import (
    rotate_and_elevate,
)


bp = Blueprint("rotate_map", __name__, url_prefix="/rotate_map")


@bp.route("/", methods=["GET"])
def render_rotate_map_select():
    map_names_list = os.listdir("data/map_data")
    return render_template("rotate_map.html", map_names_list=map_names_list)


@bp.route("/<mapname>", methods=["GET"])
def rotate_map(mapname):
    """
    Rotate map by 180 degrees along the x axis and elevate it.
    """
    Thread(target=rotate_map_task, args=(mapname,)).start()
    return "Rotate map started in the background..See logs for result", 200


def rotate_map_task(mapname):
    map_directory = Path(os.path.join("data", "map_data", mapname))
    log_filepath = map_directory / "log.txt"
    output_file_obj = open(log_filepath, "a")

    with contextlib.redirect_stdout(output_file_obj), contextlib.redirect_stderr(
        output_file_obj
    ):
        try:
            # If the scaled reconstruction already exists, the scale obtained is for that model, so scale that instead
            hloc_directory = map_directory / "hloc_data"
            model_path = hloc_directory / "scaled_sfm_reconstruction"
            if not model_path.exists():
                model_path = hloc_directory / "sfm_reconstruction"

            print(
                f"Rotating and elevating the existing model path at {model_path} map.."
            )
            rotate_and_elevate(
                model_path, rotation="x180", elevate=True, create_pcd=True
            )
            print("Map rotated successfully..")

            return "Map scaled successfully", 200

        except Exception as e:
            print("Error when scaling the map..Error trace:")
            print(e)
            return "Error occured when scaling. See logs for details", 500
