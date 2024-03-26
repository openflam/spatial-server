import os

from flask import (
    Blueprint, current_app as app, render_template, request, url_for
)
import requests

bp = Blueprint('register_with_discovery', __name__, url_prefix='/register_with_discovery')

@bp.route('/', methods=['POST', 'GET'])
def register_with_discovery():
    if request.method == 'GET':
        map_names_list = os.listdir('data/map_data')
        urls_available_list = [
            url_for('localize.image_localize', name=map_name)[1:] # Remove the leading slash
            for map_name in map_names_list
        ]
        return render_template('register_with_discovery.html', urls_available_list=urls_available_list)

    latitude = float(request.form['latitude'])
    longitude = float(request.form['longitude'])
    hostname = request.form['hostname']
    resolution = int(request.form['resolution'])

    # Call the server discovery service to register the server
    server_discovery_url = app.config['SERVER_DISCOVERY_URL']
    server_discovery_url += '/register'
    # Post the server data to the server discovery service
    response = requests.post(
        server_discovery_url, 
        data={
            'latitude': latitude, 
            'longitude': longitude, 
            'hostname': hostname, 
            'resolution': resolution
            },
        verify=False
        )

    return response.text

    