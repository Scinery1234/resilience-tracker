"""Database setup utilities.

This module centralises the configuration of the SQLAlchemy
engine and session. It exposes the ``db`` object used by
models throughout the application. Keeping database setup in
a single place makes it easier to test and to switch
configurations if needed.

Import ``db`` from ``app``
rather than from this module directly. The application factory
initialises ``db`` with the Flask app.
"""
from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()