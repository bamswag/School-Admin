from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.identity.models import Person

from .models import AuditEvent, EmergencyContact, StudentRecord


class StudentConflict(Exception):
    pass


STALE_VERSION = "The student record was changed by another user. Refresh the record and try again."


def _lock_student(student):
    return get_object_or_404(
        StudentRecord.objects.select_for_update(), pk=student.pk, organisation_id=student.organisation_id
    )


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
def update_student(actor, student, expected_version, validated_data):
    student = _lock_student(student)
    if student.archived_at:
        raise StudentConflict("Archived student records are read-only.")
    if student.version != expected_version:
        raise StudentConflict(STALE_VERSION)

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
def archive_student(actor, student, expected_version):
    student = _lock_student(student)
    if student.archived_at:
        raise StudentConflict("Student record is already archived.")
    if student.version != expected_version:
        raise StudentConflict(STALE_VERSION)
    student.archived_at = timezone.now()
    student.archived_by = actor
    student.updated_by = actor
    student.version += 1
    student.save()
    _audit(actor, student, "student.archived", ["archived_at"])
    return student


@transaction.atomic
def create_contact(actor, student, validated_data):
    student = _lock_student(student)
    if student.archived_at:
        raise StudentConflict("Archived student records are read-only.")
    contact = EmergencyContact.objects.create(student_record=student, **validated_data)
    _audit(actor, student, "contact.created", validated_data.keys())
    return contact


@transaction.atomic
def update_contact(actor, student, contact, validated_data):
    student = _lock_student(student)
    if student.archived_at:
        raise StudentConflict("Archived student records are read-only.")
    contact = get_object_or_404(student.emergency_contacts.all(), pk=contact.pk)
    changed_fields = []
    for field, value in validated_data.items():
        if getattr(contact, field) != value:
            setattr(contact, field, value)
            changed_fields.append(field)
    contact.save()
    _audit(actor, student, "contact.updated", changed_fields)
    return contact
