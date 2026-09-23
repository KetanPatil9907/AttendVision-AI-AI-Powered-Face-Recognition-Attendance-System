from rest_framework import serializers

from .models import Classroom, Division, Subject


class ClassroomSerializer(serializers.ModelSerializer):
    teacher = serializers.PrimaryKeyRelatedField(read_only=True)
    division_count = serializers.SerializerMethodField()
    subject_count = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = [
            "id",
            "teacher",
            "name",
            "code",
            "academic_year",
            "description",
            "division_count",
            "subject_count",
            "student_count",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_division_count(self, obj):
        return obj.divisions.count()

    def get_subject_count(self, obj):
        return obj.subjects.count()

    def get_student_count(self, obj):
        return sum(d.student_count for d in obj.divisions.all())

    def validate(self, attrs):
        if self.instance:
            name = attrs.get("name", self.instance.name)
            year = attrs.get("academic_year", self.instance.academic_year)
        else:
            name = attrs.get("name")
            year = attrs.get("academic_year")
        qs = Classroom.objects.filter(
            teacher=self.context["request"].user, name__iexact=name, academic_year=year
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"name": "This class already exists for the selected academic year."}
            )
        return attrs


class DivisionSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="classroom.name", read_only=True)
    academic_year = serializers.CharField(source="classroom.academic_year", read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Division
        fields = [
            "id",
            "classroom",
            "class_name",
            "academic_year",
            "name",
            "student_count",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_student_count(self, obj):
        return obj.students.count()

    def validate(self, attrs):
        classroom = attrs.get("classroom") or (
            self.instance.classroom if self.instance else None
        )
        if classroom is None:
            raise serializers.ValidationError("Classroom is required.")
        if classroom.teacher_id != self.context["request"].user.pk:
            raise serializers.ValidationError("Invalid classroom.")
        name = attrs.get("name", self.instance.name if self.instance else "")
        qs = Division.objects.filter(classroom=classroom, name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"name": "This division already exists for the class."}
            )
        return attrs


class SubjectSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="classroom.name", read_only=True)

    class Meta:
        model = Subject
        fields = ["id", "classroom", "class_name", "name", "code", "created_at"]
        read_only_fields = ["created_at"]

    def validate(self, attrs):
        classroom = attrs.get("classroom") or (
            self.instance.classroom if self.instance else None
        )
        if classroom is None:
            raise serializers.ValidationError("Classroom is required.")
        if classroom.teacher_id != self.context["request"].user.pk:
            raise serializers.ValidationError("Invalid classroom.")
        name = attrs.get("name", self.instance.name if self.instance else "")
        qs = Subject.objects.filter(classroom=classroom, name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"name": "This subject already exists for the class."}
            )
        return attrs