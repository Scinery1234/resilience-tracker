"""Service layer for the Foundations of Resilience Tracker.

This package contains business logic that sits between the
Flask route handlers and the database models. Separating
services into their own modules helps keep the routes thin
and reusable, and makes the core calculations (like wellbeing
scores and trend analysis) easy to unit test.

Nothing in this package should perform any HTTP handling.
Instead, services return simple Python data structures or
database objects, and raise exceptions defined in
``app.errors`` when something goes wrong.

The initial version of the application keeps most logic in
the route handlers themselves. This module provides stub
imports so that services can be added incrementally in later
phases without breaking the import paths.
"""

from .wellbeing_service import compute_wellbeing, compute_trend
from .soft_delete_service import soft_delete_client

__all__ = [
    "compute_wellbeing",
    "compute_trend",
    "soft_delete_client",
]