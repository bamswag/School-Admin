import uuid

from django.db import models


class Organisation(models.Model):
    class Type(models.TextChoices):
        INSTITUTION = "institution", "Institution"
        OVERSIGHT = "oversight", "Oversight"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=160)
    organisation_type = models.CharField(max_length=20, choices=Type.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code
