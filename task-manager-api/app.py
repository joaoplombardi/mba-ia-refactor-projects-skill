"""Composition root.

Creates the app, wires config, database, blueprints and the error handler.
"""
import logging

from flask import Flask
from flask_cors import CORS

from config.settings import settings
from database import db
from middlewares.error_handler import register_error_handlers
from routes.category_routes import category_bp
from routes.report_routes import report_bp
from routes.task_routes import task_bp
from routes.user_routes import user_bp
from services.notification_service import NullEmailClient, SmtpEmailClient
from utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


def build_email_client():
    if not settings.EMAIL_ENABLED:
        return NullEmailClient()
    return SmtpEmailClient(
        settings.EMAIL_HOST,
        settings.EMAIL_PORT,
        settings.EMAIL_USER,
        settings.EMAIL_PASSWORD,
    )


def create_app(config_object=settings):
    logging.basicConfig(
        level=getattr(logging, config_object.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    config_object.validate()

    app = Flask(__name__)
    app.config.from_object(config_object)

    CORS(app, origins=config_object.CORS_ORIGINS)
    db.init_app(app)

    app.register_blueprint(task_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(report_bp)

    @app.route("/health")
    def health():
        return {"status": "ok", "timestamp": str(utc_now())}

    @app.route("/")
    def index():
        return {"message": "Task Manager API", "version": config_object.VERSION}

    # Registered last, so it catches everything the blueprints raise.
    register_error_handlers(app)

    app.extensions["email_client"] = build_email_client()

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=settings.DEBUG, host=settings.HOST, port=settings.PORT)
