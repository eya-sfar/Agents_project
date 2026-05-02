"""
api/app.py
Flask application factory with Flask-RESTX for auto-documented REST API.
"""
from flask import Flask
from flask_cors import CORS
from flask_restx import Api

from api.routes.researchers import ns as researchers_ns
from api.routes.labs import ns as labs_ns
from api.routes.publications import ns as publications_ns
from api.routes.clusters import ns as clusters_ns
from api.routes.agents import ns as agents_ns
from config.settings import settings


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.flask.SECRET_KEY
    app.config["PROPAGATE_EXCEPTIONS"] = True

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    api = Api(
        app,
        version="1.0",
        title="🔭 University Observatory API",
        description="Multi-Agent Research & Lab Management System",
        doc="/docs",
        prefix="/api/v1",
    )

    api.add_namespace(researchers_ns)
    api.add_namespace(labs_ns)
    api.add_namespace(publications_ns)
    api.add_namespace(clusters_ns)
    api.add_namespace(agents_ns)

    @app.route("/health")
    def health():
        return {"status": "ok", "version": "1.0"}

    return app
