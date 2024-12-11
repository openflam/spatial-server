import os
from flask import Blueprint, request, render_template, url_for, jsonify
from spatial_server.server.tasks import (
    create_map_from_video_task,
    create_map_from_images_task,
    create_map_from_polycam_output_task,
    create_map_from_kiri_engine_output_task,
)
from spatial_server.hloc_localization.map_creation import map_creator
from spatial_server.hloc_localization import load_cache


bp = Blueprint("create_map", __name__, url_prefix="/create_map")


def _create_dataset_directory(name):
    folder_path = os.path.join("data", "map_data", name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path


def _save_file(file, folder_path, filename):
    file_path = os.path.join(folder_path, filename)
    file.save(file_path)
    return file_path


def _create_localization_url_file(dataset_name):
    # Create a file with the URL that will be used to query against the map
    folder_path = os.path.join("data", "map_data", dataset_name)

    with open(os.path.join(folder_path, "localization_url.txt"), "w") as f:
        localization_url = (
            request.url_root + url_for("localize.image_localize", name=dataset_name)[1:]
        )  # Remove the leading slash
        f.write(localization_url)


def _extract_zip(zip_file, folder_path, log_filepath=None):
    unzip_command = [
        "unzip",
        zip_file,
        "-d",
        folder_path,
    ]
    map_creator.run_command(unzip_command, log_filepath=log_filepath)
    return folder_path


def _save_and_extract_zip(request, extract_folder_name):
    zip_file = request.files["zip"]
    name = request.form.get("name", default="default_map")

    folder_path = _create_dataset_directory(name)
    zip_file_path = _save_file(zip_file, folder_path, "input.zip")
    log_file_path = os.path.join(folder_path, "log.txt")

    # If the log file already exists, delete it
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

    extract_folder_path = os.path.join(folder_path, extract_folder_name)
    _extract_zip(zip_file_path, extract_folder_path, log_file_path)

    _create_localization_url_file(name)

    return extract_folder_path, log_file_path


@bp.route("/", methods=["GET"])
def show_map_upload_form():
    return render_template("map_upload.html")


@bp.route("/video", methods=["POST"])
def upload_video():
    try:
        video = request.files["video"]
        name = request.form.get("name", default="default_map")
        num_frames_perc = request.form.get("num_frames_perc", default=25, type=float)
        
        folder_path = _create_dataset_directory(name)
        video_path = _save_file(video, folder_path, "video.mp4")
        log_filepath = os.path.join(folder_path, "log.txt")
        _create_localization_url_file(name)
        # Enqueue Celery task
        task = create_map_from_video_task.delay(video_path, num_frames_perc, log_filepath, name)
        return jsonify({"message": "Video uploaded and map building started", "task_id": task.id}), 200
    
    except Exception as e:
        return f"Error uploading video. See server logs for details: {e}", 500


@bp.route("/images", methods=["POST"])
def upload_images():
    try:
        zip_file = request.files.get("zip")
        if not zip_file:
            return jsonify({"error": "No zip file provided"}), 400
        extract_folder_path, log_file_path = _save_and_extract_zip(
            request, extract_folder_name="images_org"
        )
        name = request.form.get("name", default="default_map")
        # Enqueue Celery task
        task = create_map_from_images_task.delay(extract_folder_path, name)
        return jsonify({"message": "Images uploaded and map building started", "task_id": task.id}), 200
    
    except Exception as e:
        return f"Error uploading images. See server logs for details: {e}", 500


@bp.route("/polycam", methods=["POST"])
def upload_polycam():
    try:
        zip_file = request.files.get("zip")
        if not zip_file:
            return jsonify({"error": "No zip file provided"}), 400
        polycam_directory, log_file_path = _save_and_extract_zip(
            request, extract_folder_name="polycam_data"
        )
        name = request.form.get("name", default="default_map")
        # Enqueue Celery task
        task = create_map_from_polycam_output_task.delay(polycam_directory, log_file_path, name)
        return jsonify({"message": "Polycam output uploaded and map building started", "task_id": task.id}), 200
    
    except Exception as e:
        return f"Error uploading Polycam. See server logs for details: {e}", 500


@bp.route("/kiriengine", methods=["POST"])
def upload_kiri_engine():
    try:
        zip_file = request.files.get("zip")
        if not zip_file:
            return jsonify({"error": "No zip file provided"}), 400
        kiri_directory, log_file_path = _save_and_extract_zip(
            request, extract_folder_name="kiriengine_data"
        )
        name = request.form.get("name", default="default_map")
        # Enqueue Celery task
        task = create_map_from_kiri_engine_output_task.delay(kiri_directory, name)
        return jsonify({"message": "Kiri Engine output uploaded and map building started", "task_id": task.id}), 200
    
    except Exception as e:
        return f"Error uploading Kiri Engine output. See server logs for details: {e}", 500


@bp.route("/status/<task_id>", methods=["GET"])
def get_task_status(task_id):
    from celery.result import AsyncResult
    from spatial_server.celery_app import celery_app
    result = AsyncResult(task_id, app=celery_app)
    response = {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.status == "SUCCESS" else None,
    }
    return jsonify(response), 200
