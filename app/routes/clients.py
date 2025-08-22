"""
Routes for managing clients and their associated data.

Clients are represented by the ``User`` model with a role of
``client``. Counsellors can create, update and delete clients, while
clients themselves can view and edit their own profiles. This module
also exposes endpoints for assigning habits and managing weekly
assessments, though the detailed score operations live in other
blueprints.
"""

from __future__ import annotations

from datetime import date, datetime
from dateutil.parser import parse as parse_date  # type: ignore

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from .. import db
from ..models import User, Role, Habit, ClientHabit, WeeklyAssessment
from ..schemas import UserSchema, ClientHabitSchema, WeeklyAssessmentSchema


clients_bp = Blueprint("clients", __name__)


def _is_counsellor() -> bool:
    """Helper to determine if the current user is a counsellor."""
    return get_jwt().get("role") == Role.COUNSELLOR.value


def _is_self(user_id: int) -> bool:
    """Return True if the current user matches the given ``user_id``."""
    try:
        return int(get_jwt_identity()) == user_id
    except Exception:
        return False


@clients_bp.route("/clients", methods=["GET"])
@jwt_required()
def list_clients() -> tuple[list[dict], int]:
    """Return a list of all clients.

    Only counsellors may list all clients. Returns 403 for other roles.
    """
    if not _is_counsellor():
        return {"error": "Forbidden"}, 403
    # Exclude soft-deleted clients
    query = User.query.filter_by(role=Role.CLIENT, deleted_at=None)
    # Handle pagination parameters
    try:
        limit = int(request.args.get("limit", 25))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return {"error": "Invalid pagination parameters."}, 400
    clients_page = query.order_by(User.id.asc()).limit(limit).offset(offset).all()
    return UserSchema(many=True).dump(clients_page), 200


@clients_bp.route("/clients/<int:client_id>", methods=["GET"])
@jwt_required()
def get_client(client_id: int) -> tuple[dict, int]:
    """Retrieve an individual client's profile.

    Counsellors can view any client; clients can only view their own
    record.
    """
    user = User.query.filter_by(id=client_id, deleted_at=None).first()
    if not user:
        return {"error": "Client not found."}, 404
    if user.role != Role.CLIENT:
        return {"error": "User is not a client."}, 400
    if not (_is_counsellor() or _is_self(client_id)):
        return {"error": "Forbidden"}, 403
    return UserSchema().dump(user), 200


@clients_bp.route("/clients", methods=["POST"])
@jwt_required()
def create_client() -> tuple[dict, int]:
    """Create a new client.

    Only counsellors may create clients. Accepts ``first_name``,
    ``last_name``, ``email`` and optional ``password`` (generated if
    omitted). Returns the created client record. A password is required
    for a client to log in; if omitted, a random strong password will be
    generated and must be communicated by the counsellor.
    """
    if not _is_counsellor():
        return {"error": "Forbidden"}, 403
    data = request.get_json() or {}
    required = {"first_name", "last_name", "email"}
    missing = required - data.keys()
    if missing:
        return {"error": f"Missing fields: {', '.join(missing)}"}, 400
    email = data.get("email").strip().lower()
    if User.query.filter_by(email=email).first():
        return {"error": "A user with that email already exists."}, 409
    password = data.get("password")
    if not password:
        # simple random password generation; in a real system you would
        # generate a strong password and communicate it securely
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        password = "".join(secrets.choice(alphabet) for _ in range(12))
    user = User(
        first_name=data.get("first_name").strip(),
        last_name=data.get("last_name").strip(),
        email=email,
        role=Role.CLIENT,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return UserSchema().dump(user), 201


@clients_bp.route("/clients/<int:client_id>", methods=["PUT"])
@jwt_required()
def update_client(client_id: int) -> tuple[dict, int]:
    """Update a client's details.

    Clients may update their own information; counsellors may update any
    client. Accepts ``first_name``, ``last_name`` and ``email``.
    """
    user = User.query.get_or_404(client_id)
    if user.role != Role.CLIENT:
        return {"error": "User is not a client."}, 400
    if not (_is_counsellor() or _is_self(client_id)):
        return {"error": "Forbidden"}, 403
    data = request.get_json() or {}
    for field in ("first_name", "last_name", "email"):
        if field in data and data[field]:
            setattr(user, field, data[field].strip())
    if "email" in data and data["email"]:
        # ensure new email is not taken by someone else
        new_email = data["email"].strip().lower()
        existing = User.query.filter(User.email == new_email, User.id != user.id).first()
        if existing:
            return {"error": "Email is already taken."}, 409
        user.email = new_email
    db.session.commit()
    return UserSchema().dump(user), 200


@clients_bp.route("/clients/<int:client_id>", methods=["DELETE"])
@jwt_required()
def delete_client(client_id: int) -> tuple[dict, int]:
    """Delete a client and all of their related data.

    Only counsellors may perform this operation. This will cascade
    delete associated client habits, assessments and scores because of
    cascade rules defined in the models.
    """
    if not _is_counsellor():
        return {"error": "Forbidden"}, 403
    user = User.query.get_or_404(client_id)
    if user.role != Role.CLIENT:
        return {"error": "User is not a client."}, 400
    # Perform a soft delete rather than removing the row entirely
    from ..services import soft_delete_client
    soft_delete_client(user)
    db.session.commit()
    return {"message": "Client deleted."}, 200


@clients_bp.route("/clients/<int:client_id>/habits", methods=["GET"])
@jwt_required()
def list_client_habits(client_id: int) -> tuple[list[dict], int]:
    """List the habits assigned to a specific client.

    Counsellors can view any client's habits; clients can view their own.
    """
    user = User.query.get_or_404(client_id)
    if user.role != Role.CLIENT:
        return {"error": "User is not a client."}, 400
    if not (_is_counsellor() or _is_self(client_id)):
        return {"error": "Forbidden"}, 403
    # Filter out soft-deleted habits
    active_habits = [ch for ch in user.habits if ch.deleted_at is None]
    return ClientHabitSchema(many=True).dump(active_habits), 200


@clients_bp.route("/clients/<int:client_id>/habits", methods=["POST"])
@jwt_required()
def assign_habit_to_client(client_id: int) -> tuple[dict, int]:
    """Assign an existing habit to a client.

    Accepts ``habit_id`` and optional ``custom_label`` and ``order``.
    Only counsellors may assign habits. Returns 404 if habit or client
    does not exist. Returns 409 if the habit is already assigned to the
    client.
    """
    if not _is_counsellor():
        return {"error": "Forbidden"}, 403
    user = User.query.get_or_404(client_id)
    if user.role != Role.CLIENT:
        return {"error": "User is not a client."}, 400
    data = request.get_json() or {}
    habit_id = data.get("habit_id")
    if not habit_id:
        return {"error": "habit_id is required."}, 400
    habit = Habit.query.get(habit_id)
    if not habit:
        return {"error": "Habit not found."}, 404
    # check duplication
    existing = ClientHabit.query.filter_by(client_id=client_id, habit_id=habit_id).first()
    if existing:
        return {"error": "Habit already assigned to client."}, 409
    client_habit = ClientHabit(
        client_id=client_id,
        habit_id=habit_id,
        custom_label=data.get("custom_label"),
        order=data.get("order"),
    )
    db.session.add(client_habit)
    db.session.commit()
    return ClientHabitSchema().dump(client_habit), 201


@clients_bp.route("/clients/<int:client_id>/assessments", methods=["GET"])
@jwt_required()
def list_client_assessments(client_id: int) -> tuple[list[dict], int]:
    """List all weekly assessments for a client.

    Counsellors can view any client's assessments; clients can view
    their own. Assessments are ordered by week_start_date descending.
    """
    user = User.query.get_or_404(client_id)
    if user.role != Role.CLIENT:
        return {"error": "User is not a client."}, 400
    if not (_is_counsellor() or _is_self(client_id)):
        return {"error": "Forbidden"}, 403
    # Build base query excluding soft-deleted assessments
    query = WeeklyAssessment.query.filter_by(client_id=client_id, deleted_at=None)
    # Optional date range filtering (from=YYYY-MM-DD, to=YYYY-MM-DD)
    from_date = request.args.get("from")
    to_date = request.args.get("to")
    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date).date()
            query = query.filter(WeeklyAssessment.week_start_date >= from_dt)
        except Exception:
            return {"error": "Invalid 'from' date. Use ISO format YYYY-MM-DD."}, 400
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date).date()
            query = query.filter(WeeklyAssessment.week_start_date <= to_dt)
        except Exception:
            return {"error": "Invalid 'to' date. Use ISO format YYYY-MM-DD."}, 400
    # Pagination
    try:
        limit = int(request.args.get("limit", 25))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return {"error": "Invalid pagination parameters."}, 400
    assessments_page = (
        query.order_by(WeeklyAssessment.week_start_date.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return WeeklyAssessmentSchema(many=True).dump(assessments_page), 200


@clients_bp.route("/clients/<int:client_id>/assessments", methods=["POST"])
@jwt_required()
def create_client_assessment(client_id: int) -> tuple[dict, int]:
    """Create a new weekly assessment for a client.

    Accepts ``week_start_date`` (YYYY-MM-DD) and optional ``overall_comment``.
    Returns the created assessment. Only counsellors or the client
    themselves may create an assessment.
    """
    user = User.query.get_or_404(client_id)
    if user.role != Role.CLIENT:
        return {"error": "User is not a client."}, 400
    if not (_is_counsellor() or _is_self(client_id)):
        return {"error": "Forbidden"}, 403
    data = request.get_json() or {}
    date_str = data.get("week_start_date")
    if not date_str:
        return {"error": "week_start_date is required."}, 400
    try:
        week_date = parse_date(date_str).date()
    except Exception:
        return {"error": "Invalid date format. Use ISO 8601 (YYYY-MM-DD)."}, 400
    comment = data.get("overall_comment")
    assessment = WeeklyAssessment(client_id=client_id, week_start_date=week_date, overall_comment=comment)
    db.session.add(assessment)
    db.session.commit()
    return WeeklyAssessmentSchema().dump(assessment), 201