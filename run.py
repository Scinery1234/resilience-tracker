"""
Entry point for running the Resilience Tracker Flask application.

This module imports the application factory and starts the development
server when executed directly. In production (e.g. when deployed to
Render), a WSGI server like gunicorn should import ``create_app`` from
``app`` and serve it instead.
"""

from app import create_app, db

app = create_app()

if __name__ == "__main__":
    # Only create the database tables automatically in local
    # development when running this module directly. Production
    # deployments should manage migrations separately.
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)