from logging import getLogger

from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import DatabaseError, IntegrityError
from rest_framework import exceptions, status

from .models import EmergencyContact, StudentRecord
from .services import StudentConflict

logger = getLogger(__name__)

STUDENT_NUMBER_CONSTRAINT = "unique_student_number_per_organisation"
PRIMARY_CONTACT_CONSTRAINT = "one_primary_contact_per_student"
CONSTRAINT_ERRORS = {
    STUDENT_NUMBER_CONSTRAINT: {"student_number": "A student with this number already exists in this institution."},
    PRIMARY_CONTACT_CONSTRAINT: {"is_primary": "Only one emergency contact can be primary."},
}
SQLITE_UNIQUE_ERRORS = {
    (
        "UNIQUE constraint failed: students_studentrecord.organisation_id, students_studentrecord.student_number"
    ): STUDENT_NUMBER_CONSTRAINT,
    "UNIQUE constraint failed: students_emergencycontact.student_record_id": PRIMARY_CONTACT_CONSTRAINT,
}


class Conflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"


def _model_error(error):
    errors = getattr(error, "error_dict", {})
    for violation in errors.get(NON_FIELD_ERRORS, ()):
        params = violation.params or {}
        if (
            violation.code == "unique_together"
            and params.get("model_class") is StudentRecord
            and tuple(params.get("unique_check", ())) == ("organisation", "student_number")
        ):
            return CONSTRAINT_ERRORS[STUDENT_NUMBER_CONSTRAINT]
        if any(
            constraint.name == PRIMARY_CONTACT_CONSTRAINT
            and violation.message == constraint.get_violation_error_message()
            for constraint in EmergencyContact._meta.constraints
        ):
            return CONSTRAINT_ERRORS[PRIMARY_CONTACT_CONSTRAINT]

    public_errors = {
        "date_of_birth": "Enter a valid date of birth that is not in the future.",
        "status": "Only active students can be completed or withdrawn.",
    }
    return {field: message for field, message in public_errors.items() if field in errors} or {
        "non_field_errors": "The student or contact data could not be saved. Check the submitted fields."
    }


def _database_constraint(error):
    cause = error.__cause__
    if getattr(cause, "sqlstate", None) == "23505":
        return cause.diag.constraint_name
    if getattr(cause, "sqlite_errorname", None) == "SQLITE_CONSTRAINT_UNIQUE":
        return SQLITE_UNIQUE_ERRORS.get(str(cause))
    return None


def public_student_error(error):
    # The atomic service has already rolled back before the view handles an error.
    if isinstance(error, StudentConflict):
        return Conflict(str(error))
    if isinstance(error, ModelValidationError):
        return exceptions.ValidationError(_model_error(error))
    if isinstance(error, exceptions.ParseError):
        return exceptions.ParseError("Malformed request body.")
    if isinstance(error, IntegrityError):
        constraint = _database_constraint(error)
        if constraint in CONSTRAINT_ERRORS:
            return exceptions.ValidationError(CONSTRAINT_ERRORS[constraint])
    if isinstance(error, DatabaseError):
        logger.error("Student API database request failed (%s).", type(error).__name__)
        return exceptions.APIException("The student request could not be completed.")
    return error
