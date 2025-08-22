"""
Routes for operations on the ClientHabit association.

This module covers updating or removing a habit assignment from a client,
as well as retrieving a history of scores for a particular habit across
multiple weekly assessments.
"""

from __future__ import annotations

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from .. import db
from ..models import ClientHabit, Role, HabitScore, WeeklyAssessment
from ..schemas import ClientHabitSchema, HabitScoreSchema


client_habits_bp = Blueprint("client_habits", __name__)


def _is_counsellor() -> bool:
    return get_jwt().get("role") == Role.COUNSELLOR.value


def _is_self_client(user_id: int) -> bool:
    try:
        return int(get_jwt_identity()) == user_id
    except Exception:
        return False


@client_habits_bp.route("/client-habits/<int:client_habit_id>", methods=["PUT"])
@jwt_required()
def update_client_habit(client_habit_id: int) -> tuple[dict, int]:
    """Update a client's habit assignment.

    Accepts ``custom_label`` and/or ``order``. Counsellors can modify
    any client habit; clients may modify their own habits.
    """
    client_habit = ClientHabit.query.get_or_404(client_habit_id)
    # only counsellor or the client themselves may update
    if not (_is_counsellor() or _is_self_client(client_habit.client_id)):
        return {"error": "Forbidden"}, 403
    data = request.get_json() or {}
    if "custom_label" in data:
        client_habit.custom_label = data.get("custom_label")
    if "order" in data:
        client_habit.order = data.get("order")
    db.session.commit()
    return ClientHabitSchema().dump(client_habit), 200


@client_habits_bp.route("/client-habits/<int:client_habit_id>", methods=["DELETE"])
@jwt_required()
def delete_client_habit(client_habit_id: int) -> tuple[dict, int]:
    """Unassign a habit from a client.

    Only counsellors or the client themselves may delete the assignment. This
    will cascade delete associated habit scores via the configured
    cascade behaviour on the ``scores`` relationship.
    """
    client_habit = ClientHabit.query.get_or_404(client_habit_id)
    if not (_is_counsellor() or _is_self_client(client_habit.client_id)):
        return {"error": "Forbidden"}, 403
    db.session.delete(client_habit)
    db.session.commit()
    return {"message": "Client habit unassigned."}, 200


@client_habits_bp.route("/client-habits/<int:client_habit_id>/scores", methods=["GET"])
@jwt_required()
def list_client_habit_scores(client_habit_id: int) -> tuple[list[dict], int]:
    """List all scores for a specific client habit across assessments.

    Only the counsellor or the owning client may view this history.
    Scores are ordered by assessment week start date ascending.
    """
    client_habit = ClientHabit.query.get_or_404(client_habit_id)
    if not (_is_counsellor() or _is_self_client(client_habit.client_id)):
        return {"error": "Forbidden"}, 403
    # join to get scores along with assessment info; ordered by week
    scores = (
        HabitScore.query.join(WeeklyAssessment)
        .filter(HabitScore.client_habit_id == client_habit_id)
        .order_by(WeeklyAssessment.week_start_date.asc())
        .all()
    )
    return HabitScoreSchema(many=True).dump(scores), 200