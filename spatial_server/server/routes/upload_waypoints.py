import os

from flask import Blueprint, request, render_template, url_for

bp = Blueprint('upload_waypoints', __name__, url_prefix='/upload_waypoints')


@bp.route('/', methods=['POST', 'GET'])
def upload_waypoints():
    if request.method == 'GET':
        map_names_list = os.listdir('data/map_data')
        return render_template('upload_waypoints.html', map_names_list=map_names_list)

    if request.method == 'POST':
        waypoints = request.files['waypoints_csv']
        name = request.form.get('map_name')

        folder_path = os.path.join('data', 'map_data', name)
        waypoints_path = os.path.join(folder_path, 'waypoints_graph.csv')
        waypoints.save(waypoints_path)

        return 'Waypoints uploaded successfully'
