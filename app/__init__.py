from flask import Flask
from .utils import setup_logging

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='static')

    # Configure logging
    setup_logging(app)

    # Import the routes
    from .views import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
