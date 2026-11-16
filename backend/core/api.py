from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class RuleError(Exception):
    """Biznes qoidasi buzilganda ko'tariladigan umumiy xato (modullar shundan meros oladi).
    API'da 400 {"detail": "..."} ga aylanadi."""


def exception_handler(exc, context):
    if isinstance(exc, RuleError):
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return drf_exception_handler(exc, context)
