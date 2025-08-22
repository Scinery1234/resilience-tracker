"""Routes for derived insights.

This blueprint exposes endpoints that compute derived statistics,
such as a client's wellbeing trend over recent weeks. The heavy
lifting is delegated to service functions in
``resilience_tracker.app.services``.
"""
from __future__ import annotations

from flask import Blueprint
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from ..models import WeeklyAssessment, Role
from ..services import compute_trend

insights_bp = Blueprint("insights", __name__)


def _is_counsellor() -> bool:
    return get_jwt().get("role") == Role.COUNSELLOR.value


def _is_self_client(user_id: int) -> bool:
    try:
        return int(get_jwt_identity()) == user_id
    except Exception:
        return False


@insights_bp.route("/clients/<int:client_id>/insights/latest", methods=["GET"])
@jwt_required()
def latest_insights(client_id: int) -> tuple[dict, int]:
    """Return the latest wellbeing score and a simple trend for a client.

    Retrieves the last four weekly assessments (non-deleted) for the
    specified client, computes the most recent wellbeing score, and
    the delta compared to the prior week. Counsellors can access
    any client; clients can only access their own insights.
    """
    if not (_is_counsellor() or _is_self_client(client_id)):
        return {"error": "Forbidden"}, 403
    # Fetch assessments ordered from oldest to newest
    assessments = (
        WeeklyAssessment.query
        .filter_by(client_id=client_id, deleted_at=None)
        .order_by(WeeklyAssessment.week_start_date.asc())
        .all()
    )
    # Only take the last 4 assessments for trend computation
    if len(assessments) > 4:
        assessments = assessments[-4:]
    trend = compute_trend(assessments)
    if not trend:
        return {"message": "No assessments yet."}, 200
    return trend, 200