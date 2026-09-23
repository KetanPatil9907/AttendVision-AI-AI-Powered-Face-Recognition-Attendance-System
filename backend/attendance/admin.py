from django.contrib import admin

from .models import AttendanceRecord, AttendanceSession, RecognitionLog


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "classroom", "division", "subject", "date", "lecture_number", "status")
    list_filter = ("status", "date", "classroom", "division", "subject")
    inlines = [AttendanceRecordInline]


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "session", "status", "confidence", "marked_by_ai")
    list_filter = ("status", "marked_by_ai", "session__date")


@admin.register(RecognitionLog)
class RecognitionLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "result", "student", "confidence", "session")
    list_filter = ("result", "timestamp")