from django.urls import path
from rest_framework.routers import DefaultRouter

from .analytics import (
    AttendanceHistoryView,
    AttendanceTrendView,
    DashboardStatsView,
    StudentAttendanceSummaryView,
)
from .views import AttendanceSessionViewSet

router = DefaultRouter()
router.register("sessions", AttendanceSessionViewSet, basename="attendance-session")

urlpatterns = router.urls + [
    path("history", AttendanceHistoryView.as_view(), name="attendance-history"),
    path("trend", AttendanceTrendView.as_view(), name="attendance-trend"),
    path("dashboard/statistics", DashboardStatsView.as_view(), name="dashboard-statistics"),
    path("summary/<int:student_id>", StudentAttendanceSummaryView.as_view(), name="student-summary"),
]