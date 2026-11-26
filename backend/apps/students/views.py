from django.db.models import Q
from django.http import Http404
from rest_framework import exceptions, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from apps.accounts.models import Membership
from apps.organisations.models import Organisation

from .errors import public_student_error
from .models import EmergencyContact, StudentRecord
from .serializers import (
    AuditEventSerializer,
    EmergencyContactSerializer,
    StudentArchiveSerializer,
    StudentCreateSerializer,
    StudentRecordSerializer,
    StudentUpdateSerializer,
)
from .services import archive_student, create_contact, create_student, update_contact, update_student

WRITE_ROLES = {Membership.Role.INSTITUTION_ADMIN, Membership.Role.ADMIN_STAFF}
INSTITUTION_ROLES = WRITE_ROLES | {Membership.Role.READ_ONLY}


def get_scoped_object(queryset, **filters):
    try:
        return get_object_or_404(queryset, **filters)
    except Http404:
        raise exceptions.NotFound() from None


class StudentRecordViewSet(viewsets.GenericViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]
    serializer_class = StudentRecordSerializer

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.get_membership()

    def handle_exception(self, exc):
        return super().handle_exception(public_student_error(exc))

    def get_membership(self):
        if not hasattr(self, "_membership"):
            self._membership = Membership.objects.filter(
                user=self.request.user,
                organisation__code=self.request.headers.get("X-Organisation-Code"),
                organisation__organisation_type=Organisation.Type.INSTITUTION,
                organisation__is_active=True,
                active=True,
                role__in=INSTITUTION_ROLES,
            ).select_related("organisation").first()
        if self._membership is None:
            raise exceptions.PermissionDenied("An active institution membership is required.")
        return self._membership

    def require_writer(self):
        if self.get_membership().role not in WRITE_ROLES:
            raise exceptions.PermissionDenied("This role cannot change student records.")

    def get_queryset(self):
        queryset = StudentRecord.objects.filter(organisation=self.get_membership().organisation).prefetch_related(
            "emergency_contacts"
        )
        if self.action == "list" and self.request.query_params.get("include_archived") != "true":
            queryset = queryset.filter(archived_at__isnull=True)
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(student_number__icontains=query)
                | Q(legal_first_name__icontains=query)
                | Q(legal_middle_names__icontains=query)
                | Q(legal_last_name__icontains=query)
                | Q(email__icontains=query)
                | Q(phone__icontains=query)
            )
        student_status = self.request.query_params.get("status")
        if student_status:
            if student_status not in StudentRecord.Status.values:
                raise exceptions.ValidationError({"status": "Invalid student status."})
            queryset = queryset.filter(status=student_status)
        return queryset

    def list(self, request):
        return Response(StudentRecordSerializer(self.get_queryset(), many=True).data)

    def retrieve(self, request, pk=None):
        return Response(StudentRecordSerializer(get_scoped_object(self.get_queryset(), pk=pk)).data)

    def create(self, request):
        self.require_writer()
        serializer = StudentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contacts = serializer.validated_data.pop("emergency_contacts", [])
        student = create_student(request.user, self.get_membership().organisation, serializer.validated_data, contacts)
        return Response(StudentRecordSerializer(student).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        self.require_writer()
        student = get_scoped_object(self.get_queryset(), pk=pk)
        serializer = StudentUpdateSerializer(student, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        expected_version = serializer.validated_data.pop("version", None)
        if expected_version is None:
            raise exceptions.ValidationError({"version": "This field is required."})
        student = update_student(request.user, student, expected_version, serializer.validated_data)
        return Response(StudentRecordSerializer(student).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        self.require_writer()
        student = get_scoped_object(self.get_queryset(), pk=pk)
        serializer = StudentArchiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = archive_student(request.user, student, serializer.validated_data["version"])
        return Response(StudentRecordSerializer(student).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        student = get_scoped_object(self.get_queryset(), pk=pk)
        events = student.audit_events.filter(organisation_id=student.organisation_id).select_related("actor")
        return Response(AuditEventSerializer(events, many=True).data)

    @action(detail=True, methods=["get", "post"], url_path="emergency-contacts")
    def emergency_contacts(self, request, pk=None):
        if request.method == "POST":
            self.require_writer()
        student = get_scoped_object(self.get_queryset(), pk=pk)
        if request.method in {"GET", "HEAD"}:
            return Response(EmergencyContactSerializer(student.emergency_contacts.all(), many=True).data)
        serializer = EmergencyContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = create_contact(request.user, student, serializer.validated_data)
        return Response(EmergencyContactSerializer(contact).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"emergency-contacts/(?P<contact_id>[^/.]+)",
        url_name="emergency-contact-detail",
    )
    def emergency_contact_detail(self, request, pk=None, contact_id=None):
        self.require_writer()
        student = get_scoped_object(self.get_queryset(), pk=pk)
        contact = get_scoped_object(EmergencyContact.objects.filter(student_record=student), pk=contact_id)
        serializer = EmergencyContactSerializer(contact, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        contact = update_contact(request.user, student, contact, serializer.validated_data)
        return Response(EmergencyContactSerializer(contact).data)
