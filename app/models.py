"""
Database models for the Foundations of Resilience Tracker.

This module defines the core database schema using SQLAlchemy models.
The schema is based on the provided entity-relationship diagram and
expanded slightly to support authentication via user accounts with roles
(``client`` or ``counsellor``). Each client may have multiple habits
assigned through the ``ClientHabit`` table and submits weekly
assessments that include scored entries for each habit. An average
``wellbeing_score`` is automatically computed when scores are added or
modified.
"""

from __future__ import annotations

import enum
from datetime import datetime, date
from typing import Optional, List

from werkzeug.security import generate_password_hash, check_password_hash

from . import db


class Role(enum.Enum):
    """Enumeration of user roles."""
    CLIENT = "client"
    COUNSELLOR = "counsellor"


class User(db.Model):
    __allow_unmapped__ = True  # allow unmapped type annotations for SQLAlchemy 2.0
    """A user of the system.

    Users are either clients or counsellors. Counsellors manage clients and
    habits, while clients submit weekly assessments. Passwords are stored
    as salted hashes.
    """
    __tablename__ = "users"

    id: int = db.Column(db.Integer, primary_key=True)
    first_name: str = db.Column(db.String(50), nullable=False)
    last_name: str = db.Column(db.String(50), nullable=False)
    email: str = db.Column(db.String(120), unique=True, nullable=False)
    password_hash: str = db.Column(db.String(128), nullable=False)
    role: Role = db.Column(db.Enum(Role), default=Role.CLIENT, nullable=False)

    # Soft delete timestamp; when set, this record is considered deleted
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    habits: List[ClientHabit] = db.relationship("ClientHabit", back_populates="client", cascade="all, delete-orphan")
    assessments: List[WeeklyAssessment] = db.relationship(
        "WeeklyAssessment", back_populates="client", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"


class Habit(db.Model):
    __allow_unmapped__ = True
    """A master habit definition that can be assigned to clients."""
    __tablename__ = "habits"

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(100), unique=True, nullable=False)
    description: Optional[str] = db.Column(db.String(255))

    # Soft delete timestamp
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relationship to client habits
    client_habits: List[ClientHabit] = db.relationship(
        "ClientHabit", back_populates="habit", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Habit {self.name}>"


class ClientHabit(db.Model):
    __allow_unmapped__ = True
    """Association between a user and a habit.

    Each entry optionally stores a custom label and a display order. A
    client may not have duplicate habits assigned.
    """
    __tablename__ = "client_habits"

    id: int = db.Column(db.Integer, primary_key=True)
    client_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    habit_id: int = db.Column(db.Integer, db.ForeignKey("habits.id"), nullable=False)
    custom_label: Optional[str] = db.Column(db.String(100))
    order: Optional[int] = db.Column(db.Integer)

    # Soft delete timestamp
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    client: User = db.relationship("User", back_populates="habits")
    habit: Habit = db.relationship("Habit", back_populates="client_habits")
    scores: List[HabitScore] = db.relationship(
        "HabitScore", back_populates="client_habit", cascade="all, delete-orphan"
    )

    # Unique constraints: a client cannot have the same habit assigned twice,
    # and display order must be unique per client
    __table_args__ = (
        db.UniqueConstraint("client_id", "habit_id", name="uix_client_habit"),
        db.UniqueConstraint("client_id", "order", name="uix_client_order"),
    )

    def __repr__(self) -> str:
        return f"<ClientHabit client={self.client_id} habit={self.habit_id}>"


class WeeklyAssessment(db.Model):
    __allow_unmapped__ = True
    """Weekly wellbeing assessment submitted by a client."""
    __tablename__ = "weekly_assessments"

    id: int = db.Column(db.Integer, primary_key=True)
    client_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    week_start_date: date = db.Column(db.Date, nullable=False)
    # Average wellbeing score rounded to one decimal (0.0–10.0). Stored for performance.
    wellbeing_score = db.Column(db.Numeric(4, 1), nullable=False, default=0.0)
    overall_comment: Optional[str] = db.Column(db.String(255))
    submitted_at: datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Soft delete timestamp
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    client: User = db.relationship("User", back_populates="assessments")
    scores: List[HabitScore] = db.relationship(
        "HabitScore", back_populates="assessment", cascade="all, delete-orphan"
    )

    # Ensure one assessment per client per week
    __table_args__ = (
        db.UniqueConstraint("client_id", "week_start_date", name="uix_client_week"),
    )

    def compute_wellbeing_score(self) -> None:
        """Recalculate and update the wellbeing_score based on active habit scores.

        This method sums the ``score`` values of all associated ``HabitScore``
        objects that have not been soft-deleted (i.e. their ``deleted_at``
        attribute is ``None``). The arithmetic mean is then rounded to
        one decimal place and assigned to ``wellbeing_score``. If there
        are no active scores, the wellbeing score is set to ``0.0``.
        """
        # Filter out soft-deleted scores
        active_scores = [s for s in self.scores if getattr(s, "deleted_at", None) is None]
        if not active_scores:
            self.wellbeing_score = 0.0
            return
        total = sum(score.score for score in active_scores)
        count = len(active_scores)
        # round to 1 decimal place as per requirements
        self.wellbeing_score = round(float(total) / count, 1)

    def __repr__(self) -> str:
        return f"<WeeklyAssessment {self.client_id} {self.week_start_date}>"


class HabitScore(db.Model):
    __allow_unmapped__ = True
    """Score for a particular habit within a weekly assessment."""
    __tablename__ = "habit_scores"

    id: int = db.Column(db.Integer, primary_key=True)
    assessment_id: int = db.Column(db.Integer, db.ForeignKey("weekly_assessments.id"), nullable=False)
    client_habit_id: int = db.Column(db.Integer, db.ForeignKey("client_habits.id"), nullable=False)
    # Allow scores with one decimal place (0.0–10.0). Use Numeric for precision.
    score = db.Column(db.Numeric(3, 1), nullable=False)
    note: Optional[str] = db.Column(db.String(255))

    # Soft delete timestamp
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    assessment: WeeklyAssessment = db.relationship("WeeklyAssessment", back_populates="scores")
    client_habit: ClientHabit = db.relationship("ClientHabit", back_populates="scores")

    def __repr__(self) -> str:
        return (
            f"<HabitScore assessment={self.assessment_id} client_habit={self.client_habit_id} "
            f"score={self.score}>"
        )