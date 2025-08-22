"""
Authentication routes for the Resilience Tracker.

Provides endpoints for registering new users and logging in to obtain
JSON Web Tokens (JWTs). These tokens are required for accessing
protected resources throughout the API.
"""

from __future__ import annotations

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token

from .. import db
from ..models import User, Role
from ..schemas import UserSchema


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register() -> tuple[dict, int]:
    """Register a new user.

    Expects JSON with ``first_name``, ``last_name``, ``email``,
    ``password`` and optional ``role`` (``client`` or ``counsellor``). If no
    role is provided, ``client`` is used. Emails must be unique.
    """
    data = request.get_json() or {}
    required_fields = {"first_name", "last_name", "email", "password"}
    missing = required_fields - data.keys()
    if missing:
        return {"error": f"Missing fields: {', '.join(missing)}"}, 400

    email = data.get("email").strip().lower()
    if User.query.filter_by(email=email).first():
        return {"error": "A user with that email already exists."}, 409

    role_str = data.get("role", "client").lower()
    try:
        role = Role(role_str)
    except ValueError:
        return {"error": "Invalid role. Choose 'client' or 'counsellor'."}, 400

    user = User(
        first_name=data.get("first_name").strip(),
        last_name=data.get("last_name").strip(),
        email=email,
        role=role,
    )
    user.set_password(data.get("password"))
    db.session.add(user)
    db.session.commit()
    schema = UserSchema()
    return schema.dump(user), 201


@auth_bp.route("/login", methods=["POST"])
def login() -> tuple[dict, int]:
    """Authenticate a user and return a JWT.

    Expects JSON with ``email`` and ``password``. Returns a JWT
    containing the user's ID and role. Invalid credentials return 401.
    """
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return {"error": "Invalid email or password."}, 401

    additional_claims = {"role": user.role.value}
    access_token = create_access_token(identity=user.id, additional_claims=additional_claims)
    return {"access_token": access_token, "user": UserSchema().dump(user)}, 200