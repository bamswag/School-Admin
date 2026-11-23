import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Membership, User

pytestmark = pytest.mark.django_db


def test_list_contains_only_active_tenant_records(brs_client, school_data):
    _, _, _, brs_record, sra_record = school_data

    response = brs_client.get("/api/v1/students/")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(brs_record.id)]
    assert str(sra_record.id) not in response.content.decode()


def test_cross_tenant_detail_is_not_disclosed(brs_client, school_data):
    *_, sra_record = school_data

    response = brs_client.get(f"/api/v1/students/{sra_record.id}/")

    assert response.status_code == 404
    assert "Morgan" not in response.content.decode()


def test_user_without_membership_is_denied(school_data):
    outsider = User.objects.create_user(email="outsider@example.invalid", password="test-password")
    client = APIClient()
    client.force_authenticate(outsider)
    client.credentials(HTTP_X_ORGANISATION_CODE="BRS")

    assert client.get("/api/v1/students/").status_code == 403


def test_inactive_membership_is_denied(brs_client, school_data):
    _, _, user, _, _ = school_data
    user.memberships.update(active=False)

    assert brs_client.get("/api/v1/students/").status_code == 403


@pytest.mark.parametrize("role", [Membership.Role.INSTITUTION_ADMIN, Membership.Role.ADMIN_STAFF])
def test_institution_writer_can_patch_own_student(role, brs_client, school_data):
    _, _, user, brs_record, _ = school_data
    user.memberships.update(role=role)

    response = brs_client.patch(
        f"/api/v1/students/{brs_record.id}/",
        {"legal_first_name": "Updated", "version": 1},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["legal_first_name"] == "Updated"
    assert response.json()["version"] == 2


def test_read_only_user_cannot_patch_student(brs_client, school_data):
    _, sra, _, brs_record, _ = school_data

    response = brs_client.patch(
        f"/api/v1/students/{brs_record.id}/",
        {"legal_first_name": "Blocked", "organisation_id": str(sra.id), "version": 1},
        format="json",
    )

    assert response.status_code == 403
    brs_record.refresh_from_db()
    assert brs_record.organisation.code == "BRS"
    assert brs_record.legal_first_name == "Avery"


def test_writer_cannot_patch_cross_tenant_student(brs_client, school_data):
    _, _, user, _, sra_record = school_data
    user.memberships.update(role=Membership.Role.ADMIN_STAFF)

    response = brs_client.patch(
        f"/api/v1/students/{sra_record.id}/",
        {"legal_first_name": "Blocked", "version": 1},
        format="json",
    )

    assert response.status_code == 404
    sra_record.refresh_from_db()
    assert sra_record.legal_first_name == "Morgan"


@pytest.mark.parametrize("organisation_code", [None, "SRA"])
def test_patch_requires_authorised_institution_context(organisation_code, school_data):
    _, _, user, brs_record, _ = school_data
    user.memberships.update(role=Membership.Role.ADMIN_STAFF)
    client = APIClient()
    client.force_authenticate(user)
    if organisation_code:
        client.credentials(HTTP_X_ORGANISATION_CODE=organisation_code)

    response = client.patch(
        f"/api/v1/students/{brs_record.id}/",
        {"legal_first_name": "Blocked", "version": 1},
        format="json",
    )

    assert response.status_code == 403
    brs_record.refresh_from_db()
    assert brs_record.legal_first_name == "Avery"


def test_patch_rejects_invalid_input(brs_client, school_data):
    _, _, user, brs_record, _ = school_data
    user.memberships.update(role=Membership.Role.ADMIN_STAFF)

    response = brs_client.patch(
        f"/api/v1/students/{brs_record.id}/",
        {"date_of_birth": "not-a-date", "version": 1},
        format="json",
    )

    assert response.status_code == 400
    brs_record.refresh_from_db()
    assert brs_record.date_of_birth.isoformat() == "2005-03-10"
