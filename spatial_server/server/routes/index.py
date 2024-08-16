from flask import Blueprint, render_template

bp = Blueprint("index", __name__)


@bp.route("/", methods=["GET"])
def render_index():
    return render_template("index.html")
