import logging

from django.conf import settings
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from ai.attendance_engine import models_ready
from ai.config import model_missing_message

from .models import Student, StudentFace
from .serializers import StudentCreateUpdateSerializer, StudentListSerializer, StudentSerializer
from .services import FaceRegistrationError, process_photo, remove_face_registration

logger = logging.getLogger(__name__)


class StudentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Student.objects.all()
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return StudentCreateUpdateSerializer
        if self.action == "list":
            return StudentListSerializer
        return StudentSerializer

    def get_queryset(self):
        qs = (
            Student.objects.filter(teacher=self.request.user)
            .select_related("division", "division__classroom", "face_embedding")
            .prefetch_related("faces")
        )
        params = self.request.query_params

        division = params.get("division")
        classroom = params.get("classroom")
        status_filter = params.get("status")
        search = params.get("search")
        gender = params.get("gender")

        if division:
            qs = qs.filter(division_id=division)
        if classroom:
            qs = qs.filter(division__classroom_id=classroom)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if gender:
            qs = qs.filter(gender=gender)
        if search:
            qs = qs.filter(
                Q(full_name__icontains=search)
                | Q(roll_number__icontains=search)
                | Q(student_id__icontains=search)
            )

        order = params.get("ordering", "roll_number")
        allowed = {
            "roll_number": "roll_number",
            "-roll_number": "-roll_number",
            "full_name": "full_name",
            "-full_name": "-full_name",
            "created_at": "created_at",
            "-created_at": "-created_at",
        }
        qs = qs.order_by(allowed.get(order, "roll_number"))
        return qs

    @action(detail=True, methods=["post", "delete"], url_path="face-registration")
    def face_registration(self, request, pk=None):
        """POST: register one photo. DELETE: remove entire face registration."""
        student = self.get_object()

        if request.method == "DELETE":
            remove_face_registration(student)
            return Response({"message": "Face registration removed."})

        if not models_ready():
            return Response(
                {"message": model_missing_message()},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        image_file = request.FILES.get("image")
        if image_file is None:
            return Response(
                {"message": "No image provided. Attach the photo as an 'image' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if image_file.size > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
            return Response(
                {"message": f"Image too large (max {settings.MAX_IMAGE_SIZE_MB} MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = process_photo(student, image_file.read())
        except FaceRegistrationError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except Exception as exc:
            logger.exception("Face registration failed for student %s", student.pk)
            return Response(
                {"message": "Face processing failed. Please try a different photo."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": "Photo processed successfully.",
                "photo_id": result["photo_id"],
                "photo_count": result["photo_count"],
                "max_photos": settings.MAX_STUDENT_PHOTOS,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="face-status")
    def face_status(self, request, pk=None):
        student = self.get_object()
        faces = StudentFace.objects.filter(student=student)
        return Response(
            {
                "student_id": student.pk,
                "photo_count": faces.count(),
                "max_photos": settings.MAX_STUDENT_PHOTOS,
                "face_registered": student.face_registered,
                "photos": [
                    {"id": f.pk, "image": f.image.url if f.image else None}
                    for f in faces
                ],
            }
        )