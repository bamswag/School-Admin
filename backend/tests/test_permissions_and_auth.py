import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import Membership, User
from apps.organisations.models import Organisation

from .test_student_crud import make_client, student_payload


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("role", [Membership.Role.READ_ONLY, Membership.Role.BHA_USER])
def test_non_writers_cannot_create_students(role):
    organisation_type = "oversight" if role == Membership.Role.BHA_USER else "institution"
    code = "BHA" if role == Membership.Role.BHA_USER else "BRS"
    organisation = Organisation.objects.create(code=code, name=code, organisation_type=organisation_type)
    client, _ = make_client(organisation, role)

    assert client.post("/api/v1/students/", student_payload(), format="json").status_code == 403


def test_read_only_user_can_read_but_not_patch_or_archive(school_data):
    brs, _, user, record, _ = school_data
    client = APIClient()
    client.force_authenticate(user)
    client.credentials(HTTP_X_ORGANISATION_CODE=brs.code)

    assert client.get(f"/api/v1/students/{record.id}/").status_code == 200
    assert client.patch(f"/api/v1/students/{record.id}/", {"version": 1}, format="json").status_code == 403
    assert client.post(f"/api/v1/students/{record.id}/archive/", {"version": 1}, format="json").status_code == 403


def test_platform_and_unauthenticated_users_are_denied():
    client = APIClient()
    assert client.get("/api/v1/students/").status_code in {401, 403}

    platform = User.objects.create_user(email="platform@example.invalid", password="test", is_platform_admin=True)
    client.force_authenticate(platform)
    client.credentials(HTTP_X_ORGANISATION_CODE="BRS")
    assert client.get("/api/v1/students/").status_code == 403


def test_session_login_logout_and_memberships():
    brs = Organisation.objects.create(code="BRS", name="British Racing School", organisation_type="institution")
    user = User.objects.create_user(email="staff@example.invalid", password="correct-password")
    Membership.objects.create(user=user, organisation=brs, role=Membership.Role.ADMIN_STAFF)
    client = APIClient(enforce_csrf_checks=True)

    session = client.get("/api/v1/auth/session/")
    csrf_token = session.cookies["csrftoken"].value
    login = client.post(
        "/api/v1/auth/login/",
        {"email": "staff@example.invalid", "password": "correct-password"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    logged_in = client.get("/api/v1/auth/session/")
    logout = client.post("/api/v1/auth/logout/", {}, format="json", HTTP_X_CSRFTOKEN=csrf_token)

    assert login.status_code == 200
    assert login.json()["memberships"][0]["organisation"]["code"] == "BRS"
    assert logged_in.json()["authenticated"] is True
    assert logout.status_code == 200
    assert client.get("/api/v1/auth/session/").json()["authenticated"] is False


def test_login_errors_are_generic_and_throttled():
    cache.clear()
    User.objects.create_user(email="staff@example.invalid", password="correct-password")
    client = APIClient(enforce_csrf_checks=True)
    csrf_token = client.get("/api/v1/auth/session/").cookies["csrftoken"].value

    responses = [
        client.post(
            "/api/v1/auth/login/",
            {"email": "staff@example.invalid", "password": "wrong"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        for _ in range(6)
    ]

    assert responses[0].status_code == 401
    assert responses[0].json()["message"] == "Invalid email or password."
    assert responses[-1].status_code == 429
