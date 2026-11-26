from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event
from time import monotonic
from uuid import uuid4

import pytest
from django.db import DatabaseError, IntegrityError, connection, connections, transaction
from rest_framework.test import APIClient

from apps.accounts.models import Membership
from apps.identity.models import Person
from apps.students import services
from apps.students.models import AuditEvent, EmergencyContact, StudentRecord

from .test_student_crud import make_client, student_payload

pytestmark = pytest.mark.django_db

STUDENTS = "/api/v1/students/"
CONTACT = {"full_name": "Synthetic Contact", "relationship": "Sibling", "phone": "0000000000"}


@pytest.mark.parametrize(
    "action,field",
    [
        ("create", "unexpected"),
        ("create", "version"),
        ("create", "created_by"),
        ("edit", "person_id"),
        ("archive", "archived_at"),
        ("contact_create", "student_record_id"),
        ("contact_edit", "id"),
        ("nested", "updated_at"),
    ],
)
def test_invalid_write_fields_are_rejected(school_data, action, field):
    school, _, _, student, _ = school_data
    client, _ = make_client(school)
    detail = f"{STUDENTS}{student.pk}/"
    contacts = f"{detail}emergency-contacts/"
    contact = EmergencyContact.objects.create(student_record=student, **CONTACT)
    instructions = {
        "create": (client.post, STUDENTS, student_payload()),
        "edit": (client.patch, detail, {"version": 1}),
        "archive": (client.post, f"{detail}archive/", {"version": 1}),
        "contact_create": (client.post, contacts, CONTACT.copy()),
        "contact_edit": (client.patch, f"{contacts}{contact.pk}/", {}),
        "nested": (client.post, STUDENTS, student_payload(emergency_contacts=[CONTACT.copy()])),
    }
    request, path, data = instructions[action]
    subject = data["emergency_contacts"][0] if action == "nested" else data
    subject[field] = "synthetic-value"

    response = request(path, data, format="json")

    assert response.status_code == 400
    errors = response.json()
    if action == "nested":
        errors = errors["emergency_contacts"][0]
    assert field in errors
    assert b"synthetic-value" not in response.content
    student.refresh_from_db()
    assert student.version == 1
    assert student.archived_at is None
    assert StudentRecord.objects.count() == 2
    assert EmergencyContact.objects.count() == 1
    assert not AuditEvent.objects.exists()


def test_malformed_student_json_returns_safe_error(school_data, brs_client):
    school, *_ = school_data
    client, _ = make_client(school)
    response = client.post(STUDENTS, data="{", content_type="application/json")
    assert response.status_code == 400
    assert response.json() == {"detail": "Malformed request body."}
    assert brs_client.post(STUDENTS, data="{", content_type="application/json").status_code == 403


def test_create_preserves_nested_multipart_shape(school_data):
    school, *_ = school_data
    client, _ = make_client(school)
    data = student_payload()
    data.pop("emergency_contacts")
    data.update({f"emergency_contacts[0]{field}": value for field, value in CONTACT.items()})
    response = client.post(STUDENTS, data, format="multipart")
    assert response.status_code == 201
    assert [contact["full_name"] for contact in response.json()["emergency_contacts"]] == [CONTACT["full_name"]]


@pytest.mark.parametrize("database_constraint", [False, True])
def test_duplicate_student_number_has_field_error(school_data, monkeypatch, database_constraint):
    school, other_school, _, existing, other = school_data
    client, _ = make_client(school)
    other_client, _ = make_client(other_school)
    if database_constraint:
        monkeypatch.setattr(StudentRecord, "validate_constraints", lambda self, exclude=None: None)
    count = Person.objects.count()
    payload = student_payload(student_number=existing.student_number)
    duplicate = client.post(STUDENTS, payload, format="json")
    assert duplicate.status_code == 400
    assert set(duplicate.json()) == {"student_number"}
    assert Person.objects.count() == count
    assert not AuditEvent.objects.exists()
    created = other_client.post(STUDENTS, payload, format="json")
    assert created.status_code == 201
    update = other_client.patch(
        f"{STUDENTS}{other.pk}/", {"version": 1, "student_number": existing.student_number}, format="json"
    )
    assert update.status_code == 400
    assert update.json() == duplicate.json()
    other.refresh_from_db()
    assert other.version == 1
    assert other.student_number != existing.student_number


@pytest.mark.parametrize("database_constraint", [False, True])
def test_second_primary_contact_has_field_error(school_data, monkeypatch, database_constraint):
    school, _, _, student, _ = school_data
    client, _ = make_client(school)
    EmergencyContact.objects.create(student_record=student, is_primary=True, **CONTACT)
    if database_constraint:
        monkeypatch.setattr(EmergencyContact, "validate_constraints", lambda self, exclude=None: None)
    path = f"{STUDENTS}{student.pk}/emergency-contacts/"
    response = client.post(path, {**CONTACT, "is_primary": True}, format="json")
    assert response.status_code == 400
    assert set(response.json()) == {"is_primary"}
    assert student.emergency_contacts.count() == 1
    assert not student.audit_events.exists()


def test_database_rejects_contact_without_existing_student():
    with pytest.raises(IntegrityError), transaction.atomic():
        EmergencyContact.objects.bulk_create([EmergencyContact(student_record_id=uuid4(), **CONTACT)])
        connection.check_constraints(table_names=[EmergencyContact._meta.db_table])
    assert not EmergencyContact.objects.exists()


@pytest.mark.parametrize("action", ["create", "edit"])
def test_student_write_rolls_back_after_late_database_failure(school_data, monkeypatch, action):
    school, _, _, student, _ = school_data
    client, _ = make_client(school)
    client.raise_request_exception = False
    person_count = Person.objects.count()
    audit = services._audit

    def fail_after_audit(*args):
        audit(*args)
        raise DatabaseError("internal-only diagnostic")

    def save():
        if action == "create":
            return client.post(STUDENTS, student_payload(), format="json")
        return client.patch(f"{STUDENTS}{student.pk}/", {"version": 1, "legal_first_name": "Updated"}, format="json")

    with monkeypatch.context() as patch:
        patch.setattr(services, "_audit", fail_after_audit)
        response = save()

    assert response.status_code == 500
    assert response.json() == {"detail": "The student request could not be completed."}
    student.refresh_from_db()
    assert student.legal_first_name == "Avery"
    assert student.version == 1
    assert student.updated_by_id is None
    assert StudentRecord.objects.count() == 2
    assert Person.objects.count() == person_count
    assert not EmergencyContact.objects.exists()
    assert not AuditEvent.objects.exists()
    assert save().status_code == (201 if action == "create" else 200)


@pytest.mark.django_db(transaction=True)
def test_postgresql_concurrent_student_updates_preserve_first_write(school_data, monkeypatch):
    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    school, _, _, student, _ = school_data
    _, staff_a = make_client(school, Membership.Role.ADMIN_STAFF)
    _, staff_b = make_client(school, Membership.Role.INSTITUTION_ADMIN)
    first_saved = Event()
    release_first = Event()
    first_pid = Queue()
    second_pid = Queue()
    audit = services._audit
    lock_student = services._lock_student

    def hold_first_write(actor, *args):
        audit(actor, *args)
        if actor.pk == staff_a.pk:
            first_pid.put(connection.connection.info.backend_pid)
            first_saved.set()
            assert release_first.wait(10)

    def signal_second_lock(record):
        if first_saved.is_set():
            second_pid.put(connection.connection.info.backend_pid)
        return lock_student(record)

    monkeypatch.setattr(services, "_audit", hold_first_write)
    monkeypatch.setattr(services, "_lock_student", signal_second_lock)

    def save(actor, name):
        client = APIClient()
        client.force_authenticate(actor)
        client.credentials(HTTP_X_ORGANISATION_CODE=school.code)
        try:
            return client.patch(f"{STUDENTS}{student.pk}/", {"version": 1, "legal_first_name": name}, format="json")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(save, staff_a, "First")
        try:
            assert first_saved.wait(10)
            second = workers.submit(save, staff_b, "Second")
            blocker = first_pid.get(timeout=5)
            waiting = second_pid.get(timeout=5)
            deadline = monotonic() + 5
            with connection.cursor() as cursor:
                while monotonic() < deadline:
                    cursor.execute("SELECT pg_blocking_pids(%s)", [waiting])
                    if blocker in cursor.fetchone()[0]:
                        break
                    release_first.wait(0.02)
                else:
                    pytest.fail("Staff B never waited for Staff A's transaction lock")
        finally:
            release_first.set()
        assert first.result(timeout=10).status_code == 200
        rejected = second.result(timeout=10)

    assert rejected.status_code == 409
    assert "refresh" in rejected.json()["detail"].lower()
    student.refresh_from_db()
    assert student.legal_first_name == "First"
    assert student.version == 2
    assert student.audit_events.get().actor_id == staff_a.pk
