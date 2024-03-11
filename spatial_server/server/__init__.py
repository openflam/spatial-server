from concurrent.futures import ProcessPoolExecutor

from flask import Flask
from flask_cors import CORS

from .config import Config

# Create an executor to run map building in the background
executor = ProcessPoolExecutor()

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        **Config
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
    
    from .routes import localize
    app.register_blueprint(localize.bp)

    from .routes import create_map
    app.register_blueprint(create_map.bp)

    from .routes import register_with_discovery
    app.register_blueprint(register_with_discovery.bp)

    from .routes import download_map
    app.register_blueprint(download_map.bp)

    from .routes import render_template
    app.register_blueprint(render_template.bp)

    CORS(app)

    return app