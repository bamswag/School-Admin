import pytest

from apps.accounts.models import User

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
    from rest_framework.test import APIClient

    outsider = User.objects.create_user(email="outsider@example.invalid", password="test-password")
    client = APIClient()
    client.force_authenticate(outsider)
    client.credentials(HTTP_X_ORGANISATION_CODE="BRS")

    assert client.get("/api/v1/students/").status_code == 403


def test_inactive_membership_is_denied(brs_client, school_data):
    _, _, user, _, _ = school_data
    user.memberships.update(active=False)

    assert brs_client.get("/api/v1/students/").status_code == 403


def test_patch_cannot_change_organisation_ownership(brs_client, school_data):
    _, sra, _, brs_record, _ = school_data

    response = brs_client.patch(
        f"/api/v1/students/{brs_record.id}/",
        {"organisation_id": str(sra.id)},
        format="json",
    )

    assert response.status_code == 405
    brs_record.refresh_from_db()
    assert brs_record.organisation.code == "BRS"
