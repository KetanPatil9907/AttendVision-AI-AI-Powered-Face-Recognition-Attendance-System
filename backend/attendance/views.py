"""Attendance API views."""
import logging

from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from ai.attendance_engine import models_ready
from ai.config import model_missing_message

from .models import AttendanceRecord, AttendanceSession, RecognitionLog
from .serializers import (
    AttendanceRecordSerializer,
    AttendanceSessionCreateSerializer,
    AttendanceSessionSerializer,
    ManualUpdateSerializer,
    RecognitionLogSerializer,
)
from .services import ensure_present_records, finalize_session, process_recognition

logger = logging.getLogger(__name__)


class AttendanceSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = AttendanceSession.objects.all()
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return AttendanceSessionCreateSerializer
        return AttendanceSessionSerializer

    def get_queryset(self):
        qs = AttendanceSession.objects.filter(teacher=self.request.user).select_related(
            "classroom", "division", "subject"
        )
        params = self.request.query_params
        if params.get("classroom"):
            qs = qs.filter(classroom_id=params["classroom"])
        if params.get("division"):
            qs = qs.filter(division_id=params["division"])
        if params.get("subject"):
            qs = qs.filter(subject_id=params["subject"])
        if params.get("date"):
            qs = qs.filter(date=params["date"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        return qs

    def perform_create(self, serializer):
        session = serializer.save(teacher=self.request.user)
        ensure_present_records(session)
        return session

    @action(detail=True, methods=["get"])
    def records(self, request, pk=None):
        session = self.get_object()
        # Materialise the roster before serialising, so students enrolled
        # after the session was created still appear in the UI.
        if session.status == AttendanceSession.Status.IN_PROGRESS:
            ensure_present_records(session)
        records = (
            AttendanceRecord.objects.filter(session=session)
            .select_related("student")
            .order_by("student__roll_number")
        )
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search")
        if status_filter:
            records = records.filter(status=status_filter)
        if search:
            records = records.filter(student__full_name__icontains=search)
        data = AttendanceRecordSerializer(records, many=True).data
        return Response(
            {
                "session": AttendanceSessionSerializer(session).data,
                "records": data,
            }
        )

    @action(detail=True, methods=["post"])
    def recognize(self, request, pk=None):
        """Run AI recognition on the uploaded image / webcam frame."""
        session = self.get_object()
        if not models_ready():
            return Response(
                {"message": model_missing_message()},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        image_file = request.FILES.get("image")
        if image_file is None:
            return Response(
                {"message": "No image provided. Attach the frame as an 'image' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if image_file.size > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
            return Response(
                {"message": f"Image too large (max {settings.MAX_IMAGE_SIZE_MB} MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = process_recognition(session, image_file.read())
        except Exception as exc:
            logger.exception("Recognition failed for session %s", session.pk)
            return Response(
                {"message": "Recognition failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        if "error" in result:
            code = result.get("code")
            return Response(
                {"message": result["error"], "code": code},
                status=self._error_status(code),
            )
        return Response(result)

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        session = self.get_object()
        if session.status == AttendanceSession.Status.FINALIZED:
            return Response(
                {"message": "This session was already finalized."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        finalized_session = finalize_session(session)
        return Response(
    {
        "message": "Attendance finalized successfully.",
        "session": AttendanceSessionSerializer(finalized_session).data,
    }
)

    @action(detail=True, methods=["post"], url_path="update-records")
    def update_records(self, request, pk=None):
        """Manual correction of attendance records before finalization."""
        session = self.get_object()
        if session.status == AttendanceSession.Status.FINALIZED:
            return Response(
                {"message": "Cannot edit a finalized session."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ManualUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_statuses = {AttendanceRecord.Status.PRESENT, AttendanceRecord.Status.ABSENT}
        updated = 0
        for item in serializer.validated_data["updates"]:
            if item["status"] not in valid_statuses:
                continue
            rows = AttendanceRecord.objects.filter(session=session, pk=item["id"]).update(
                status=item["status"],
                manually_updated=True,
            )
            updated += rows
        return Response(
            {"message": f"Updated {updated} record(s).", "updated": updated}
        )

    @action(detail=True, methods=["get"], url_path="recognition-logs")
    def recognition_logs(self, request, pk=None):
        session = self.get_object()
        logs = RecognitionLog.objects.filter(session=session).select_related("student")
        page = self.paginate_queryset(logs)
        # Note: an empty page is falsy - never fall back to the full queryset.
        data = RecognitionLogSerializer(page if page is not None else logs, many=True).data
        if page is not None:
            return self.get_paginated_response(data)
        return Response({"logs": data})

    def _error_status(self, code):
        mapping = {
            "session_finalized": status.HTTP_400_BAD_REQUEST,
            "ai_error": status.HTTP_422_UNPROCESSABLE_ENTITY,
        }
        return mapping.get(code, status.HTTP_400_BAD_REQUEST)