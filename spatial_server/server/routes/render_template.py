from flask import Blueprint, request, render_template

bp = Blueprint("render_template", __name__, url_prefix="/render_template")


@bp.route("/", methods=["GET"])
def render_template_route():
    name = request.args.get("name")
    return render_template(name)
