from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import Membership, User
from apps.organisations.models import Organisation
from apps.students.models import AuditEvent, StudentRecord

pytestmark = pytest.mark.django_db


def student_payload(**overrides):
    payload = {
        "student_number": "DEMO-BRS-200",
        "legal_first_name": "Jamie",
        "legal_middle_names": "River",
        "legal_last_name": "Example",
        "date_of_birth": "2006-02-14",
        "gender": "Prefer not to say",
        "nationality": "GB",
        "email": "jamie@example.invalid",
        "phone": "+440000000001",
        "address_line_1": "1 Fictional Yard",
        "city": "Newmarket",
        "postcode": "CB8 0XX",
        "country": "GB",
        "emergency_contacts": [
            {
                "full_name": "Taylor Example",
                "relationship": "Parent",
                "phone": "+440000000002",
                "email": "taylor@example.invalid",
                "is_primary": True,
            }
        ],
    }
    payload.update(overrides)
    return payload


def make_client(organisation, role=Membership.Role.ADMIN_STAFF):
    user = User.objects.create_user(email=f"{role}.{organisation.code.lower()}@tests.example.invalid", password="test")
    Membership.objects.create(user=user, organisation=organisation, role=role)
    client = APIClient()
    client.force_authenticate(user)
    client.credentials(HTTP_X_ORGANISATION_CODE=organisation.code)
    return client, user


def test_create_student_is_atomic_and_audited():
    brs = Organisation.objects.create(code="BRS", name="British Racing School", organisation_type="institution")
    client, user = make_client(brs)

    response = client.post("/api/v1/students/", student_payload(), format="json")

    assert response.status_code == 201
    record = StudentRecord.objects.get(student_number="DEMO-BRS-200")
    assert record.organisation == brs
    assert record.person.verification_status == "unverified"
    assert record.created_by == user
    assert record.emergency_contacts.get().full_name == "Taylor Example"
    assert AuditEvent.objects.get(student_record=record).event_type == "student.created"


def test_future_date_of_birth_is_rejected():
    brs = Organisation.objects.create(code="BRS", name="British Racing School", organisation_type="institution")
    client, _ = make_client(brs)
    future = (date.today() + timedelta(days=1)).isoformat()

    response = client.post("/api/v1/students/", student_payload(date_of_birth=future), format="json")

    assert response.status_code == 400
    assert StudentRecord.objects.count() == 0


def test_two_primary_contacts_are_rejected():
    brs = Organisation.objects.create(code="BRS", name="British Racing School", organisation_type="institution")
    client, _ = make_client(brs)
    contact = student_payload()["emergency_contacts"][0]

    response = client.post(
        "/api/v1/students/",
        student_payload(emergency_contacts=[contact, {**contact, "email": "other@example.invalid"}]),
        format="json",
    )

    assert response.status_code == 400
    assert StudentRecord.objects.count() == 0


def test_same_student_number_is_unique_per_institution():
    brs = Organisation.objects.create(code="BRS", name="British Racing School", organisation_type="institution")
    sra = Organisation.objects.create(code="SRA", name="Scottish Racing Academy", organisation_type="institution")
    brs_client, _ = make_client(brs)
    sra_client, _ = make_client(sra)

    assert brs_client.post("/api/v1/students/", student_payload(), format="json").status_code == 201
    assert brs_client.post("/api/v1/students/", student_payload(), format="json").status_code == 400
    assert sra_client.post("/api/v1/students/", student_payload(), format="json").status_code == 201


def test_patch_rejects_stale_version_and_immutable_ownership(school_data):
    brs, sra, user, record, _ = school_data
    user.memberships.update(role=Membership.Role.ADMIN_STAFF)
    client = APIClient()
    client.force_authenticate(user)
    client.credentials(HTTP_X_ORGANISATION_CODE=brs.code)

    rejected = client.patch(
        f"/api/v1/students/{record.id}/",
        {"legal_first_name": "Updated", "version": 1, "organisation_id": str(sra.id)},
        format="json",
    )
    assert rejected.status_code == 400
    assert "organisation_id" in rejected.json()
    updated = client.patch(
        f"/api/v1/students/{record.id}/", {"legal_first_name": "Updated", "version": 1}, format="json"
    )
    stale = client.patch(
        f"/api/v1/students/{record.id}/",
        {"legal_first_name": "Stale", "version": 1},
        format="json",
    )

    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert stale.status_code == 409
    assert "refresh" in stale.json()["detail"].lower()
    record.refresh_from_db()
    assert record.legal_first_name == "Updated"
    assert record.organisation == brs


def test_status_transitions_only_from_active(school_data):
    brs, _, user, record, _ = school_data
    user.memberships.update(role=Membership.Role.ADMIN_STAFF)
    client = APIClient()
    client.force_authenticate(user)
    client.credentials(HTTP_X_ORGANISATION_CODE=brs.code)

    completed = client.patch(
        f"/api/v1/students/{record.id}/", {"status": "completed", "version": 1}, format="json"
    )
    reversed_status = client.patch(
        f"/api/v1/students/{record.id}/", {"status": "active", "version": 2}, format="json"
    )

    assert completed.status_code == 200
    assert reversed_status.status_code == 400


def test_archive_preserves_status_and_makes_record_read_only(school_data):
    brs, _, user, record, _ = school_data
    user.memberships.update(role=Membership.Role.ADMIN_STAFF)
    record.status = StudentRecord.Status.COMPLETED
    record.save()
    client = APIClient()
    client.force_authenticate(user)
    client.credentials(HTTP_X_ORGANISATION_CODE=brs.code)

    archived = client.post(f"/api/v1/students/{record.id}/archive/", {"version": 1}, format="json")
    hidden = client.get("/api/v1/students/")
    visible = client.get("/api/v1/students/?include_archived=true")
    edit = client.patch(
        f"/api/v1/students/{record.id}/", {"legal_first_name": "Nope", "version": 2}, format="json"
    )

    assert archived.status_code == 200
    assert archived.json()["status"] == "completed"
    assert hidden.json() == []
    assert len(visible.json()) == 1
    assert edit.status_code == 409


def test_search_and_status_filters_are_tenant_scoped(school_data):
    brs, _, user, brs_record, _ = school_data
    user.memberships.update(role=Membership.Role.ADMIN_STAFF)
    client = APIClient()
    client.force_authenticate(user)
    client.credentials(HTTP_X_ORGANISATION_CODE=brs.code)

    by_name = client.get("/api/v1/students/?q=Avery")
    no_cross_tenant = client.get("/api/v1/students/?q=Morgan")
    by_status = client.get("/api/v1/students/?status=active")

    assert [item["id"] for item in by_name.json()] == [str(brs_record.id)]
    assert no_cross_tenant.json() == []
    assert [item["id"] for item in by_status.json()] == [str(brs_record.id)]


def test_contacts_are_tenant_scoped_and_audited(school_data):
    brs, _, user, brs_record, sra_record = school_data
    user.memberships.update(role=Membership.Role.ADMIN_STAFF)
    client = APIClient()
    client.force_authenticate(user)
    client.credentials(HTTP_X_ORGANISATION_CODE=brs.code)

    created = client.post(
        f"/api/v1/students/{brs_record.id}/emergency-contacts/",
        {"full_name": "Alex Contact", "relationship": "Sibling", "phone": "+440000000003", "is_primary": True},
        format="json",
    )
    cross_tenant = client.post(
        f"/api/v1/students/{sra_record.id}/emergency-contacts/",
        {"full_name": "Leak", "relationship": "Other", "phone": "+440000000004"},
        format="json",
    )
    contact_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/students/{brs_record.id}/emergency-contacts/{contact_id}/",
        {"relationship": "Next of kin"},
        format="json",
    )

    assert created.status_code == 201
    assert updated.status_code == 200
    assert cross_tenant.status_code == 404
    assert AuditEvent.objects.filter(student_record=brs_record, event_type="contact.updated").exists()


def test_audit_events_cannot_be_changed_or_deleted(school_data):
    brs, _, user, record, _ = school_data
    event = AuditEvent.objects.create(
        actor=user,
        organisation=brs,
        student_record=record,
        event_type="student.created",
        changed_fields=["student_number"],
    )
    event.event_type = "tampered"

    with pytest.raises(ValidationError):
        event.save()
    with pytest.raises(ValidationError):
        event.delete()
