from io import BytesIO
import os
import zipfile

from flask import Blueprint, render_template, send_file

bp = Blueprint("download_map", __name__, url_prefix="/download_map")


@bp.route("/<map_name>", methods=["GET"])
def download_map(map_name, download_sfm_recnstruction=False):
    directory = os.path.join("data", "map_data", map_name)

    all_filepaths = []
    if download_sfm_recnstruction:
        hloc_directory = os.path.join(
            directory, "hloc_data", "scaled_sfm_reconstruction"
        )
        if not os.path.exists(hloc_directory):
            hloc_directory = os.path.join(directory, "hloc_data", "sfm_reconstruction")
        images_directory = os.path.join(directory, "images_8")

        # List of filepaths to include in the zip file with their arc names
        point_cloud_filepaths = [
            (os.path.join(hloc_directory, "cameras.bin"), "point_cloud/cameras.bin"),
            (os.path.join(hloc_directory, "images.bin"), "point_cloud/images.bin"),
            (os.path.join(hloc_directory, "points3D.bin"), "point_cloud/points3D.bin"),
        ]

        image_filepaths = [
            (os.path.join(images_directory, filename), os.path.join("images", filename))
            for filename in os.listdir(images_directory)
        ]

        all_filepaths = all_filepaths + point_cloud_filepaths + image_filepaths

    localizer_url_filepath = [
        (os.path.join(directory, "localization_url.txt"), "localization_url.txt")
    ]

    point_cloud_pcd_filepath = [
        (os.path.join(directory, "hloc_data", "points.pcd"), "point_cloud.pcd")
    ]

    all_filepaths = all_filepaths + localizer_url_filepath + point_cloud_pcd_filepath

    # If waypoints_graph.csv exists, add it to the zip file
    waypoints_graph_filepath = os.path.join(directory, "waypoints_graph.csv")
    if os.path.exists(waypoints_graph_filepath):
        all_filepaths.append((waypoints_graph_filepath, "waypoints_graph.csv"))

    # Create a zip file of the map data
    # Create a BytesIO object to store the zip file in memory
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, "w") as zip_file:
        for filepath, arcname in all_filepaths:
            zip_file.write(filepath, arcname=arcname)

    # Move the file pointer to the beginning of the BytesIO object
    memory_file.seek(0)

    # Return the zip file as a download
    return send_file(
        memory_file,
        mimetype="application/zip",
        download_name="map.zip",
        as_attachment=True,
    )


@bp.route("/", methods=["GET"])
def download_map_form():
    map_names_list = os.listdir("data/map_data")
    return render_template("download_map.html", map_names_list=map_names_list)
