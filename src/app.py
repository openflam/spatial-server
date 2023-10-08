import os

from flask import Flask, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Receive the uploaded video
@app.route('/', methods=['POST'])
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

    return 'Video uploaded and processing started'

if __name__ == '__main__':
    app.run(debug = False, host = '0.0.0.0', port=8001)
