import os

from flask import Blueprint, request
import pandas as pd

bp = Blueprint("download_waypoints", __name__, url_prefix="/<map_name>/waypoints")


@bp.route("/", methods=["GET"])
def download_waypoints(map_name):
    waypoints_graph_filepath = os.path.join(
        "data", "map_data", map_name, "waypoints_graph.csv"
    )
    waypoints_graph_df = pd.read_csv(waypoints_graph_filepath)

    # Convert to a list of "names" and "positions". The "names" are the waypoint IDs.
    waypoints_graph_df = waypoints_graph_df[["id", "x", "y", "z", "neighbors"]].to_dict(
        orient="records"
    )
    waypoints_graph_df = [
        {
            "name": waypoint["id"],
            "position": [waypoint["x"], waypoint["y"], waypoint["z"]],
            "neighbors": waypoint["neighbors"].split(";"),
        }
        for waypoint in waypoints_graph_df
    ]

    return waypoints_graph_df
