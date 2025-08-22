"""
Application factory for the Foundations of Resilience Tracker.

This module provides a function to create and configure the Flask
application. All extensions (SQLAlchemy, Migrate, JWT) are initialised
here. Individual blueprints for different parts of the API are
registered inside the factory to allow for modular development and
unit testing.

Environment variables control the database connection and secret key.
In production (e.g. on Render), set ``DATABASE_URL`` and
``JWT_SECRET_KEY`` in your environment. A default configuration is
provided for development, using SQLite when no database URL is
available.
"""

from __future__ import annotations

import os
from datetime import timedelta

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

# instantiate extensions without binding them to an app yet.  They will
# be bound in create_app().  This pattern avoids issues with circular
# imports and makes testing easier.
from .db import db  # use shared db object from db.py
migrate = Migrate()
jwt = JWTManager()


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure a Flask application.

    Parameters
    ----------
    test_config: dict | None, optional
        Optional configuration overrides used when running tests.

    Returns
    -------
    Flask
        A configured Flask application instance.
    """
    app = Flask(__name__)

    # Default configuration. Override using environment variables or
    # by passing a ``test_config`` mapping.
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///resilience.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=os.environ.get("JWT_SECRET_KEY", "please-change-this-secret-key"),
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(days=1),
    )

    if test_config:
        app.config.update(test_config)

    # Initialise extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Register custom error handlers
    from .errors import register_error_handlers
    register_error_handlers(app)

    # Register blueprints. Importing here avoids circular imports.
    from .routes.auth import auth_bp
    from .routes.clients import clients_bp
    from .routes.habits import habits_bp
    from .routes.assessments import assessments_bp
    from .routes.client_habits import client_habits_bp
    from .routes.insights import insights_bp

    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(clients_bp, url_prefix="/api")
    app.register_blueprint(habits_bp, url_prefix="/api")
    app.register_blueprint(assessments_bp, url_prefix="/api")
    app.register_blueprint(client_habits_bp, url_prefix="/api")
    app.register_blueprint(insights_bp, url_prefix="/api")

    # Provide a simple health check route
    @app.route("/api/health")
    def health_check() -> dict[str, str]:
        """Return a simple health check response.

        This endpoint can be used by deployment platforms to verify
        that the application has started correctly.
        """
        return {"status": "ok"}

    return app