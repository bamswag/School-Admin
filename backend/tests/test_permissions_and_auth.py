from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Membership, User
from apps.organisations.models import Organisation

from .test_student_crud import make_client, student_payload

pytestmark = pytest.mark.django_db


@pytest.fixture
def session_client():
    cache.clear()
    yield APIClient(enforce_csrf_checks=True)
    cache.clear()


def login_request(client, email, password, **extra):
    return client.post(
        "/api/v1/auth/login/",
        {"email": email, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        **extra,
    )


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


def test_student_api_requires_session_authentication():
    client = APIClient()
    anonymous = client.get("/api/v1/students/", HTTP_X_ORGANISATION_CODE="BRS")
    with_basic_header = client.get("/api/v1/students/", HTTP_X_ORGANISATION_CODE="BRS", HTTP_AUTHORIZATION="Basic")
    assert anonymous.status_code == with_basic_header.status_code == 403
    assert anonymous.json() == with_basic_header.json()


def test_session_login_logout_and_memberships(session_client):
    brs = Organisation.objects.create(code="BRS", name="British Racing School", organisation_type="institution")
    user = User.objects.create_user(email="staff@example.invalid", password="correct-password")
    Membership.objects.create(user=user, organisation=brs, role=Membership.Role.ADMIN_STAFF)
    client = session_client

    session = client.get("/api/v1/auth/session/")
    assert session.status_code == 200
    assert session.json() == {"authenticated": False, "user": None, "memberships": []}
    assert "no-store" in session.headers["Cache-Control"]
    csrf_token = session.cookies["csrftoken"].value
    login = client.post(
        "/api/v1/auth/login/",
        {"email": "staff@example.invalid", "password": "correct-password"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    logged_in = client.get("/api/v1/auth/session/")
    assert login.status_code == 200
    assert login.cookies["csrftoken"].value != csrf_token
    assert login.json()["memberships"][0]["organisation"]["code"] == "BRS"
    assert logged_in.json() == login.json()
    assert client.get("/api/v1/students/", HTTP_X_ORGANISATION_CODE="BRS").status_code == 200
    assert (
        client.post("/api/v1/students/", student_payload(), format="json", HTTP_X_ORGANISATION_CODE="BRS").status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/students/",
            student_payload(),
            format="json",
            HTTP_X_ORGANISATION_CODE="BRS",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        ).status_code
        == 201
    )
    assert client.post("/api/v1/auth/logout/", {}, format="json", HTTP_X_CSRFTOKEN=csrf_token).status_code == 403
    logout = client.post("/api/v1/auth/logout/", {}, format="json", HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
    assert logout.status_code == 200
    assert logout.json() == session.json()
    assert client.get("/api/v1/students/", HTTP_X_ORGANISATION_CODE="BRS").status_code in {401, 403}
    assert client.get("/api/v1/auth/session/").json()["authenticated"] is False


def test_login_errors_are_generic_and_throttled(session_client):
    User.objects.create_user(email="staff@example.invalid", password="correct-password")
    client = session_client
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

    assert [response.status_code for response in responses] == [401] * 5 + [429]
    assert responses[0].json()["message"] == "Invalid email or password."


@pytest.mark.parametrize("endpoint", ["login", "logout"])
def test_session_posts_require_csrf(session_client, endpoint):
    assert session_client.post(f"/api/v1/auth/{endpoint}/", {}, format="json").status_code == 403


def test_session_memberships_are_current_and_scoped(session_client):
    user = User.objects.create_user(email="staff@example.invalid", password=" spaced-password ")
    other_user = User.objects.create_user(email="other@example.invalid")
    for code, org_type, org_active, membership_active, owner, role in [
        ("BRS", "institution", True, True, user, Membership.Role.ADMIN_STAFF),
        ("BHA", "oversight", True, True, user, Membership.Role.BHA_USER),
        ("NHC", "institution", False, True, user, Membership.Role.ADMIN_STAFF),
        ("SRA", "institution", True, False, user, Membership.Role.ADMIN_STAFF),
        ("STUD", "institution", True, True, other_user, Membership.Role.ADMIN_STAFF),
    ]:
        org = Organisation.objects.create(code=code, name=code, organisation_type=org_type, is_active=org_active)
        Membership.objects.create(user=owner, organisation=org, role=role, active=membership_active)

    session_client.get("/api/v1/auth/session/")
    response = login_request(session_client, "STAFF@example.invalid", " spaced-password ")
    assert response.status_code == 200
    assert response.json()["user"] == {"id": str(user.id), "email": user.email}
    assert [row["organisation"]["code"] for row in response.json()["memberships"]] == ["BHA", "BRS"]
    Membership.objects.filter(user=user, organisation__code="BRS").update(active=False)
    refreshed = session_client.get("/api/v1/auth/session/").json()
    assert [row["organisation"]["code"] for row in refreshed["memberships"]] == ["BHA"]
    assert session_client.get("/api/v1/students/", HTTP_X_ORGANISATION_CODE="BRS").status_code == 403
    assert session_client.get("/api/v1/students/", HTTP_X_ORGANISATION_CODE="BHA").status_code == 403


def test_invalid_credentials_have_identical_responses(session_client):
    User.objects.create_user(email="active@example.invalid", password="correct-password")
    User.objects.create_user(email="inactive@example.invalid", password="correct-password", is_active=False)
    session_client.get("/api/v1/auth/session/")
    for email, password in [
        ("active@example.invalid", "wrong-password"),
        ("inactive@example.invalid", "correct-password"),
        ("unknown@example.invalid", "correct-password"),
    ]:
        response = login_request(session_client, email, password)
        assert response.status_code == 401
        assert response.json() == {"message": "Invalid email or password."}
    assert session_client.get("/api/v1/auth/session/").json()["authenticated"] is False


@pytest.mark.parametrize("limit_by", ["email", "ip"])
def test_login_limits_email_and_ip_independently(session_client, limit_by):
    session_client.get("/api/v1/auth/session/")
    for attempt in range(6):
        email = f"staff-{attempt if limit_by == 'ip' else 0}@example.invalid"
        ip = f"192.0.2.{attempt + 1 if limit_by == 'email' else 1}"
        response = login_request(session_client, email, "wrong", REMOTE_ADDR=ip)
        assert response.status_code == (401 if attempt < 5 else 429)


def test_session_expires_after_an_hour_of_inactivity(session_client, monkeypatch):
    User.objects.create_user(email="staff@example.invalid", password="correct-password")
    now = timezone.now()
    monkeypatch.setattr(timezone, "now", lambda: now)
    session_client.get("/api/v1/auth/session/")
    response = login_request(session_client, "staff@example.invalid", "correct-password")
    cookie = response.cookies["sessionid"]
    assert cookie["max-age"] == 3600
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"
    now += timedelta(minutes=59)
    assert session_client.get("/api/v1/auth/session/").json()["authenticated"] is True
    now += timedelta(minutes=59)
    assert session_client.get("/api/v1/auth/session/").json()["authenticated"] is True
    now += timedelta(minutes=60, seconds=1)
    assert session_client.get("/api/v1/auth/session/").json()["authenticated"] is False
