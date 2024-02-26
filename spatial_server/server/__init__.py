from concurrent.futures import ProcessPoolExecutor

from flask import Flask
from flask_cors import CORS

# Create an executor to run map building in the background
executor = ProcessPoolExecutor()

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev'
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
    
    from . import localize
    app.register_blueprint(localize.bp)

    from . import create_map
    app.register_blueprint(create_map.bp)

    CORS(app)

    return app