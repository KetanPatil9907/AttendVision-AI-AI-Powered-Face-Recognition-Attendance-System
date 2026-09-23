"""Attendance serializers."""
from rest_framework import serializers

from .models import AttendanceRecord, AttendanceSession, RecognitionLog


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    roll_number = serializers.CharField(source="student.roll_number", read_only=True)
    student_id = serializers.CharField(source="student.student_id", read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRecord
        fields = [
            "id",
            "student",
            "student_name",
            "roll_number",
            "student_id",
            "status",
            "confidence",
            "marked_by_ai",
            "manually_updated",
            "recognized_at",
            "photo_url",
        ]
        read_only_fields = ["confidence", "marked_by_ai", "recognized_at"]

    def get_photo_url(self, obj):
        face = obj.student.faces.first()
        if face:
            return face.image.url if hasattr(face, "image") else None
        return None


class RecognitionLogSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    roll_number = serializers.CharField(source="student.roll_number", read_only=True)

    class Meta:
        model = RecognitionLog
        fields = ["id", "timestamp", "student", "student_name", "roll_number", "confidence", "result", "message"]


class AttendanceSessionSerializer(serializers.ModelSerializer):
    classroom_name = serializers.CharField(source="classroom.name", read_only=True)
    division_name = serializers.CharField(source="division.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    present_count = serializers.SerializerMethodField()
    absent_count = serializers.SerializerMethodField()
    total_students = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceSession
        fields = [
            "id",
            "classroom",
            "classroom_name",
            "division",
            "division_name",
            "subject",
            "subject_name",
            "date",
            "lecture_number",
            "status",
            "created_at",
            "started_at",
            "finalized_at",
            "present_count",
            "absent_count",
            "total_students",
            "percentage",
        ]
        read_only_fields = ["status", "started_at", "finalized_at"]

    def get_records(self, obj):
        return obj.records.all()

    def get_present_count(self, obj):
        return obj.records.filter(status=AttendanceRecord.Status.PRESENT).count()

    def get_absent_count(self, obj):
        return obj.records.filter(status=AttendanceRecord.Status.ABSENT).count()

    def get_total_students(self, obj):
        return obj.records.count()

    def get_percentage(self, obj):
        total = obj.records.count()
        if total == 0:
            return 0.0
        present = obj.records.filter(status=AttendanceRecord.Status.PRESENT).count()
        return round(present / total * 100, 1)


class AttendanceSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSession
        fields = ["id", "classroom", "division", "subject", "date", "lecture_number"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        teacher = self.context["request"].user
        classroom = attrs.get("classroom")
        division = attrs.get("division")
        subject = attrs.get("subject")
        if classroom and classroom.teacher_id != teacher.pk:
            raise serializers.ValidationError({"classroom": "Invalid classroom."})
        if division and (division.classroom_id != (classroom.pk if classroom else None)):
            raise serializers.ValidationError(
                {"division": "Division does not belong to the selected class."}
            )
        if subject and (subject.classroom_id != (classroom.pk if classroom else None)):
            raise serializers.ValidationError(
                {"subject": "Subject does not belong to the selected class."}
            )
        if division and division.classroom.teacher_id != teacher.pk:
            raise serializers.ValidationError({"division": "Invalid division."})
        if subject and subject.classroom.teacher_id != teacher.pk:
            raise serializers.ValidationError({"subject": "Invalid subject."})
        return attrs


class ManualUpdateSerializer(serializers.Serializer):
    updates = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )

    def validate_updates(self, value):
        cleaned = []
        for item in value:
            record_id = item.get("id")
            status_value = item.get("status")
            if record_id is None or not isinstance(record_id, int):
                raise serializers.ValidationError("Each update needs a numeric 'id'.")
            if status_value not in ("present", "absent"):
                raise serializers.ValidationError("Status must be 'present' or 'absent'.")
            cleaned.append({"id": record_id, "status": status_value})
        return cleaned