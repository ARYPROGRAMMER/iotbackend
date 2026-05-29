from concurrent.futures import ThreadPoolExecutor

from flask import Flask, jsonify

from stealthera_api.config import Config
from stealthera_api.docs_api import docs_bp
from stealthera_api.dashboard.routes import dashboard_bp
from stealthera_api.iwown.commands import commands_bp
from stealthera_api.iwown.ingest import ingest_bp
from stealthera_api.logging_config import configure_logging
from stealthera_api.request_logging import register_request_logging
from stealthera_api.storage import create_store


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    config_class.load_runtime_env(app)
    configure_logging(app)
    register_request_logging(app)
    app.ingest_executor = ThreadPoolExecutor(max_workers=4)
    app.store = create_store(app.config, app.logger)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(ingest_bp)
    app.register_blueprint(commands_bp)
    app.register_blueprint(docs_bp)

    @app.get("/healthz")
    def healthz():
        return jsonify(
            {
                "status": "ok",
                "storage": app.store.name,
                "service": "stealthera-api",
            }
        )

    return app
