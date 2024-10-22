import contextlib
import os
from pathlib import Path
from threading import Thread

from flask import Blueprint, jsonify, request, render_template

from .. import shared_data
from spatial_server.hloc_localization.scale_adjustment.get_scale import (
    get_scale_from_image_pose_data,
)
from spatial_server.hloc_localization.scale_adjustment.scale_existing_model import (
    scale_existing_model,
)
from spatial_server.hloc_localization.map_creation.map_transforms import (
    rotate_and_elevate,
)


bp = Blueprint("scale_map", __name__, url_prefix="/scale_map")


@bp.route("/", methods=["GET"])
def render_scale_map_select():
    map_names_list = os.listdir("data/map_data")
    return render_template("scale_map.html", map_names_list=map_names_list)


@bp.route("/<mapname>", methods=["GET"])
def scale_map(mapname):
    Thread(target=scale_map_task, args=(mapname,)).start()
    return "Scale map started in the background..See logs for result", 200


def scale_map_task(mapname):
    map_directory = Path(os.path.join("data", "map_data", mapname))
    log_filepath = map_directory / "log.txt"
    output_file_obj = open(log_filepath, "a")

    with contextlib.redirect_stdout(output_file_obj), contextlib.redirect_stderr(
        output_file_obj
    ):
        try:
            # Get the scale factor
            print("Getting scale factor..")
            get_scale_from_image_pose_data(mapname, shared_data)

            # If the scaled reconstruction already exists, the scale obtained is for that model, so scale that instead
            hloc_directory = map_directory / "hloc_data"
            model_path = hloc_directory / "scaled_sfm_reconstruction"
            if not model_path.exists():
                model_path = hloc_directory / "sfm_reconstruction"

            # Scale the model with the scale factor
            print(f"Scaling the existing model path at {model_path} map..")
            scale_existing_model(model_path)

            # Save the model as pcd file
            print("Saving PCD of the scaled map..")
            rotate_and_elevate(
                model_path, rotation=None, elevate=False, create_pcd=True
            )
            print("Map scaled successfully..")

            return "Map scaled successfully", 200

        except Exception as e:
            print("Error when scaling the map..Error trace:")
            print(e)
            return "Error occured when scaling. See logs for details", 500
