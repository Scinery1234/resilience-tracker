"""Centralised error handling and custom exceptions.

This module defines custom exception classes and provides
Flask error handlers that serialise them into JSON responses.
By using custom exceptions, the service layer can signal
specific error conditions without coupling itself to HTTP
response codes. The Flask app will register these handlers
during application factory initialisation.
"""
from __future__ import annotations

from flask import jsonify

class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str, fields: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.fields = fields or {}

    def to_response(self, status_code: int = 400):
        response = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": self.message,
                "fields": self.fields,
            }
        }
        return jsonify(response), status_code


class NotFoundError(Exception):
    """Raised when a requested resource cannot be found."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def to_response(self, status_code: int = 404):
        response = {
            "error": {
                "code": "NOT_FOUND",
                "message": self.message,
            }
        }
        return jsonify(response), status_code


class ConflictError(Exception):
    """Raised when a uniqueness or resource conflict occurs."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def to_response(self, status_code: int = 409):
        response = {
            "error": {
                "code": "CONFLICT",
                "message": self.message,
            }
        }
        return jsonify(response), status_code


def register_error_handlers(app) -> None:
    """Register custom error handlers on the given Flask app."""
    @app.errorhandler(ValidationError)
    def handle_validation_error(err: ValidationError):
        return err.to_response(400)

    @app.errorhandler(NotFoundError)
    def handle_not_found_error(err: NotFoundError):
        return err.to_response(404)

    @app.errorhandler(ConflictError)
    def handle_conflict_error(err: ConflictError):
        return err.to_response(409)