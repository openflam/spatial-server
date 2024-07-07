import os

from flask import Blueprint, request, render_template, url_for

from spatial_server.hloc_localization.map_creation import map_creator
from spatial_server.server import executor

bp = Blueprint('create_map', __name__, url_prefix='/create_map')


def _create_dataset_directory(name):
    folder_path = os.path.join('data', 'map_data', name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path


def _save_file(file, folder_path, filename):
    file_path = os.path.join(folder_path, filename)
    file.save(file_path)
    return file_path


def _create_localization_url_file(dataset_name):
    # Create a file with the URL that will be used to query against the map
    folder_path = os.path.join('data', 'map_data', dataset_name)

    with open(os.path.join(folder_path, 'localization_url.txt'), 'w') as f:
        localization_url = request.url_root \
            + url_for('localize.image_localize', name=dataset_name)[1:] # Remove the leading slash
        f.write(localization_url)


def _extract_zip(zip_file, folder_path):
    os.system(f'unzip {zip_file} -d {folder_path}')
    return folder_path


def _save_and_extract_zip(request, extract_folder_name):
    zip_file = request.files['zip']
    name = request.form.get('name', default='default_map')
    
    folder_path = _create_dataset_directory(name)
    zip_file_path = _save_file(zip_file, folder_path, 'input.zip')
    
    extract_folder_path = os.path.join(folder_path, extract_folder_name)
    _extract_zip(zip_file_path, extract_folder_path)
    
    _create_localization_url_file(name)
    
    return extract_folder_path


@bp.route('/', methods=['GET'])
def show_map_upload_form():
    return render_template('map_upload.html')

@bp.route('/video', methods=['POST'])
def upload_video():
    video = request.files['video']
    name = request.form.get('name', default='default_map')
    num_frames_perc = request.form.get('num_frames_perc', default=25, type=float)

    folder_path = _create_dataset_directory(name)
    video_path = _save_file(video, folder_path, 'video.mp4')
    _create_localization_url_file(name)

    # Call the map builder function
    executor.submit(map_creator.create_map_from_video, video_path, num_frames_perc)

    return 'Video uploaded and map building started'

@bp.route('/images', methods=['POST'])
def upload_images():
    images_folder_path = _save_and_extract_zip(request, extract_folder_name = 'images_org')
    # Call the map builder function
    executor.submit(map_creator.create_map_from_images, images_folder_path)

    return 'Images uploaded and map building started'

@bp.route('/polycam', methods=['POST'])
def upload_polycam():
    polycam_directory = _save_and_extract_zip(request, extract_folder_name = 'polycam_data')
    # Call the map builder function
    executor.submit(map_creator.create_map_from_polycam_output, polycam_directory)
    return 'Polycam output uploaded and map building started'

@bp.route('/kiriengine', methods=['POST'])
def upload_kiri_engine():
    kiri_directory = _save_and_extract_zip(request, extract_folder_name = 'kiriengine_data')
    # Call the map builder function
    executor.submit(map_creator.create_map_from_polycam_output, kiri_directory)
    return 'Polycam output uploaded and map building started'