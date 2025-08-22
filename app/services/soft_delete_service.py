"""Soft delete utilities.

To preserve historical data without permanently removing records,
the application uses *soft deletion*. Instead of deleting rows
from the database, a ``deleted_at`` timestamp column is set.
Queries that should only return active records must filter
``deleted_at IS NULL``.

This module defines helper functions to perform cascading
soft deletes across related entities. For example, deleting a
client should mark all associated client habits, assessments,
and habit scores as deleted.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from resilience_tracker.app.models import User, ClientHabit, WeeklyAssessment, HabitScore
from resilience_tracker.app import db

def soft_delete_client(client: User) -> None:
    """Soft delete a client and all related data.

    This function sets the ``deleted_at`` timestamp on the client
    record and iterates through the client's habits, assessments,
    and scores to mark them as deleted. Changes are flushed to
    the database session but not committed, allowing the caller
    to decide when to commit.

    Parameters
    ----------
    client: User
        The client to be soft deleted.
    """
    now = datetime.utcnow()
    # Assume the User model has a deleted_at column; if not,
    # this will simply set an attribute on the instance.
    setattr(client, "deleted_at", now)
    # Soft delete client habits
    for ch in client.habits:
        setattr(ch, "deleted_at", now)
        # Soft delete associated scores
        for score in ch.scores:
            setattr(score, "deleted_at", now)
    # Soft delete assessments and their scores
    for assessment in client.assessments:
        setattr(assessment, "deleted_at", now)
        for score in assessment.scores:
            setattr(score, "deleted_at", now)
    db.session.flush()