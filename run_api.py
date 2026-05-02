"""
run_api.py
Entry point for the Flask REST API.
"""
from database.connection import init_db
from api.app import create_app
from config.settings import settings
from utils.logger import logger


def main():
    logger.info("Initialising database …")
    init_db()

    app = create_app()
    logger.info(f"Starting API on {settings.flask.HOST}:{settings.flask.PORT}")
    logger.info(f"Swagger docs available at http://localhost:{settings.flask.PORT}/docs")

    app.run(
        host=settings.flask.HOST,
        port=settings.flask.PORT,
        debug=settings.flask.DEBUG,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
