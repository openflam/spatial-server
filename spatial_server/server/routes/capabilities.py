from flask import Blueprint

bp = Blueprint("capabilities", __name__, url_prefix="/<map_name>/capabilities")


@bp.route("/", methods=["GET"])
def get_capabilities(map_name):
    return ["image"]
