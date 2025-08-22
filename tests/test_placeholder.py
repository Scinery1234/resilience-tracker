"""Placeholder tests for the Resilience Tracker.

Use this file as a starting point to add unit tests for the
application. Tests should import the Flask app via the
``create_app`` factory and use a temporary database for
isolated execution. Pytest fixtures can help set up the app
and client contexts.
"""
from resilience_tracker.app import create_app


def test_health_endpoint() -> None:
    """Ensure the health check returns the expected response."""
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}