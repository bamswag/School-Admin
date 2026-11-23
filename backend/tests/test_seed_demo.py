from django.core.management import call_command

from apps.accounts.models import Membership, User
from apps.identity.models import Person
from apps.organisations.models import Organisation
from apps.students.models import StudentRecord


def test_seed_demo_is_idempotent(db, monkeypatch):
    monkeypatch.setenv("DEMO_ACCOUNT_PASSWORD", "test-password")

    call_command("seed_demo")
    call_command("seed_demo")

    assert set(Organisation.objects.values_list("code", flat=True)) == {"BRS", "SRA", "NHC", "STUD", "BHA"}
    assert Organisation.objects.filter(organisation_type="institution").count() == 4
    assert Organisation.objects.filter(code="BHA", organisation_type="oversight").count() == 1
    assert User.objects.count() == 15
    assert Membership.objects.count() == 14
    assert Person.objects.count() == 4
    assert StudentRecord.objects.count() == 4
