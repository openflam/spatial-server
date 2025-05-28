import os
import json

from flask import Blueprint, jsonify


bp = Blueprint("capabilities", __name__, url_prefix="/<map_name>/capabilities")


@bp.route("/", methods=["GET"])
def get_capabilities(map_name):
    capabilities_path = os.path.join("data", "map_data", map_name, "capabilities.json")

    if os.path.isfile(capabilities_path):
        with open(capabilities_path, "r") as file:
            capabilities = json.load(file)
        return jsonify(capabilities)

    # Default response
    return {
        "commonName": map_name,
        "iconURL": f"/static/icon",
        "services": [
            {
                "name": "localization",
                "url": f"/localize",
                "types": ["image"],
            },
            {
                "name": "tileserver",
                "url": f"/static/tileset",
            }
        ]
    }
