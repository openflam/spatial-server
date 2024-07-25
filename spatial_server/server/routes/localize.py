import os
import pickle
import uuid

from flask import Blueprint, request, jsonify

from spatial_server.hloc_localization import localizer

bp = Blueprint("localize", __name__, url_prefix="/localize")


@bp.route("/image/<name>", methods=["POST"])
def image_localize(name):
    # Download an image, save it and localize it against the map
    image = request.files["image"]

    # Create the folder if it doesn't exist
    random_id = str(uuid.uuid4())
    folder_path = os.path.join("data", "query_data", name, str(random_id))
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Save the uploaded image
    image_path = os.path.join(folder_path, "query_image.png")
    image.save(image_path)

    # Call the localization function
    pose = localizer.localize(image_path, name)
    # print("Localizer Result: ", pose)
    return jsonify(pose)
