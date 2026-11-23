import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Membership, User
from apps.identity.models import Person
from apps.organisations.models import Organisation
from apps.students.models import StudentRecord


@pytest.fixture
def school_data(db):
    brs = Organisation.objects.create(code="BRS", name="British Racing School", organisation_type="institution")
    sra = Organisation.objects.create(code="SRA", name="Scottish Racing Academy", organisation_type="institution")
    brs_user = User.objects.create_user(email="reader@brs.example.invalid", password="test-password")
    Membership.objects.create(user=brs_user, organisation=brs, role="read_only")
    brs_record = StudentRecord.objects.create(
        person=Person.objects.create(),
        organisation=brs,
        student_number="DEMO-BRS-001",
        legal_first_name="Avery",
        legal_last_name="Example",
        date_of_birth="2005-03-10",
    )
    sra_record = StudentRecord.objects.create(
        person=Person.objects.create(),
        organisation=sra,
        student_number="DEMO-SRA-001",
        legal_first_name="Morgan",
        legal_last_name="Sample",
        date_of_birth="2004-07-18",
    )
    return brs, sra, brs_user, brs_record, sra_record


@pytest.fixture
def brs_client(school_data):
    brs, _, user, _, _ = school_data
    client = APIClient()
    client.force_authenticate(user)
    client.credentials(HTTP_X_ORGANISATION_CODE=brs.code)
    return client
