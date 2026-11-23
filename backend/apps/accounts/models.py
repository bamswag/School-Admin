import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models

from apps.organisations.models import Organisation


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_platform_admin", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Superuser requires is_staff and is_superuser")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_platform_admin = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"

    def __str__(self):
        return self.email


class Membership(models.Model):
    class Role(models.TextChoices):
        INSTITUTION_ADMIN = "institution_admin", "Institution administrator"
        ADMIN_STAFF = "admin_staff", "Administrative staff"
        READ_ONLY = "read_only", "Read only"
        BHA_ADMIN = "bha_admin", "BHA administrator"
        BHA_USER = "bha_user", "BHA user"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="memberships")
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="memberships")
    role = models.CharField(max_length=30, choices=Role.choices)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "organisation"], name="unique_user_organisation")]

    def clean(self):
        school_roles = {self.Role.INSTITUTION_ADMIN, self.Role.ADMIN_STAFF, self.Role.READ_ONLY}
        if self.organisation.organisation_type == Organisation.Type.INSTITUTION and self.role not in school_roles:
            raise ValidationError({"role": "This role is not valid for an institution."})
        if self.organisation.organisation_type == Organisation.Type.OVERSIGHT and self.role in school_roles:
            raise ValidationError({"role": "This role is not valid for an oversight organisation."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
