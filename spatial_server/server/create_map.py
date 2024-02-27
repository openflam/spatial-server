import os

from flask import Blueprint, request, render_template

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

    # Create the folder if it doesn't exist
    folder_path = os.path.join('data', 'map_data', name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # Save the uploaded video with the filename 'video.mp4' in the specified folder
    video_path = os.path.join(folder_path, 'video.mp4')
    video.save(video_path)

    # Call the map builder function
    executor.submit(map_creator.create_map_from_video, video_path)

    return 'Video uploaded and map building started'

    
    


