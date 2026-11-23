import uuid
from datetime import date

from django.core.exceptions import ValidationError
from django.db import models

from apps.identity.models import Person
from apps.organisations.models import Organisation


class StudentRecord(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        WITHDRAWN = "withdrawn", "Withdrawn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="student_records")
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="student_records")
    student_number = models.CharField(max_length=50)
    legal_first_name = models.CharField(max_length=100)
    legal_middle_names = models.CharField(max_length=150, blank=True)
    legal_last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=40, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    address_line_1 = models.CharField(max_length=200, blank=True)
    address_line_2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    postcode = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, blank=True, related_name="archived_students"
    )
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, blank=True, related_name="created_students"
    )
    updated_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, blank=True, related_name="updated_students"
    )
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "student_number"],
                name="unique_student_number_per_organisation",
            )
        ]
        indexes = [
            models.Index(fields=["organisation", "status", "archived_at"]),
            models.Index(fields=["organisation", "legal_last_name"]),
        ]
        ordering = ["legal_last_name", "legal_first_name", "id"]

    def clean(self):
        if self.organisation.organisation_type != Organisation.Type.INSTITUTION:
            raise ValidationError({"organisation": "Only institutions can own student records."})
        if self.date_of_birth and self.date_of_birth > date.today():
            raise ValidationError({"date_of_birth": "Date of birth cannot be in the future."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class EmergencyContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student_record = models.ForeignKey(StudentRecord, on_delete=models.PROTECT, related_name="emergency_contacts")
    full_name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=80)
    phone = models.CharField(max_length=32)
    email = models.EmailField(blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "full_name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["student_record"],
                condition=models.Q(is_primary=True),
                name="one_primary_contact_per_student",
            )
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    occurred_at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="student_audit_events")
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="student_audit_events")
    student_record = models.ForeignKey(StudentRecord, on_delete=models.PROTECT, related_name="audit_events")
    event_type = models.CharField(max_length=80)
    changed_fields = models.JSONField(default=list)

    class Meta:
        ordering = ["-occurred_at", "-id"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Audit events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit events are append-only.")
