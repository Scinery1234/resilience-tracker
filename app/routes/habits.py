"""
Routes for managing master habits.

Habits define the high-level behaviours clients can track. Only
counsellors may create, update or delete habits. Listing habits is
available to all authenticated users.
"""

from __future__ import annotations

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt

from .. import db
from ..models import Habit, Role
from ..schemas import HabitSchema


habits_bp = Blueprint("habits", __name__)


def _is_counsellor() -> bool:
    return get_jwt().get("role") == Role.COUNSELLOR.value


@habits_bp.route("/habits", methods=["GET"])
@jwt_required()
def list_habits() -> tuple[list[dict], int]:
    """List all master habits."""
    habits = Habit.query.order_by(Habit.name.asc()).all()
    return HabitSchema(many=True).dump(habits), 200


@habits_bp.route("/habits", methods=["POST"])
@jwt_required()
def create_habit() -> tuple[dict, int]:
    """Create a new master habit.

    Only counsellors may perform this operation. Requires ``name``.
    Optionally accepts ``description``.
    """
    if not _is_counsellor():
        return {"error": "Forbidden"}, 403
    data = request.get_json() or {}
    name = data.get("name")
    if not name:
        return {"error": "name is required."}, 400
    habit = Habit(name=name.strip(), description=data.get("description"))
    db.session.add(habit)
    db.session.commit()
    return HabitSchema().dump(habit), 201


@habits_bp.route("/habits/<int:habit_id>", methods=["PUT"])
@jwt_required()
def update_habit(habit_id: int) -> tuple[dict, int]:
    """Update a master habit.

    Only counsellors may update habits. Accepts ``name`` and/or
    ``description``.
    """
    if not _is_counsellor():
        return {"error": "Forbidden"}, 403
    habit = Habit.query.get_or_404(habit_id)
    data = request.get_json() or {}
    if "name" in data and data["name"]:
        habit.name = data["name"].strip()
    if "description" in data:
        habit.description = data["description"]
    db.session.commit()
    return HabitSchema().dump(habit), 200


@habits_bp.route("/habits/<int:habit_id>", methods=["DELETE"])
@jwt_required()
def delete_habit(habit_id: int) -> tuple[dict, int]:
    """Delete a master habit.

    Only counsellors may delete habits. A habit can only be deleted if
    it is not assigned to any clients. Returns 409 if deletion is not
    permitted.
    """
    if not _is_counsellor():
        return {"error": "Forbidden"}, 403
    habit = Habit.query.get_or_404(habit_id)
    if habit.client_habits:
        return {"error": "Cannot delete habit assigned to clients."}, 409
    db.session.delete(habit)
    db.session.commit()
    return {"message": "Habit deleted."}, 200