"""
Routes for managing weekly assessments and their habit scores.

This blueprint contains endpoints for viewing, updating and deleting
assessments as well as creating, updating and deleting individual habit
score entries associated with an assessment.
"""

from __future__ import annotations

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from .. import db
from ..models import WeeklyAssessment, Role, HabitScore, ClientHabit
from ..schemas import WeeklyAssessmentSchema, HabitScoreSchema


assessments_bp = Blueprint("assessments", __name__)


def _is_counsellor() -> bool:
    return get_jwt().get("role") == Role.COUNSELLOR.value


def _is_self_client(user_id: int) -> bool:
    try:
        return int(get_jwt_identity()) == user_id
    except Exception:
        return False


def _can_access_assessment(assessment: WeeklyAssessment) -> bool:
    """Return True if the current user can access the given assessment."""
    return _is_counsellor() or _is_self_client(assessment.client_id)


@assessments_bp.route("/assessments/<int:assessment_id>", methods=["GET"])
@jwt_required()
def get_assessment(assessment_id: int) -> tuple[dict, int]:
    """Retrieve a specific weekly assessment with its scores."""
    assessment = WeeklyAssessment.query.filter_by(id=assessment_id, deleted_at=None).first()
    if not assessment:
        return {"error": "Assessment not found."}, 404
    if not _can_access_assessment(assessment):
        return {"error": "Forbidden"}, 403
    return WeeklyAssessmentSchema().dump(assessment), 200


@assessments_bp.route("/assessments/<int:assessment_id>", methods=["PUT"])
@jwt_required()
def update_assessment(assessment_id: int) -> tuple[dict, int]:
    """Update an assessment's overall comment.

    Only counsellors or the owner may perform this action. If habit scores
    were modified separately, the wellbeing score will already be
    updated automatically.
    """
    assessment = WeeklyAssessment.query.filter_by(id=assessment_id, deleted_at=None).first()
    if not assessment:
        return {"error": "Assessment not found."}, 404
    if not _can_access_assessment(assessment):
        return {"error": "Forbidden"}, 403
    data = request.get_json() or {}
    from ..util.sanitization import strip_tags
    if "overall_comment" in data:
        raw_comment = data.get("overall_comment")
        assessment.overall_comment = strip_tags(raw_comment) if raw_comment else None
    db.session.commit()
    return WeeklyAssessmentSchema().dump(assessment), 200


@assessments_bp.route("/assessments/<int:assessment_id>", methods=["DELETE"])
@jwt_required()
def delete_assessment(assessment_id: int) -> tuple[dict, int]:
    """Delete a weekly assessment and its scores.

    Only counsellors or the owning client may delete an assessment.
    """
    assessment = WeeklyAssessment.query.filter_by(id=assessment_id, deleted_at=None).first()
    if not assessment:
        return {"error": "Assessment not found."}, 404
    if not _can_access_assessment(assessment):
        return {"error": "Forbidden"}, 403
    # Soft delete the assessment and its scores
    from datetime import datetime
    now = datetime.utcnow()
    assessment.deleted_at = now
    for score in assessment.scores:
        score.deleted_at = now
    db.session.commit()
    return {"message": "Assessment deleted."}, 200


@assessments_bp.route("/assessments/<int:assessment_id>/scores", methods=["GET"])
@jwt_required()
def list_assessment_scores(assessment_id: int) -> tuple[list[dict], int]:
    """List all habit scores for a specific assessment."""
    assessment = WeeklyAssessment.query.filter_by(id=assessment_id, deleted_at=None).first()
    if not assessment:
        return {"error": "Assessment not found."}, 404
    if not _can_access_assessment(assessment):
        return {"error": "Forbidden"}, 403
    # Filter out soft-deleted scores
    active_scores = [s for s in assessment.scores if s.deleted_at is None]
    return HabitScoreSchema(many=True).dump(active_scores), 200


@assessments_bp.route("/assessments/<int:assessment_id>/scores", methods=["POST"])
@jwt_required()
def create_score(assessment_id: int) -> tuple[dict, int]:
    """Add a new habit score to an assessment.

    Accepts ``client_habit_id``, ``score`` (0–10) and optional ``note``.
    Only counsellors or the owning client may add scores. Scores must
    reference a habit assigned to the assessment's client. After
    creation, the wellbeing score is recalculated.
    """
    assessment = WeeklyAssessment.query.get_or_404(assessment_id)
    if not _can_access_assessment(assessment):
        return {"error": "Forbidden"}, 403
    data = request.get_json() or {}
    client_habit_id = data.get("client_habit_id")
    if not client_habit_id:
        return {"error": "client_habit_id is required."}, 400
    client_habit = ClientHabit.query.get(client_habit_id)
    if not client_habit:
        return {"error": "Client habit not found."}, 404
    if client_habit.client_id != assessment.client_id:
        return {"error": "Habit does not belong to the assessment's client."}, 400
    score_val = data.get("score")
    if score_val is None:
        return {"error": "score is required."}, 400
    try:
        score_num = float(score_val)
    except Exception:
        return {"error": "score must be a number."}, 400
    if score_num < 0 or score_num > 10:
        return {"error": "score must be between 0 and 10."}, 400
    from ..util.sanitization import strip_tags
    raw_note = data.get("note")
    # Enforce a limit of 7 scores per habit per week (assessment)
    # Count existing active scores for this assessment and client habit
    from sqlalchemy import and_
    existing_count = HabitScore.query.filter(
        HabitScore.assessment_id == assessment_id,
        HabitScore.client_habit_id == client_habit_id,
        HabitScore.deleted_at.is_(None),
    ).count()
    if existing_count >= 7:
        return {"error": "Cannot submit more than 7 scores for this habit in a single week."}, 400

    habit_score = HabitScore(
        assessment_id=assessment_id,
        client_habit_id=client_habit_id,
        score=score_num,
        note=strip_tags(raw_note) if raw_note else None,
    )
    db.session.add(habit_score)
    db.session.commit()
    # Recompute wellbeing score using service or model method
    assessment.compute_wellbeing_score()
    db.session.commit()
    return HabitScoreSchema().dump(habit_score), 201


@assessments_bp.route("/scores/<int:score_id>", methods=["PUT"])
@jwt_required()
def update_score(score_id: int) -> tuple[dict, int]:
    """Update an individual habit score.

    Accepts ``score`` (0–10) and/or ``note``. Only counsellors or the
    owning client may modify the score. After updating, the associated
    assessment's wellbeing score is recalculated.
    """
    score = HabitScore.query.get_or_404(score_id)
    assessment = score.assessment
    if not _can_access_assessment(assessment):
        return {"error": "Forbidden"}, 403
    data = request.get_json() or {}
    if "score" in data:
        try:
            new_score = float(data.get("score"))
        except Exception:
            return {"error": "score must be a number."}, 400
        if new_score < 0 or new_score > 10:
            return {"error": "score must be between 0 and 10."}, 400
        score.score = new_score
    if "note" in data:
        from ..util.sanitization import strip_tags
        raw_note = data.get("note")
        score.note = strip_tags(raw_note) if raw_note else None
    db.session.commit()
    assessment.compute_wellbeing_score()
    db.session.commit()
    return HabitScoreSchema().dump(score), 200


@assessments_bp.route("/scores/<int:score_id>", methods=["DELETE"])
@jwt_required()
def delete_score(score_id: int) -> tuple[dict, int]:
    """Delete a habit score.

    Only counsellors or the owning client may delete a score. After
    deletion, the assessment's wellbeing score is recalculated.
    """
    score = HabitScore.query.get_or_404(score_id)
    assessment = score.assessment
    if not _can_access_assessment(assessment):
        return {"error": "Forbidden"}, 403
    # Soft delete the score
    from datetime import datetime
    now = datetime.utcnow()
    score.deleted_at = now
    db.session.commit()
    # Recompute wellbeing score excluding deleted scores
    assessment.compute_wellbeing_score()
    db.session.commit()
    return {"message": "Score deleted."}, 200