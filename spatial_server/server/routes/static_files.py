import os
from io import BytesIO

from flask import Blueprint, send_file, request


bp = Blueprint("static_files", __name__, url_prefix="/<map_name>/static")


@bp.route("/icon", methods=["GET"])
def get_icon(map_name):
    """
    Serve the icon for the map.
    """
    directory = os.path.join("data", "map_data", map_name)

    map_icon_path = os.path.join(directory, "icon.png")
    default_icon_path = os.path.join("spatial_server", "server", "static", "images", "default_icon.jpg")

    map_icon_path = os.path.abspath(map_icon_path)
    default_icon_path = os.path.abspath(default_icon_path)

    if os.path.exists(map_icon_path):
        return send_file(map_icon_path, mimetype="image/png")
    else:
        return send_file(default_icon_path, mimetype="image/jpeg")


@bp.route("/tilecontent", methods=["GET"])
def get_tilecontent(map_name):
    """
    Serve the tile GLB for the map.
    """
    directory = os.path.join("data", "map_data", map_name)
    map_glb_path = os.path.join(directory, "polycam_data", "raw.glb")

    map_glb_path = os.path.abspath(map_glb_path)

    if os.path.exists(map_glb_path):
        return send_file(map_glb_path, mimetype="model/gltf-binary")
    else:
        return send_file(BytesIO(), mimetype="model/gltf-binary")


@bp.route("/tileset", methods=["GET"])
def get_tileserver(map_name):
    """
    Serve the tileserver json for the map.
    """
    directory = os.path.join("data", "map_data", map_name)
    map_tileserver_path = os.path.join(directory, "tileset.json")

    map_tileserver_path = os.path.abspath(map_tileserver_path)

    if os.path.exists(map_tileserver_path):
        return send_file(map_tileserver_path, mimetype="application/json")
    else:
        return send_file(BytesIO(), mimetype="application/json")
