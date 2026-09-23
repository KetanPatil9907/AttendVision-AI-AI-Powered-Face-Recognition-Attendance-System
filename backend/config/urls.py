from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from attendance.analytics import DashboardStatsView


def home(request):
    return JsonResponse({
        "status": "online",
        "message": "Smart Attendance System API is running",
        "version": "1.0.0",
    })


api_patterns = [
    path("auth/", include("accounts.urls")),
    path("classes/", include("classes.urls")),
    path("students/", include("students.urls")),
    path("attendance/", include("attendance.urls")),
    path("reports/", include("reports.urls")),
    path(
        "dashboard/statistics",
        DashboardStatsView.as_view(),
        name="dashboard-statistics",
    ),
]


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("api/", include(api_patterns)),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT,
    )