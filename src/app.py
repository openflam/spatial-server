##########################################################
# Example server application has the following routes that is exposed to any client connecting to the server:
# '/upload'
#       Accepts POST requests with the video file and 'name' field.
#       Saves the uploaded file and initiates the map building process. 
#
# Note: All routes are CORS enabled (CORS = Cross-Origin Resource Sharing)
##########################################################


import os

from flask import Flask, request
from flask_cors import CORS
from concurrent.futures import ProcessPoolExecutor

from map_creator import create_map_from_video

app = Flask(__name__)
CORS(app)

# Create an executor to run map building in the background
executor = ProcessPoolExecutor()

# Receive the uploaded video
@app.route('/upload', methods=['POST'])
def upload_video():

    video = request.files['video']
    name = request.form.get('name', '')

    # Create the folder if it doesn't exist
    folder_path = os.path.join('data', 'map_data', name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Save the uploaded video with the filename 'video.mp4' in the specified folder
    video_path = os.path.join(folder_path, 'video.mp4')
    video.save(video_path)
    
    # Call the map builder function
    executor.submit(create_map_from_video, video_path)

    return 'Video uploaded and map building started'

if __name__ == '__main__':
    app.run(debug = True, host = '0.0.0.0', port=8001)
