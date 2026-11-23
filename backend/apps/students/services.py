from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.identity.models import Person

from .models import AuditEvent, EmergencyContact, StudentRecord


class StudentConflict(Exception):
    pass


def _audit(actor, student, event_type, changed_fields):
    AuditEvent.objects.create(
        actor=actor,
        organisation=student.organisation,
        student_record=student,
        event_type=event_type,
        changed_fields=sorted(changed_fields),
    )


@transaction.atomic
def create_student(actor, organisation, validated_data, contacts):
    student = StudentRecord(
        person=Person.objects.create(),
        organisation=organisation,
        created_by=actor,
        updated_by=actor,
        **validated_data,
    )
    student.save()
    for contact_data in contacts:
        EmergencyContact.objects.create(student_record=student, **contact_data)
    _audit(actor, student, "student.created", validated_data.keys())
    return student


@transaction.atomic
def update_student(actor, student_id, expected_version, validated_data):
    student = StudentRecord.objects.select_for_update().get(id=student_id)
    if student.archived_at:
        raise StudentConflict("Archived student records are read-only.")
    if student.version != expected_version:
        raise StudentConflict("The student record was changed by another user.")

    new_status = validated_data.get("status", student.status)
    if new_status != student.status and student.status != StudentRecord.Status.ACTIVE:
        raise ValidationError({"status": "Only active students can be completed or withdrawn."})

    changed_fields = []
    for field, value in validated_data.items():
        if getattr(student, field) != value:
            setattr(student, field, value)
            changed_fields.append(field)
    student.updated_by = actor
    student.version += 1
    student.save()
    _audit(actor, student, "student.updated", changed_fields)
    return student


@transaction.atomic
def archive_student(actor, student_id, expected_version):
    student = StudentRecord.objects.select_for_update().get(id=student_id)
    if student.archived_at:
        raise StudentConflict("Student record is already archived.")
    if student.version != expected_version:
        raise StudentConflict("The student record was changed by another user.")
    student.archived_at = timezone.now()
    student.archived_by = actor
    student.updated_by = actor
    student.version += 1
    student.save()
    _audit(actor, student, "student.archived", ["archived_at"])
    return student


@transaction.atomic
def create_contact(actor, student, validated_data):
    if student.archived_at:
        raise StudentConflict("Archived student records are read-only.")
    contact = EmergencyContact.objects.create(student_record=student, **validated_data)
    _audit(actor, student, "contact.created", validated_data.keys())
    return contact


@transaction.atomic
def update_contact(actor, student, contact, validated_data):
    if student.archived_at:
        raise StudentConflict("Archived student records are read-only.")
    changed_fields = []
    for field, value in validated_data.items():
        if getattr(contact, field) != value:
            setattr(contact, field, value)
            changed_fields.append(field)
    contact.save()
    _audit(actor, student, "contact.updated", changed_fields)
    return contact
