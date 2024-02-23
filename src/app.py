##########################################################
# Example server application has the following routes that is exposed to any client connecting to the server:
# '/upload'
#       Accepts POST requests with the video file and 'name' field.
#       Saves the uploaded file and initiates the map building process. 
# '/localize'
#       Accepts POST requests with the image file and 'name' field.
#       Localizes it against the map and returns the pose.
# Note: All routes are CORS enabled (CORS = Cross-Origin Resource Sharing)
##########################################################


import os
import pickle
import uuid

from flask import Flask, request, jsonify
from flask_cors import CORS
from concurrent.futures import ProcessPoolExecutor

import map_creator
import localizer

app = Flask(__name__)
CORS(app)

# Create an executor to run map building in the background
executor = ProcessPoolExecutor()

# Receive the uploaded video and create the map
@app.route('/upload', methods=['POST'])
def upload_video():

    video = request.files['video']
    name = request.form['name']

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

# Localize an image against the map
@app.route('/localize', methods=['POST'])
def localize():
    # Download an image, save it and localize it against the map
    image = request.files['image']
    name = request.form.get('name')
    aframe_camera_matrix_world = request.form.get('aframe_camera_matrix_world')
    aframe_camera_matrix_world = list(map(float, aframe_camera_matrix_world.split(',')))

    # Create the folder if it doesn't exist
    random_id = str(uuid.uuid4())
    folder_path = os.path.join('data', 'query_data', name, str(random_id))
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # Save the uploaded image
    image_path = os.path.join(folder_path, 'query_image.png')
    image.save(image_path)
    # Save aframe camera matrix
    with open(os.path.join(folder_path, 'aframe_camera_matrix_world.pkl'), 'wb') as f:
        pickle.dump(aframe_camera_matrix_world, f)

    # Call the localization function
    pose = localizer.localize(image_path, name, aframe_camera_matrix_world)
    print("Localizer Result: ", pose)
    return jsonify(pose)

if __name__ == '__main__':
    app.run(debug = True, host = '0.0.0.0', port=8001)
