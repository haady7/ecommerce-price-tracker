from flask import Flask
from app.config import Config
from app.routes import api
from app.scheduler import start_scheduler

def create_app(start_background_scheduler=True):
    app = Flask(__name__, template_folder="templates", static_folder="../static")
    app.config.from_object(Config)
    app.register_blueprint(api)
    if start_background_scheduler:
        start_scheduler(app)
    return app
