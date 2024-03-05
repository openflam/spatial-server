from flask import (
    Blueprint, current_app as app, render_template, request
)
import requests

bp = Blueprint('register_with_discovery', __name__, url_prefix='/register_with_discovery')

@bp.route('/', methods=['POST', 'GET'])
def register_with_discovery():
    if request.method == 'GET':
        return render_template('register_with_discovery.html')

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
            })

    return response.text

    