"""Seed script for initial data.

Running this script will populate the database with a set of
predefined habits and an example client for demonstration
purposes. It can be executed with ``flask run`` or via an
invocation of ``python -m resilience_tracker.seed.seed`` once
the application context is available.
"""
from __future__ import annotations

from app import create_app, db
from app.models import Habit, User, Role

def run_seeds() -> None:
    """Insert initial habits and a demo client into the database."""
    app = create_app()
    with app.app_context():
        # Define master habits
        habits = [
            Habit(name="Drink Water", description="Stay hydrated by drinking enough water each day"),
            Habit(name="Get Enough Sleep", description="Aim for 7-9 hours of quality sleep per night"),
            Habit(name="Exercise", description="Engage in physical activity to move your body"),
            Habit(name="Eat Healthily", description="Choose nutritious foods and maintain balanced meals"),
            Habit(name="Connect with Nature", description="Spend time outdoors or in green spaces"),
            Habit(name="Connect with Others", description="Maintain healthy relationships and social connections"),
            Habit(name="Practice Spirituality", description="Engage in activities that nourish your spirit"),
            Habit(name="Express Creativity", description="Do something creative like painting, writing, or music"),
        ]
        db.session.bulk_save_objects(habits)
        # Add a demo counsellor and client
        counsellor = User(
            first_name="Admin",
            last_name="Counsellor",
            email="counsellor@example.com",
            role=Role.COUNSELLOR,
        )
        counsellor.set_password("password")
        client = User(
            first_name="Demo",
            last_name="Client",
            email="client@example.com",
            role=Role.CLIENT,
        )
        client.set_password("password")
        db.session.add_all([counsellor, client])
        db.session.commit()
        print("Seed data inserted successfully.")


if __name__ == "__main__":
    run_seeds()