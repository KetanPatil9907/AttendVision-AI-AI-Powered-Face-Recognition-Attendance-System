from django.contrib import admin

from .models import FaceEmbedding, Student, StudentFace


class StudentFaceInline(admin.TabularInline):
    model = StudentFace
    extra = 0


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("full_name", "roll_number", "student_id", "division", "status", "teacher")
    list_filter = ("status", "gender", "division", "division__classroom")
    search_fields = ("full_name", "roll_number", "student_id", "email")
    inlines = [StudentFaceInline]


@admin.register(StudentFace)
class StudentFaceAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "embedding_generated", "created_at")
    list_filter = ("embedding_generated",)


@admin.register(FaceEmbedding)
class FaceEmbeddingAdmin(admin.ModelAdmin):
    list_display = ("student", "model_name", "photo_count", "updated_at")
    search_fields = ("student__full_name",)