"""Custom DRF exception handler giving consistent error responses."""
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Return {detail: [...], errors: {...}} without leaking raw stack traces."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    message = ""
    if isinstance(response.data, dict):
        detail = response.data.get("detail")
        if detail is not None:
            message = str(detail) if not isinstance(detail, (list, dict)) else str(detail)
        errors = {}
        for key, value in response.data.items():
            if key == "detail":
                continue
            errors[key] = value if isinstance(value, list) else [str(value)]
        response.data = {"message": message, "errors": errors}
    else:
        response.data = {"message": str(response.data), "errors": {}}
    return response