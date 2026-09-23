"""Report generation for the Smart Attendance System.

Supported formats: PDF (ReportLab), Excel (openpyxl), CSV (stdlib).
"""
import csv
import html
import io
import logging

from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from attendance.models import AttendanceRecord, AttendanceSession

logger = logging.getLogger(__name__)

PDF_STYLES = getSampleStyleSheet()
PDF_STYLES.add(
    ParagraphStyle(
        name="ReportHeader",
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=16,
        spaceAfter=4,
    )
)
PDF_STYLES.add(
    ParagraphStyle(
        name="SubHeader",
        alignment=TA_CENTER,
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.grey,
    )
)


def _query_sessions(teacher, params):
    qs = (
        AttendanceSession.objects.filter(teacher=teacher)
        .select_related("classroom", "division", "subject")
        .order_by("-date")
    )
    if params.get("date_from"):
        qs = qs.filter(date__gte=params["date_from"])
    if params.get("date_to"):
        qs = qs.filter(date__lte=params["date_to"])
    if params.get("classroom"):
        qs = qs.filter(classroom_id=params["classroom"])
    if params.get("division"):
        qs = qs.filter(division_id=params["division"])
    if params.get("subject"):
        qs = qs.filter(subject_id=params["subject"])
    return qs


def _session_summary(session):
    stats = list(
        session.records.values("status")
        .annotate(n=Count("id"))
    )
    present = next((s["n"] for s in stats if s["status"] == "present"), 0)
    total = session.records.count()
    return present, total - present, total


def _rows_for_sessions(sessions, per_session=True):
    """Build tabular data for reports.

    per_session=True  -> one row per finalized session.
    per_session=False -> student-wise rows, limited to a filtered scope.
    """
    rows = []
    for session in sessions:
        present, absent, total = _session_summary(session)
        percentage = round(present / total * 100, 1) if total else 0.0
        rows.append(
            {
                "date": session.date.isoformat(),
                "class": session.classroom.name,
                "division": session.division.name,
                "subject": session.subject.name,
                "lecture": session.lecture_number or "-",
                "total": total,
                "present": present,
                "absent": absent,
                "percentage": percentage,
            }
        )
    return rows


def _student_rows(sessions):
    records = (
        AttendanceRecord.objects.filter(session__in=sessions)
        .select_related("student")
        .order_by("student__roll_number")
    )
    summary = {}
    for rec in records:
        student_key = rec.student.pk
        entry = summary.setdefault(
            student_key,
            {
                "name": rec.student.full_name,
                "roll": rec.student.roll_number,
                "student_id": rec.student.student_id,
                "total": 0,
                "present": 0,
            },
        )
        entry["total"] += 1
        if rec.status == AttendanceRecord.Status.PRESENT:
            entry["present"] += 1
    rows = []
    for entry in summary.values():
        rows.append(
            {
                "name": entry["name"],
                "roll": entry["roll"],
                "student_id": entry["student_id"],
                "total": entry["total"],
                "present": entry["present"],
                "absent": entry["total"] - entry["present"],
                "percentage": round(entry["present"] / entry["total"] * 100, 1)
                if entry["total"]
                else 0.0,
            }
        )
    return rows


def build_report(teacher, params):
    """Main dispatcher. types: daily|weekly|monthly|class|subject|student|all.

    Returns (filename, content_bytes, mimetype).
    """
    report_type = params.get("type", "daily")
    fmt = params.get("format", "pdf").lower()
    if fmt not in ("pdf", "xlsx", "csv"):
        raise ValueError("Unsupported format")

    sessions = _query_sessions(teacher, params).filter(status=AttendanceSession.Status.FINALIZED)

    if report_type == "daily":
        # Without an explicit period a daily report means "today"; with one the
        # caller already narrowed the query down to the requested date range.
        if not params.get("date_from") and not params.get("date_to"):
            sessions = sessions.filter(date=timezone.localdate())
        title = "Daily Attendance Report"
    elif report_type == "weekly":
        end = timezone.localdate()
        start = end - timezone.timedelta(days=6)
        sessions = sessions.filter(date__gte=start, date__lte=end)
        title = "Weekly Attendance Report"
    elif report_type == "monthly":
        end = timezone.localdate()
        start = end.replace(day=1)
        sessions = sessions.filter(date__gte=start, date__lte=end)
        title = "Monthly Attendance Report"
    elif report_type == "class":
        title = "Class Attendance Report"
        return _class_report(teacher, sessions, params, fmt)
    elif report_type == "subject":
        title = "Subject Attendance Report"
    elif report_type == "student":
        title = "Student Attendance Report"
        return _student_report(teacher, sessions, params, fmt)
    elif report_type == "all":
        title = "Complete Attendance Report"
    else:
        title = "Attendance Report"

    rows = _rows_for_sessions(sessions)
    headers = ["Date", "Class", "Division", "Subject", "Lecture", "Total", "Present", "Absent", "Percentage"]
    data_rows = [
        [r["date"], r["class"], r["division"], r["subject"], r["lecture"], r["total"], r["present"], r["absent"], f"{r['percentage']}%"]
        for r in rows
    ]
    meta = [
        ("Report Type", title),
        ("Generated On", timezone.localdate().isoformat()),
        ("Period", f"{params.get('date_from', '-')} to {params.get('date_to', '-')}"),
    ]
    return _render(rows, headers, data_rows, meta, fmt, filename_slug=report_type)


def _class_report(teacher, sessions, params, fmt):
    classroom_id = params.get("classroom")
    divisions = {}
    for session in sessions:
        if classroom_id and session.classroom_id != int(classroom_id):
            continue
        key = session.division_id
        entry = divisions.setdefault(key, {"name": f"{session.classroom.name} - {session.division.name}", "total": 0, "present": 0, "sessions": 0})
        present, absent, total = _session_summary(session)
        entry["total"] += total
        entry["present"] += present
        entry["sessions"] += 1

    headers = ["Class / Division", "Sessions", "Total Marks", "Present", "Absent", "Percentage"]
    data_rows = [
        [
            d["name"],
            d["sessions"],
            d["total"],
            d["present"],
            d["total"] - d["present"],
            f"{round(d['present'] / d['total'] * 100, 1) if d['total'] else 0}%",
        ]
        for d in divisions.values()
    ]
    meta = [("Report Type", "Class Attendance Report"), ("Generated On", str(timezone.localdate()))]
    return _render(divisions, headers, data_rows, meta, fmt, filename_slug="class")


def _student_report(teacher, sessions, params, fmt):
    rows = _student_rows(sessions)
    headers = ["Roll No", "Student ID", "Name", "Total", "Present", "Absent", "Percentage"]
    data_rows = [
        [r["roll"], r["student_id"], r["name"], r["total"], r["present"], r["absent"], f"{r['percentage']}%"]
        for r in rows
    ]
    meta = [("Report Type", "Student Attendance Report"), ("Generated On", str(timezone.localdate()))]
    return _render(rows, headers, data_rows, meta, fmt, filename_slug="student")


def _safe_slug(value):
    """Reduce a caller-supplied report type to a filename-safe slug."""
    slug = "".join(ch.lower() for ch in str(value or "") if ch.isalnum() or ch in "-_")
    return slug or "report"


def _render(rows, headers, data_rows, meta, fmt, filename_slug):
    slug = _safe_slug(filename_slug)
    if fmt == "csv":
        return _render_csv(headers, data_rows, slug)
    if fmt == "xlsx":
        return _render_xlsx(meta, headers, data_rows, slug)
    return _render_pdf(meta, headers, data_rows, slug)


def _render_csv(headers, data_rows, slug):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(data_rows)
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{slug}_report.csv"'
    return response


def _render_xlsx(meta, headers, data_rows, slug):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance Report"
    for label, value in meta:
        ws.append([label, value])
    ws.append([])
    ws.append(headers)
    for row in data_rows:
        ws.append(row)
    for cell in ws[meta.__len__() + 2]:
        cell.font = Font(bold=True)
    buffer = io.BytesIO()
    wb.save(buffer)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{slug}_report.xlsx"'
    return response


def _render_pdf(meta, headers, data_rows, slug):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm
    )
    story = [Paragraph("Smart Attendance System", PDF_STYLES["ReportHeader"]), Paragraph("Attendance Report", PDF_STYLES["SubHeader"]), Spacer(1, 6 * mm)]

    meta_lines = [
        Paragraph(f"<b>{label}:</b> {html.escape(str(value))}", PDF_STYLES["BodyText"])
        for label, value in meta
        if value
    ]
    story.extend(meta_lines)
    story.append(Spacer(1, 4 * mm))

    table = Table([headers] + [[str(c) for c in row] for row in data_rows], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.10, 0.36, 0.72)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.93, 0.95, 0.98)]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{slug}_report.pdf"'
    return response