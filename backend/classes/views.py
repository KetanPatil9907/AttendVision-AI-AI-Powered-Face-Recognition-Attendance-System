from django.db.models import Count
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied

from .models import Classroom, Division, Subject
from .serializers import ClassroomSerializer, DivisionSerializer, SubjectSerializer


class OwnedModelViewSet(viewsets.ModelViewSet):
    """Base viewset scoping all records to the authenticated teacher."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


class ClassroomViewSet(OwnedModelViewSet):
    queryset = Classroom.objects.all()
    serializer_class = ClassroomSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


class DivisionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Division.objects.all()
    serializer_class = DivisionSerializer

    def get_queryset(self):
        qs = Division.objects.filter(classroom__teacher=self.request.user).prefetch_related("students")
        classroom = self.request.query_params.get("classroom")
        if classroom:
            qs = qs.filter(classroom_id=classroom)
        return qs

    def perform_create(self, serializer):
        classroom = serializer.validated_data["classroom"]
        self._check_ownership(classroom)
        serializer.save()

    def perform_update(self, serializer):
        classroom = serializer.validated_data.get("classroom") or self.get_object().classroom
        self._check_ownership(classroom)
        serializer.save()

    def _check_ownership(self, classroom):
        if classroom.teacher_id != self.request.user.pk:
            raise PermissionDenied("You do not own this classroom.")


class SubjectViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

    def get_queryset(self):
        qs = Subject.objects.filter(classroom__teacher=self.request.user)
        classroom = self.request.query_params.get("classroom")
        if classroom:
            qs = qs.filter(classroom_id=classroom)
        return qs

    def perform_create(self, serializer):
        classroom = serializer.validated_data["classroom"]
        self._check_ownership(classroom)
        serializer.save()

    def perform_update(self, serializer):
        classroom = serializer.validated_data.get("classroom") or self.get_object().classroom
        self._check_ownership(classroom)
        serializer.save()

    def _check_ownership(self, classroom):
        if classroom.teacher_id != self.request.user.pk:
            raise PermissionDenied("You do not own this classroom.")