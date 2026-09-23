"""Report export endpoints."""
import logging

from rest_framework import permissions, status
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import build_report

logger = logging.getLogger(__name__)


class _FormatFreeRequest:
    """Delegates to request but exposes query_params without the ``format``
    override so DRF's renderer negotiation never sees ``?format=pdf`` etc."""

    def __init__(self, request):
        self._request = request

    def __getattr__(self, item):
        return getattr(self._request, item)

    @property
    def query_params(self):
        params = self._request.query_params.copy()
        params.pop("format", None)
        return params


class ExportContentNegotiation(DefaultContentNegotiation):
    """The export endpoint interprets ``?format=`` itself, so disable DRF's
    URL format override (which would otherwise 404 for ``pdf``/``xlsx``/``csv``)."""

    def select_renderer(self, request, renderers, format_suffix=None):
        return super().select_renderer(_FormatFreeRequest(request), renderers, format_suffix)


class ReportExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    content_negotiation_class = ExportContentNegotiation

    def get(self, request):
        params = request.query_params
        fmt = (params.get("format") or "pdf").lower()
        if fmt not in ("pdf", "xlsx", "csv"):
            return Response({"message": "Unsupported format."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return build_report(request.user, params)
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Report export failed")
            return Response(
                {"message": "Report generation failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )