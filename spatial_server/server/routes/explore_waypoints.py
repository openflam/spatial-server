import os
import pickle
import uuid

from flask import Blueprint, jsonify, request, render_template

bp = Blueprint("explore_waypoints", __name__, url_prefix="/explore_waypoints")


@bp.route("/", methods=["GET"])
def render_mapselect_page():
    map_names_list = os.listdir("data/map_data")
    return render_template(
        "waypoints_explorer/select_map.html", map_names_list=map_names_list
    )


@bp.route("/<name>", methods=["GET"])
def render_aframe_page(name):
    return render_template("waypoints_explorer/aframe.html", mapname=name)
