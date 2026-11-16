from django.db.models import Sum
from rest_framework.permissions import BasePermission

from .models import AuditLog, Module, PointsEntry, Role, RoleAssignment


def add_points(*, season, module, subject_type, subject_id, amount, reason_type, reason_id="",
               note="", actor=None):
    if amount == 0:
        return None
    return PointsEntry.objects.create(
        season=season, module=module, subject_type=subject_type, subject_id=subject_id,
        amount=amount, reason_type=reason_type, reason_id=str(reason_id), note=note[:300],
        created_by=actor if (actor is not None and actor.is_authenticated) else None,
    )


def points_total(*, season, module, subject_type, subject_id, reason_type=None, reason_id=None) -> int:
    qs = PointsEntry.objects.filter(season=season, module=module, subject_type=subject_type,
                                    subject_id=subject_id)
    if reason_type is not None:
        qs = qs.filter(reason_type=reason_type)
    if reason_id is not None:
        qs = qs.filter(reason_id=str(reason_id))
    return qs.aggregate(s=Sum("amount"))["s"] or 0


def points_by_subject(*, season, module, subject_type) -> dict:
    rows = (PointsEntry.objects.filter(season=season, module=module, subject_type=subject_type)
            .values("subject_id").annotate(total=Sum("amount")))
    return {r["subject_id"]: r["total"] for r in rows}


def log_action(actor, action, obj=None, before=None, after=None, note=""):
    """Jurnalga yozuv qo'shadi. actor None bo'lishi mumkin (tizim amali)."""
    return AuditLog.objects.create(
        actor=actor if (actor is not None and actor.is_authenticated) else None,
        action=action,
        object_type=obj._meta.label if obj is not None else "",
        object_id=str(obj.pk) if obj is not None else "",
        before=before,
        after=after,
        note=note,
    )


def has_role(user, role, module=Module.CORE, season=None):
    """Foydalanuvchida berilgan rol bormi.

    - superuser va bosh admin hamma rolga ega deb hisoblanadi;
    - season berilsa: shu mavsumga yoki barcha mavsumlarga berilgan rol hisobga olinadi.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    qs = RoleAssignment.objects.filter(user=user)
    if qs.filter(role=Role.ADMIN).exists():
        return True
    qs = qs.filter(role=role, module=module)
    if season is not None:
        qs = qs.filter(season__isnull=True) | qs.filter(season=season)
    return qs.exists()


def require_role(role, module=Module.CORE):
    """DRF uchun ruxsat klassi: `permission_classes = [require_role(Role.SCORER, Module.ZAKOVAT)]`."""

    class _HasRole(BasePermission):
        message = "Bu amal uchun ruxsatingiz yo'q."

        def has_permission(self, request, view):
            return has_role(request.user, role, module)

    _HasRole.__name__ = f"HasRole_{role}_{module}"
    return _HasRole
