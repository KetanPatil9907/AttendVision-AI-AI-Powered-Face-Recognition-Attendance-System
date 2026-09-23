from django.contrib import admin

from .models import Classroom, Division, Subject


class DivisionInline(admin.TabularInline):
    model = Division
    extra = 0


class SubjectInline(admin.TabularInline):
    model = Subject
    extra = 0


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("name", "academic_year", "code", "teacher", "created_at")
    list_filter = ("academic_year",)
    search_fields = ("name", "code")
    inlines = [DivisionInline, SubjectInline]


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ("name", "classroom", "created_at")
    list_filter = ("classroom",)
    search_fields = ("name",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "classroom", "created_at")
    list_filter = ("classroom",)
    search_fields = ("name", "code")