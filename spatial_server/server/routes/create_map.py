import os

from flask import Blueprint, request, render_template, url_for

from spatial_server.hloc_localization import map_creator
from spatial_server.server import executor

bp = Blueprint('create_map', __name__, url_prefix='/create_map')

@bp.route('/', methods=['GET'])
def show_map_upload_form():
    return render_template('video_upload.html')

@bp.route('/video', methods=['POST'])
def upload_video():
    video = request.files['video']
    name = request.form.get('name', default='default_map')
    num_frames_perc = request.form.get('num_frames_perc', default=0.25, type=float)

    # Create the folder if it doesn't exist
    folder_path = os.path.join('data', 'map_data', name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # Save the uploaded video with the filename 'video.mp4' in the specified folder
    video_path = os.path.join(folder_path, 'video.mp4')
    video.save(video_path)

    # Create a file with the URL that will be used to query against the map
    with open(os.path.join(folder_path, 'localization_url.txt'), 'w') as f:
        localization_url = request.url_root \
            + url_for('localize.image_localize', name=name)[1:] # Remove the leading slash
        f.write(localization_url)

    # Call the map builder function
    executor.submit(map_creator.create_map_from_video, video_path, num_frames_perc)

    return 'Video uploaded and map building started'

    
    


