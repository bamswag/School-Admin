import re
from collections.abc import Mapping

from rest_framework import serializers
from rest_framework.utils.html import is_html_input

from .models import AuditEvent, EmergencyContact, StudentRecord


class RejectUnsupportedFields:
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            writable = {name for name, field in self.fields.items() if not field.read_only}
            unsupported = set(data) - writable
            if is_html_input(data):
                # DRF also accepts indexed nested form fields such as emergency_contacts[0]full_name.
                unsupported = {name for name in unsupported if not self._is_nested_form_field(name, writable)}
            if unsupported:
                raise serializers.ValidationError({name: "This field is not writable." for name in sorted(unsupported)})
        return super().to_internal_value(data)

    def _is_nested_form_field(self, name, writable):
        match = re.fullmatch(r"([^\[]+)\[[0-9]+\].*", name)
        return (
            match is not None and match[1] in writable and isinstance(self.fields[match[1]], serializers.ListSerializer)
        )


class EmergencyContactSerializer(RejectUnsupportedFields, serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ["id", "full_name", "relationship", "phone", "email", "is_primary", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentRecordSerializer(serializers.ModelSerializer):
    person_id = serializers.UUIDField(read_only=True)
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)

    class Meta:
        model = StudentRecord
        fields = [
            "id",
            "person_id",
            "student_number",
            "legal_first_name",
            "legal_middle_names",
            "legal_last_name",
            "date_of_birth",
            "gender",
            "nationality",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "region",
            "postcode",
            "country",
            "status",
            "archived_at",
            "created_at",
            "updated_at",
            "version",
            "emergency_contacts",
        ]
        read_only_fields = fields


class StudentCreateSerializer(RejectUnsupportedFields, serializers.ModelSerializer):
    emergency_contacts = EmergencyContactSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = StudentRecord
        fields = [
            "student_number",
            "legal_first_name",
            "legal_middle_names",
            "legal_last_name",
            "date_of_birth",
            "gender",
            "nationality",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "region",
            "postcode",
            "country",
            "emergency_contacts",
        ]

    def validate_emergency_contacts(self, contacts):
        if sum(contact.get("is_primary", False) for contact in contacts) > 1:
            raise serializers.ValidationError("Only one emergency contact can be primary.")
        return contacts


class StudentUpdateSerializer(RejectUnsupportedFields, serializers.ModelSerializer):
    version = serializers.IntegerField(min_value=1, write_only=True)

    class Meta:
        model = StudentRecord
        fields = [
            "student_number",
            "legal_first_name",
            "legal_middle_names",
            "legal_last_name",
            "date_of_birth",
            "gender",
            "nationality",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "region",
            "postcode",
            "country",
            "status",
            "version",
        ]


class StudentArchiveSerializer(RejectUnsupportedFields, serializers.Serializer):
    version = serializers.IntegerField(min_value=1)


class AuditEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = AuditEvent
        fields = ["id", "occurred_at", "actor_email", "event_type", "changed_fields"]
