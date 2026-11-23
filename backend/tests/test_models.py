import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import Membership, User
from apps.identity.models import Person
from apps.organisations.models import Organisation
from apps.students.models import StudentRecord

pytestmark = pytest.mark.django_db


def test_person_starts_unverified():
    assert Person.objects.create().verification_status == "unverified"


def test_bha_role_cannot_be_assigned_to_school():
    school = Organisation.objects.create(code="BRS", name="British Racing School", organisation_type="institution")
    user = User.objects.create_user(email="bha@demo.example.invalid", password="test-password")

    with pytest.raises(ValidationError):
        Membership.objects.create(user=user, organisation=school, role="bha_user")


def test_oversight_organisation_cannot_own_student():
    bha = Organisation.objects.create(code="BHA", name="British Horseracing Authority", organisation_type="oversight")

    with pytest.raises(ValidationError):
        StudentRecord.objects.create(
            person=Person.objects.create(),
            organisation=bha,
            student_number="DEMO-BHA-001",
            legal_first_name="Invalid",
            legal_last_name="Owner",
            date_of_birth="2000-01-01",
        )
