from rest_framework import serializers

from classes.models import Classroom, Division

from .models import FaceEmbedding, Student, StudentFace


class StudentFaceSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True)

    class Meta:
        model = StudentFace
        fields = ["id", "image", "embedding_generated", "created_at"]


class StudentListSerializer(serializers.ModelSerializer):
    division_name = serializers.CharField(source="division.name", read_only=True)
    class_name = serializers.CharField(source="division.classroom.name", read_only=True)
    face_registered = serializers.SerializerMethodField()
    photo_count = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id",
            "full_name",
            "roll_number",
            "student_id",
            "email",
            "mobile",
            "gender",
            "date_of_birth",
            "academic_year",
            "status",
            "division",
            "division_name",
            "class_name",
            "face_registered",
            "photo_count",
            "created_at",
        ]

    def get_face_registered(self, obj):
        return hasattr(obj, "face_embedding")

    def get_photo_count(self, obj):
        return obj.faces.count()


class StudentSerializer(StudentListSerializer):
    faces = StudentFaceSerializer(many=True, read_only=True)
    embedding_dim = serializers.SerializerMethodField()
    has_embedding = serializers.SerializerMethodField()

    class Meta(StudentListSerializer.Meta):
        fields = StudentListSerializer.Meta.fields + ["faces", "embedding_dim", "has_embedding"]

    def get_embedding_dim(self, obj):
        emb = getattr(obj, "face_embedding", None)
        return len(emb.embedding) if emb else 0

    def get_has_embedding(self, obj):
        return hasattr(obj, "face_embedding")


class StudentCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            "id",
            "full_name",
            "roll_number",
            "student_id",
            "email",
            "mobile",
            "gender",
            "date_of_birth",
            "academic_year",
            "status",
            "division",
        ]
        read_only_fields = ["id"]

    def validate_division(self, value):
        if value.classroom.teacher_id != self.context["request"].user.pk:
            raise serializers.ValidationError("Invalid division selected.")
        return value

    def validate(self, attrs):
        teacher = self.context["request"].user
        division = attrs.get("division") or getattr(self.instance, "division", None)
        if division is None:
            raise serializers.ValidationError({"division": "Division is required."})

        student_id = (attrs.get("student_id") or getattr(self.instance, "student_id", "")).strip()
        roll = (attrs.get("roll_number") or getattr(self.instance, "roll_number", "")).strip()

        sid_qs = Student.objects.filter(teacher=teacher, student_id__iexact=student_id)
        if self.instance:
            sid_qs = sid_qs.exclude(pk=self.instance.pk)
        if sid_qs.exists():
            raise serializers.ValidationError(
                {"student_id": "A student with this ID / PRN already exists."}
            )

        roll_qs = Student.objects.filter(teacher=teacher, division=division, roll_number__iexact=roll)
        if self.instance:
            roll_qs = roll_qs.exclude(pk=self.instance.pk)
        if roll_qs.exists():
            raise serializers.ValidationError(
                {"roll_number": "This roll number already exists in the division."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["teacher"] = self.context["request"].user
        return super().create(validated_data)


class FaceEmbeddingSerializer(serializers.ModelSerializer):
    """Exposes only metadata - never the embedding vector itself."""

    class Meta:
        model = FaceEmbedding
        fields = ["model_name", "photo_count", "updated_at"]