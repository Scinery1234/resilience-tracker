"""
Serialization schemas using Marshmallow for the Resilience Tracker.

These schemas convert SQLAlchemy models to and from JSON-friendly
representations. Sensitive fields, such as password hashes, are
excluded. Nested relationships are included where useful, but kept
minimal to avoid deep recursion in responses.
"""

from __future__ import annotations

from marshmallow import Schema, fields, validate, post_load
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field

from .models import User, Habit, ClientHabit, WeeklyAssessment, HabitScore


class UserSchema(SQLAlchemyAutoSchema):
    """Schema for serialising ``User`` objects."""

    class Meta:
        model = User
        load_instance = True
        include_fk = True
        # Exclude password_hash from the serialised output
        exclude = ("password_hash",)


class HabitSchema(SQLAlchemyAutoSchema):
    """Schema for serialising ``Habit`` objects."""

    name = auto_field(validate=validate.Length(max=100))
    description = auto_field(validate=validate.Length(max=255), allow_none=True)

    class Meta:
        model = Habit
        load_instance = True
        include_fk = True


class ClientHabitSchema(SQLAlchemyAutoSchema):
    """Schema for serialising ``ClientHabit`` objects."""

    habit = fields.Nested(HabitSchema, only=("id", "name", "description"))

    custom_label = auto_field(validate=validate.Length(max=100), allow_none=True)
    order = auto_field(validate=validate.Range(min=0), allow_none=True)

    class Meta:
        model = ClientHabit
        load_instance = True
        include_fk = True


class HabitScoreSchema(SQLAlchemyAutoSchema):
    """Schema for serialising ``HabitScore`` objects."""

    client_habit = fields.Nested(ClientHabitSchema, only=("id", "habit", "custom_label"))

    score = auto_field(validate=validate.Range(min=0, max=10))
    note = auto_field(validate=validate.Length(max=500), allow_none=True)

    class Meta:
        model = HabitScore
        load_instance = True
        include_fk = True


class WeeklyAssessmentSchema(SQLAlchemyAutoSchema):
    """Schema for serialising ``WeeklyAssessment`` objects."""

    scores = fields.Nested(HabitScoreSchema, many=True)

    week_start_date = auto_field()  # Marshmallow will treat as ISO8601 date
    overall_comment = auto_field(validate=validate.Length(max=500), allow_none=True)

    class Meta:
        model = WeeklyAssessment
        load_instance = True
        include_fk = True
