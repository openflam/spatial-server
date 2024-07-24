import os
import pickle
import uuid

from flask import Blueprint, jsonify, request, render_template

bp = Blueprint("save_image_pose", __name__, url_prefix="/save_image_pose")


@bp.route("/", methods=["GET"])
def render_mapselect_page():
    map_names_list = os.listdir("data/map_data")
    return render_template(
        "aframe_data_collection/select_map.html", map_names_list=map_names_list
    )


@bp.route("/<name>", methods=["GET"])
def render_aframe_page(name):
    return render_template("aframe_data_collection/aframe.html", mapname=name)


@bp.route("/<name>", methods=["POST"])
def save_image_pose(name):
    # Download an image, save it and localize it against the map
    image = request.files["image"]
    aframe_camera_matrix_world = request.form["aframe_camera_matrix_world"]
    aframe_camera_matrix_world = list(map(float, aframe_camera_matrix_world.split(",")))

    # Create the folder if it doesn't exist
    random_id = str(uuid.uuid4())
    folder_path = os.path.join(
        "data", "map_data", name, "images_with_pose", str(random_id)
    )
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Save the uploaded image
    image_path = os.path.join(folder_path, "query_image.png")
    image.save(image_path)
    print("Image saved to", image_path)
    # Save the rest of the metadata
    location_data = {
        "aframe_camera_matrix_world": aframe_camera_matrix_world,
        "lat": request.form["lat"],
        "lon": request.form["lon"],
        "error_m": request.form["error_m"],
    }
    print(location_data)
    with open(os.path.join(folder_path, "location_data.pkl"), "wb") as f:
        print("Location data saved to", os.path.join(folder_path, "location_data.pkl"))
        pickle.dump(location_data, f)

    return jsonify("success")
