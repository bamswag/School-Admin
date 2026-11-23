import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Membership, User
from apps.identity.models import Person
from apps.organisations.models import Organisation
from apps.students.models import StudentRecord

ORGANISATIONS = {
    "BRS": ("British Racing School", Organisation.Type.INSTITUTION),
    "SRA": ("Scottish Racing Academy", Organisation.Type.INSTITUTION),
    "NHC": ("National Horseracing College", Organisation.Type.INSTITUTION),
    "STUD": ("The National Stud", Organisation.Type.INSTITUTION),
    "BHA": ("British Horseracing Authority", Organisation.Type.OVERSIGHT),
}

STUDENTS = {
    "BRS": ("DEMO-BRS-001", "Avery", "Example", "2005-03-10"),
    "SRA": ("DEMO-SRA-001", "Morgan", "Sample", "2004-07-18"),
    "NHC": ("DEMO-NHC-001", "Riley", "Fiction", "2006-01-22"),
    "STUD": ("DEMO-STUD-001", "Casey", "Placeholder", "2003-11-05"),
}


class Command(BaseCommand):
    help = "Seed synthetic-only Task 001 organisations, accounts, and student records."

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get("DEMO_ACCOUNT_PASSWORD")
        if not password:
            raise CommandError("DEMO_ACCOUNT_PASSWORD is required")

        organisations = {}
        for code, (name, organisation_type) in ORGANISATIONS.items():
            organisations[code], _ = Organisation.objects.update_or_create(
                code=code,
                defaults={"name": name, "organisation_type": organisation_type, "is_active": True},
            )

        platform_user, _ = User.objects.get_or_create(
            email="platform.admin@example.invalid",
            defaults={"is_platform_admin": True, "is_staff": True},
        )
        self._set_password(platform_user, password)

        for code in STUDENTS:
            for role in (
                Membership.Role.INSTITUTION_ADMIN,
                Membership.Role.ADMIN_STAFF,
                Membership.Role.READ_ONLY,
            ):
                user, _ = User.objects.get_or_create(email=f"{role}.{code.lower()}@example.invalid")
                self._set_password(user, password)
                Membership.objects.get_or_create(user=user, organisation=organisations[code], defaults={"role": role})

            if not StudentRecord.objects.filter(
                organisation=organisations[code], student_number=STUDENTS[code][0]
            ).exists():
                student_number, first_name, last_name, date_of_birth = STUDENTS[code]
                StudentRecord.objects.create(
                    person=Person.objects.create(),
                    organisation=organisations[code],
                    student_number=student_number,
                    legal_first_name=first_name,
                    legal_last_name=last_name,
                    date_of_birth=date_of_birth,
                )

        for role in (Membership.Role.BHA_ADMIN, Membership.Role.BHA_USER):
            user, _ = User.objects.get_or_create(email=f"{role}@example.invalid")
            self._set_password(user, password)
            Membership.objects.get_or_create(user=user, organisation=organisations["BHA"], defaults={"role": role})

        self.stdout.write(self.style.SUCCESS("Synthetic demo data is ready."))

    @staticmethod
    def _set_password(user, password):
        user.set_password(password)
        user.save(update_fields=["password"])
