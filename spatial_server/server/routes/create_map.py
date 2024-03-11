import os

from flask import Blueprint, request, render_template, url_for

from spatial_server.hloc_localization import map_creator
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


@bp.route('/', methods=['GET'])
def show_map_upload_form():
    return render_template('map_upload.html')

@bp.route('/video', methods=['POST'])
def upload_video():
    video = request.files['video']
    name = request.form.get('name', default='default_map')
    num_frames_perc = request.form.get('num_frames_perc', default=0.25, type=float)

    folder_path = _create_dataset_directory(name)
    video_path = _save_file(video, folder_path, 'video.mp4')
    _create_localization_url_file(name)

    # Call the map builder function
    executor.submit(map_creator.create_map_from_video, video_path, num_frames_perc)

    return 'Video uploaded and map building started'

@bp.route('/images', methods=['POST'])
def upload_images():
    images_zip = request.files['imagesZip']
    name = request.form.get('name', default='default_map')

    folder_path = _create_dataset_directory(name)
    images_zip_path = _save_file(images_zip, folder_path, 'images.zip')

    images_folder_path = os.path.join(folder_path, 'images')
    _extract_zip(images_zip_path, images_folder_path)

    _create_localization_url_file(name)
    
    # Call the map builder function
    executor.submit(map_creator.create_map_from_images, images_folder_path)

    return 'Images uploaded and map building started'
