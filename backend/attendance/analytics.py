"""Attendance history, student summaries and dashboard statistics."""
from datetime import date, timedelta

from django.conf import settings
from django.db.models import Avg, Count, F, Q
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.models import AttendanceRecord, AttendanceSession
from students.models import Student


def _shift_month(first_of_month, offset):
    """First day of the month `offset` months from `first_of_month` (may be negative)."""
    month_index = first_of_month.month - 1 + offset
    year = first_of_month.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


class AttendanceHistoryView(APIView):
    """Aggregated per-session attendance history with optional filters."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = (
            AttendanceSession.objects.filter(teacher=request.user)
            .select_related("classroom", "division", "subject")
            .order_by("-date", "-created_at")
        )
        params = request.query_params
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        classroom = params.get("classroom")
        division = params.get("division")
        subject = params.get("subject")
        status_filter = params.get("status")
        student_id = params.get("student")
        search = params.get("search")

        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if classroom:
            qs = qs.filter(classroom_id=classroom)
        if division:
            qs = qs.filter(division_id=division)
        if subject:
            qs = qs.filter(subject_id=subject)
        if status_filter == "finalized":
            qs = qs.filter(status=AttendanceSession.Status.FINALIZED)
        if student_id:
            qs = qs.filter(records__student_id=student_id).distinct()
        if search:
            qs = qs.filter(
                Q(classroom__name__icontains=search)
                | Q(subject__name__icontains=search)
                | Q(division__name__icontains=search)
            )

        rows = []
        for session in qs:
            stats = session.records.aggregate(
                total=Count("id"),
                present=Count("id", filter=Q(status=AttendanceRecord.Status.PRESENT)),
            )
            total = stats["total"] or 0
            present = stats["present"] or 0
            rows.append(
                {
                    "id": session.pk,
                    "date": session.date.isoformat(),
                    "classroom": session.classroom.name,
                    "classroom_id": session.classroom_id,
                    "division": session.division.name,
                    "division_id": session.division_id,
                    "subject": session.subject.name,
                    "subject_id": session.subject_id,
                    "lecture_number": session.lecture_number,
                    "status": session.status,
                    "total": total,
                    "present": present,
                    "absent": total - present,
                    "percentage": round(present / total * 100, 1) if total else 0.0,
                }
            )
        return Response({"sessions": rows})


class StudentAttendanceSummaryView(APIView):
    """Per-student attendance profile across finalized sessions."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, student_id):
        try:
            student = Student.objects.get(pk=student_id, teacher=request.user)
        except Student.DoesNotExist:
            return Response({"message": "Student not found."}, status=404)

        sessions = AttendanceSession.objects.filter(
            teacher=request.user,
            division=student.division,
            status=AttendanceSession.Status.FINALIZED,
        )
        records = AttendanceRecord.objects.filter(student=student, session__in=sessions)

        total = records.count()
        present = records.filter(status=AttendanceRecord.Status.PRESENT).count()
        absent = total - present

        # Monthly attendance for the last 6 months (real calendar months - a fixed
        # 30-day stride drifts and double-counts days across a year).
        monthly = []
        today = timezone.localdate()
        month_start = today.replace(day=1)
        for i in range(5, -1, -1):
            month = _shift_month(month_start, -i)
            month_records = records.filter(session__date__year=month.year, session__date__month=month.month)
            total_m = month_records.count()
            present_m = month_records.filter(status=AttendanceRecord.Status.PRESENT).count()
            monthly.append(
                {
                    "month": month.strftime("%Y-%m"),
                    "label": month.strftime("%b %Y"),
                    "total": total_m,
                    "present": present_m,
                    "percentage": round(present_m / total_m * 100, 1) if total_m else 0.0,
                }
            )

        # Subject-wise
        subject_wise = []
        for subject in student.division.classroom.subjects.all():
            subject_sessions = sessions.filter(subject=subject)
            if not subject_sessions.exists():
                continue
            subject_records = records.filter(session__subject=subject)
            total_s = subject_records.count()
            present_s = subject_records.filter(status=AttendanceRecord.Status.PRESENT).count()
            subject_wise.append(
                {
                    "subject_id": subject.pk,
                    "subject": subject.name,
                    "total": total_s,
                    "present": present_s,
                    "percentage": round(present_s / total_s * 100, 1) if total_s else 0.0,
                }
            )

        return Response(
            {
                "student": {
                    "id": student.pk,
                    "full_name": student.full_name,
                    "roll_number": student.roll_number,
                    "student_id": student.student_id,
                    "class": student.division.classroom.name,
                    "division": student.division.name,
                },
                "summary": {
                    "total_lectures": total,
                    "present": present,
                    "absent": absent,
                    "percentage": round(present / total * 100, 1) if total else 0.0,
                },
                "monthly": monthly,
                "subjects": subject_wise,
            }
        )


class AttendanceTrendView(APIView):
    """Daily present/absent trend for the last N days (default 30)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            days = int(request.query_params.get("days", 30))
        except (TypeError, ValueError):
            return Response({"message": "'days' must be an integer."}, status=400)
        days = max(1, min(days, 90))
        end = timezone.localdate()
        start = end - timedelta(days=days - 1)

        sessions = AttendanceSession.objects.filter(
            teacher=request.user,
            status=AttendanceSession.Status.FINALIZED,
            date__gte=start,
            date__lte=end,
        )
        daily = {}
        for session in sessions:
            key = session.date.isoformat()
            present = session.records.filter(status=AttendanceRecord.Status.PRESENT).count()
            total = session.records.count()
            entry = daily.setdefault(key, {"present": 0, "absent": 0, "total": 0, "sessions": 0})
            entry["present"] += present
            entry["absent"] += total - present
            entry["total"] += total
            entry["sessions"] += 1

        series = []
        day = start
        while day <= end:
            iso = day.isoformat()
            entry = daily.get(iso, {"present": 0, "absent": 0, "total": 0, "sessions": 0})
            series.append(
                {
                    "date": iso,
                    "label": day.strftime("%d %b"),
                    "present": entry["present"],
                    "absent": entry["absent"],
                    "total": entry["total"],
                    "percentage": round(entry["present"] / entry["total"] * 100, 1)
                    if entry["total"]
                    else 0.0,
                }
            )
            day += timedelta(days=1)
        return Response({"series": series})


class DashboardStatsView(APIView):
    """Aggregate statistics shown on the teacher dashboard."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.localdate()

        total_students = Student.objects.filter(teacher=user).count()
        total_classes = user.classrooms.count()
        total_subjects = sum(c.subjects.count() for c in user.classrooms.all())
        total_divisions = sum(c.divisions.count() for c in user.classrooms.all())

        # Today's finalized/in-progress sessions
        todays_sessions = AttendanceSession.objects.filter(teacher=user, date=today)
        today_present = 0
        today_absent = 0
        for session in todays_sessions:
            stats = session.records.aggregate(
                total=Count("id"),
                present=Count("id", filter=Q(status=AttendanceRecord.Status.PRESENT)),
            )
            today_present += stats["present"] or 0
            today_absent += (stats["total"] or 0) - (stats["present"] or 0)

        # Overall average attendance across finalized sessions
        finalized = AttendanceSession.objects.filter(
            teacher=user, status=AttendanceSession.Status.FINALIZED
        )
        overall_total = 0
        overall_present = 0
        for session in finalized:
            stats = session.records.aggregate(
                total=Count("id"),
                present=Count("id", filter=Q(status=AttendanceRecord.Status.PRESENT)),
            )
            overall_total += stats["total"] or 0
            overall_present += stats["present"] or 0
        average_attendance = (
            round(overall_present / overall_total * 100, 1) if overall_total else 0.0
        )

        # Class-wise average attendance
        class_wise = []
        for classroom in user.classrooms.all():
            c_sessions = finalized.filter(classroom=classroom)
            c_total = 0
            c_present = 0
            for session in c_sessions:
                stats = session.records.aggregate(
                    total=Count("id"),
                    present=Count("id", filter=Q(status=AttendanceRecord.Status.PRESENT)),
                )
                c_total += stats["total"] or 0
                c_present += stats["present"] or 0
            class_wise.append(
                {
                    "classroom": classroom.name,
                    "academic_year": classroom.academic_year,
                    "total": c_total,
                    "present": c_present,
                    "percentage": round(c_present / c_total * 100, 1) if c_total else 0.0,
                }
            )

        recent_sessions = AttendanceSession.objects.filter(teacher=user).order_by(
            "-created_at"
        )[:5]

        return Response(
            {
                "teacher": {
                    "name": user.full_name,
                    "title": user.get_title_display()
                    if hasattr(user, "get_title_display")
                    else user.title,
                },
                "counts": {
                    "students": total_students,
                    "classes": total_classes,
                    "divisions": total_divisions,
                    "subjects": total_subjects,
                },
                "today": {
                    "date": today.isoformat(),
                    "sessions": todays_sessions.count(),
                    "present": today_present,
                    "absent": today_absent,
                    "percentage": round(today_present / (today_present + today_absent) * 100, 1)
                    if (today_present + today_absent)
                    else 0.0,
                },
                "average_attendance": average_attendance,
                "class_wise": class_wise,
                "recent_sessions": [
                    {
                        "id": s.pk,
                        "classroom": s.classroom.name,
                        "division": s.division.name,
                        "subject": s.subject.name,
                        "date": s.date.isoformat(),
                        "status": s.status,
                    }
                    for s in recent_sessions
                ],
            }
        )