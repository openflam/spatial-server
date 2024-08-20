from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import os

from flask import Flask
from flask_cors import CORS

from .config import Config
from spatial_server.hloc_localization import load_cache

# Create an executor to run map building in the background
executor = ProcessPoolExecutor(mp_context=multiprocessing.get_context("spawn"))

# Shared data - data that is shared between requests.
# TODO: This is a hack. Find a better way to do this.
shared_data = {}


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(SECRET_KEY="dev", **Config)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    load_cache.load_ml_models(shared_data)
    load_cache.load_db_data(shared_data)

    from .routes import index

    app.register_blueprint(index.bp)

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

    from .routes import save_image_pose

    app.register_blueprint(save_image_pose.bp)

    from .routes import upload_waypoints

    app.register_blueprint(upload_waypoints.bp)

    from .routes import download_waypoints

    app.register_blueprint(download_waypoints.bp)

    from .routes import explore_waypoints

    app.register_blueprint(explore_waypoints.bp)

    from .routes import capabilities

    app.register_blueprint(capabilities.bp)

    # Read the BEHIND_PROXY environment variable
    behind_proxy = os.getenv("BEHIND_PROXY", "false").lower() == "true"
    print("BEHIND_PROXY:", behind_proxy)
    if behind_proxy:
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    CORS(app)

    return app
