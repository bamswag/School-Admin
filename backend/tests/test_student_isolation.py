from uuid import uuid4

import pytest
from django.utils import timezone

from apps.accounts.models import Membership
from apps.identity.models import Person
from apps.organisations.models import Organisation
from apps.students.models import AuditEvent, EmergencyContact, StudentRecord

from .test_student_crud import make_client, student_payload

pytestmark = pytest.mark.django_db

STUDENTS = "/api/v1/students/"
CONTACT = {"full_name": "Fictional Contact", "relationship": "Sibling", "phone": "+440000000003"}


@pytest.mark.parametrize(
    "context", ["missing", "wrong", "revoked", "inactive_school", "bha", "role_mismatch", "platform"]
)
def test_student_routes_require_current_institution_membership(brs_client, school_data, context):
    brs, sra, user, record, _ = school_data
    assert brs_client.get(STUDENTS).status_code == 200
    assert brs_client.options(STUDENTS).status_code == 200
    if context == "missing":
        brs_client.credentials()
    elif context == "wrong":
        brs_client.credentials(HTTP_X_ORGANISATION_CODE=sra.code)
    elif context == "revoked":
        user.memberships.update(active=False)
    elif context == "inactive_school":
        Organisation.objects.filter(pk=brs.pk).update(is_active=False)
    elif context == "bha":
        user.memberships.update(active=False)
        bha = Organisation.objects.create(code="BHA", name="Synthetic oversight", organisation_type="oversight")
        Membership.objects.create(user=user, organisation=bha, role=Membership.Role.BHA_USER)
        brs_client.credentials(HTTP_X_ORGANISATION_CODE=bha.code)
    elif context == "role_mismatch":
        user.memberships.update(role=Membership.Role.BHA_USER)
    else:
        user.memberships.update(active=False)
        user.is_platform_admin = True
        user.is_superuser = True
        user.save(update_fields=["is_platform_admin", "is_superuser"])

    detail = f"{STUDENTS}{record.pk}/"
    contacts = f"{detail}emergency-contacts/"
    for method, path in (
        ("get", STUDENTS),
        ("get", f"{STUDENTS}?q=Avery"),
        ("options", STUDENTS),
        ("post", STUDENTS),
        ("get", detail),
        ("patch", detail),
        ("post", f"{detail}archive/"),
        ("get", f"{detail}history/"),
        ("get", contacts),
        ("head", contacts),
        ("post", contacts),
        ("patch", f"{contacts}{uuid4()}/"),
    ):
        assert getattr(brs_client, method)(path).status_code == 403, (method, path, context)


@pytest.mark.parametrize("role", [Membership.Role.READ_ONLY, Membership.Role.ADMIN_STAFF])
def test_contact_head_is_read_only(brs_client, school_data, role):
    _, _, user, record, _ = school_data
    user.memberships.update(role=role)
    contacts = f"{STUDENTS}{record.pk}/emergency-contacts/"
    response = brs_client.head(contacts)
    assert response.status_code == 200
    assert response.content == b""
    assert not record.emergency_contacts.exists()
    assert not record.audit_events.exists()


@pytest.mark.parametrize(
    "method,suffix",
    [
        ("get", ""),
        ("patch", ""),
        ("post", "archive/"),
        ("get", "history/"),
        ("get", "emergency-contacts/"),
        ("post", "emergency-contacts/"),
    ],
)
def test_foreign_and_malformed_student_ids_match_missing_response(school_data, method, suffix):
    brs, _, _, _, foreign = school_data
    client, _ = make_client(brs)
    client.raise_request_exception = False
    request = getattr(client, method)
    missing = request(f"{STUDENTS}{uuid4()}/{suffix}")
    assert missing.status_code == 404
    for student_id in (foreign.pk, "invalid-id"):
        response = request(f"{STUDENTS}{student_id}/{suffix}")
        assert response.status_code == 404
        assert response.json() == missing.json()


def test_nested_contact_lookup_uses_exact_parent(school_data):
    brs, _, user, own, foreign = school_data
    client, _ = make_client(brs)
    client.raise_request_exception = False
    sibling = StudentRecord.objects.create(
        organisation=brs,
        person=Person.objects.create(),
        student_number="DEMO-SIBLING",
        legal_first_name="Fictional",
        legal_last_name="Sibling",
        date_of_birth=own.date_of_birth,
    )
    contacts = [EmergencyContact.objects.create(student_record=student, **CONTACT) for student in (sibling, foreign)]
    path = f"{STUDENTS}{own.pk}/emergency-contacts/"
    missing = client.patch(f"{path}{uuid4()}/")
    assert missing.status_code == 404
    for contact_id in (contacts[0].pk, contacts[1].pk, "invalid-id"):
        response = client.patch(f"{path}{contact_id}/")
        assert response.status_code == 404
        assert response.json() == missing.json()
    assert all(contact.relationship == "Sibling" for contact in EmergencyContact.objects.all())
    assert not AuditEvent.objects.exists()

    client.force_authenticate(user)
    for student_id in (own.pk, uuid4()):
        response = client.post(f"{STUDENTS}{student_id}/emergency-contacts/", CONTACT, format="json")
        assert response.status_code == 403
    assert EmergencyContact.objects.count() == 2


@pytest.mark.parametrize("role", [Membership.Role.INSTITUTION_ADMIN, Membership.Role.ADMIN_STAFF])
def test_history_serializes_only_events_owned_by_selected_school(school_data, role):
    brs, sra, _, own, _ = school_data
    client, writer = make_client(brs, role)
    event = AuditEvent.objects.create(
        actor=writer,
        organisation=brs,
        student_record=own,
        event_type="student.updated",
        changed_fields=["email"],
    )
    _, foreign_actor = make_client(sra, role)
    AuditEvent.objects.create(
        actor=foreign_actor,
        organisation=sra,
        student_record=own,
        event_type="student.updated",
        changed_fields=["phone"],
    )
    response = client.get(f"{STUDENTS}{own.pk}/history/")
    assert response.status_code == 200
    assert [entry["id"] for entry in response.json()] == [str(event.pk)]
    assert set(response.json()[0]) == {"id", "occurred_at", "actor_email", "event_type", "changed_fields"}


def test_switching_school_uses_its_role_and_search_scope(brs_client, school_data):
    brs, sra, user, own, foreign = school_data
    Membership.objects.create(user=user, organisation=sra, role=Membership.Role.ADMIN_STAFF)
    path = f"{STUDENTS}{foreign.pk}/emergency-contacts/"
    EmergencyContact.objects.create(student_record=foreign, **CONTACT)
    foreign.email = "synthetic@foreign.example.invalid"
    foreign.save()
    assert brs_client.get(STUDENTS, {"q": foreign.email}).json() == []
    assert brs_client.get(STUDENTS, {"q": CONTACT["full_name"]}).json() == []
    assert brs_client.post(STUDENTS, student_payload(), format="json").status_code == 403
    brs_client.credentials(HTTP_X_ORGANISATION_CODE=sra.code)
    rows = brs_client.get(STUDENTS, {"q": foreign.email}).json()
    assert [row["id"] for row in rows] == [str(foreign.pk)]
    assert {"organisation", "created_by", "updated_by", "archived_by"}.isdisjoint(rows[0])
    assert {"student_record", "organisation"}.isdisjoint(rows[0]["emergency_contacts"][0])
    assert brs_client.get(f"{STUDENTS}{own.pk}/").status_code == 404
    assert brs_client.get(path).status_code == 200
    rejected = brs_client.post(STUDENTS, student_payload(organisation_id=str(brs.pk)), format="json")
    assert rejected.status_code == 400
    assert "organisation_id" in rejected.json()
    created = brs_client.post(STUDENTS, student_payload(), format="json")
    assert created.status_code == 201
    assert StudentRecord.objects.get(pk=created.json()["id"]).organisation_id == sra.pk


@pytest.mark.parametrize("payload", [{"version": True}, {"version": 1.5}, {"version": None}, {}])
def test_archive_rejects_invalid_version_without_mutation(school_data, payload):
    brs, _, _, record, _ = school_data
    client, _ = make_client(brs)
    response = client.post(f"{STUDENTS}{record.pk}/archive/", payload, format="json")
    assert response.status_code == 400
    assert "version" in response.json()
    record.refresh_from_db()
    assert record.archived_at is None
    assert not record.audit_events.exists()


@pytest.mark.parametrize("method", ["post", "patch"])
def test_contact_writes_recheck_parent_archival(school_data, monkeypatch, method):
    from apps.students import views

    brs, _, _, own, _ = school_data
    client, _ = make_client(brs)
    path = f"{STUDENTS}{own.pk}/emergency-contacts/"
    contact = EmergencyContact.objects.create(student_record=own, **CONTACT)
    if method == "patch":
        path += f"{contact.pk}/"

    service_name = "create_contact" if method == "post" else "update_contact"
    service = getattr(views, service_name)

    def archive_before_write(*args):
        StudentRecord.objects.filter(pk=own.pk).update(archived_at=timezone.now())
        return service(*args)

    monkeypatch.setattr(views, service_name, archive_before_write)
    response = getattr(client, method)(path, {**CONTACT, "relationship": "Parent"}, format="json")
    assert response.status_code == 409
    contact.refresh_from_db()
    assert contact.relationship == CONTACT["relationship"]
    assert own.emergency_contacts.count() == 1
    assert not own.audit_events.exists()
