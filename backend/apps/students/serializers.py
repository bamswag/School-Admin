from rest_framework import serializers

from .models import AuditEvent, EmergencyContact, StudentRecord


class EmergencyContactSerializer(serializers.ModelSerializer):
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


class StudentCreateSerializer(serializers.ModelSerializer):
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


class StudentUpdateSerializer(serializers.ModelSerializer):
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


class AuditEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = AuditEvent
        fields = ["id", "occurred_at", "actor_email", "event_type", "changed_fields"]
