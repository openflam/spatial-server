from flask import Blueprint


bp = Blueprint("capabilities", __name__, url_prefix="/<map_name>/capabilities")


@bp.route("/", methods=["GET"])
def get_capabilities(map_name):
    return {
        "commonName": map_name,
        "iconURL": f"/{map_name}/static/icon",
        "services": [
            {
                "name": "localization",
                "url": f"/{map_name}/localize",
                "types": ["image"],
            },
            {
                "name": "tileserver",
                "url": f"/{map_name}/static/tileserver",
            }
        ]
    }
