"""Boshqaruv bo'limi API (/api/manage/...) va e'lonlar (/api/announcements/).

Boshqaruv — faqat bosh admin (superuser yoki "admin" roli).
E'lon yozish: bosh admin (har qanday modul), Tashkiliy guruh (zakovat), tashkilotchi (kitobxonlik).
Barcha o'zgarishlar harakatlar jurnaliga yoziladi.
"""
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.importer import ImportFormatError, import_employees
from accounts.models import Branch, Employee, User, mask_phone

from .api import RuleError
from .models import Announcement, AuditLog, Module, Role, RoleAssignment, Season
from .services import has_role, log_action


def is_admin(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_superuser or has_role(user, Role.ADMIN)))


class AdminView(APIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not is_admin(request.user):
            raise PermissionDenied("Bu bo'lim faqat bosh admin uchun.")


def validated(ser_cls, data):
    s = ser_cls(data=data)
    s.is_valid(raise_exception=True)
    return s.validated_data


def user_payload(u: User) -> dict:
    emp = u.employee
    return {
        "id": u.pk, "name": str(u), "status": u.status, "is_superuser": u.is_superuser,
        "display_name": u.display_name, "email": u.email,
        "employee": None if emp is None else {"id": emp.pk, "full_name": emp.full_name, "branch": emp.branch.name,
                                              "is_active": emp.is_active},
        "identities": [i.provider for i in u.identities.all()],
        "date_joined": u.date_joined, "last_login": u.last_login,
    }


def employee_payload(e: Employee) -> dict:
    user = getattr(e, "user", None)
    return {
        "id": e.pk, "full_name": e.full_name, "branch": {"id": e.branch_id, "name": e.branch.name},
        "position": e.position, "phone": mask_phone(e.phone), "email": e.email,
        "telegram": e.telegram_username, "is_active": e.is_active,
        "account": None if user is None else {"id": user.pk, "status": user.status},
    }


# ================================================================== xodimlar

class EmployeesView(AdminView):
    """?q= &branch= &active=1|0 &account=yes|no"""

    def get(self, request):
        p = request.query_params
        qs = Employee.objects.select_related("branch", "user").order_by("full_name")
        if p.get("q"):
            qs = qs.filter(Q(full_name__icontains=p["q"]) | Q(email__icontains=p["q"]) | Q(position__icontains=p["q"]))
        if p.get("branch"):
            qs = qs.filter(branch_id=p["branch"])
        if p.get("active") in ("1", "0"):
            qs = qs.filter(is_active=p["active"] == "1")
        if p.get("account") == "yes":
            qs = qs.filter(user__isnull=False)
        elif p.get("account") == "no":
            qs = qs.filter(user__isnull=True)
        total = Employee.objects.count()
        return Response({
            "branches": [{"id": b.pk, "name": b.name} for b in Branch.objects.all()],
            "stats": {
                "total": total,
                "active": Employee.objects.filter(is_active=True).count(),
                "with_account": Employee.objects.filter(user__isnull=False).count(),
            },
            "items": [employee_payload(e) for e in qs[:500]],
        })


class EmployeeUpdateSer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False)
    position = serializers.CharField(max_length=150, required=False, allow_blank=True)
    branch_id = serializers.IntegerField(required=False)


class EmployeeDetailView(AdminView):
    def patch(self, request, pk):
        e = get_object_or_404(Employee, pk=pk)
        d = validated(EmployeeUpdateSer, request.data)
        before = {"is_active": e.is_active, "position": e.position, "branch": e.branch_id}
        if "branch_id" in d:
            e.branch = get_object_or_404(Branch, pk=d.pop("branch_id"))
        for k, v in d.items():
            setattr(e, k, v)
        e.save()
        log_action(request.user, "employee.updated", e, before=before,
                   after={"is_active": e.is_active, "position": e.position, "branch": e.branch_id})
        return Response(employee_payload(e))


class EmployeeImportView(AdminView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            raise RuleError("Excel fayl tanlanmagan.")
        if not f.name.lower().endswith(".xlsx"):
            raise RuleError("Faqat .xlsx formatidagi fayl qabul qilinadi.")
        dry = request.data.get("dry_run", "true") in ("true", "1", True)
        deactivate = request.data.get("deactivate_missing") in ("true", "1", True)
        try:
            report = import_employees(f, dry_run=dry, deactivate_missing=deactivate)
        except ImportFormatError as exc:
            raise RuleError(str(exc))
        except Exception:  # noqa: BLE001 — buzilgan fayl
            raise RuleError("Faylni o'qib bo'lmadi. U .xlsx formatida ekanini tekshiring.")
        if not dry and report.ok:
            log_action(request.user, "employees.imported", note=report.summary())
        return Response({
            "dry_run": dry, "saved": (not dry) and report.ok, "ok": report.ok, "summary": report.summary(),
            "created": report.created, "updated": report.updated, "unchanged": report.unchanged,
            "deactivated": report.deactivated,
            "errors": [{"row": r, "reason": m} for r, m in report.errors],
            "warnings": [{"row": r, "reason": m} for r, m in report.warnings],
        })


# ================================================================== akkauntlar

class UsersView(AdminView):
    """?status=pending|active|blocked &q="""

    def get(self, request):
        p = request.query_params
        qs = (User.objects.select_related("employee__branch").prefetch_related("identities")
              .order_by("-date_joined"))
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("q"):
            qs = qs.filter(Q(employee__full_name__icontains=p["q"]) | Q(display_name__icontains=p["q"])
                           | Q(email__icontains=p["q"]) | Q(username__icontains=p["q"]))
        counts = {s: User.objects.filter(status=s).count() for s, _ in User.Status.choices}
        return Response({"counts": counts, "items": [user_payload(u) for u in qs[:300]]})


class ApproveSer(serializers.Serializer):
    employee_id = serializers.IntegerField(required=False)


class UserActionView(AdminView):
    def post(self, request, pk, action):
        user = get_object_or_404(User, pk=pk)
        before = {"status": user.status, "employee": user.employee_id}
        if action == "approve":
            d = validated(ApproveSer, request.data)
            if d.get("employee_id"):
                emp = get_object_or_404(Employee, pk=d["employee_id"])
                other = User.objects.filter(employee=emp).exclude(pk=user.pk).first()
                if other:
                    raise RuleError(f"Bu xodim boshqa akkauntga bog'langan: {other}.")
                user.employee = emp
            if user.employee_id is None and not user.is_superuser:
                raise RuleError("Avval akkauntni xodimlar ro'yxatidagi xodimga bog'lang.")
            user.status = User.Status.ACTIVE
        elif action == "block":
            if user.pk == request.user.pk:
                raise RuleError("O'zingizni bloklay olmaysiz.")
            user.status = User.Status.BLOCKED
        elif action == "unblock":
            user.status = User.Status.ACTIVE if user.employee_id or user.is_superuser else User.Status.PENDING
        else:
            raise RuleError("Noma'lum amal.")
        try:
            with transaction.atomic():
                user.save()
        except IntegrityError:
            raise RuleError("Bu xodim boshqa akkauntga bog'langan.")
        log_action(request.user, f"user.{action}", user, before=before,
                   after={"status": user.status, "employee": user.employee_id})
        return Response(user_payload(user))


# ================================================================== rollar

class RoleSer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=Role.choices)
    module = serializers.ChoiceField(choices=Module.choices, default=Module.CORE)
    season_id = serializers.IntegerField(required=False, allow_null=True)


class RolesView(AdminView):
    def get(self, request):
        qs = RoleAssignment.objects.select_related("user__employee__branch", "season", "granted_by").order_by(
            "module", "role")
        return Response({
            "roles": [{"value": v, "label": l} for v, l in Role.choices],
            "modules": [{"value": v, "label": l} for v, l in Module.choices],
            "items": [{
                "id": r.pk, "user": {"id": r.user_id, "name": str(r.user),
                                     "branch": r.user.employee.branch.name if r.user.employee_id else None},
                "role": r.role, "role_label": r.get_role_display(), "module": r.module,
                "module_label": r.get_module_display(), "season": r.season.name if r.season_id else None,
                "granted_by": str(r.granted_by) if r.granted_by_id else None, "created_at": r.created_at,
            } for r in qs],
        })

    def post(self, request):
        d = validated(RoleSer, request.data)
        user = get_object_or_404(User, pk=d["user_id"])
        if user.status != User.Status.ACTIVE:
            raise RuleError("Rolni faqat faol akkauntga berish mumkin.")
        if d["role"] == Role.ADMIN and d["module"] != Module.CORE:
            raise RuleError("Bosh admin roli faqat 'Umumiy' modulda beriladi.")
        season = get_object_or_404(Season, pk=d["season_id"]) if d.get("season_id") else None
        # season bo'sh bo'lganda bazadagi noyoblik cheklovi ishlamaydi (NULL lar teng emas) — shu yerda tekshiramiz
        if RoleAssignment.objects.filter(user=user, role=d["role"], module=d["module"], season=season).exists():
            raise RuleError("Bu rol allaqachon berilgan.")
        try:
            with transaction.atomic():
                ra = RoleAssignment.objects.create(user=user, role=d["role"], module=d["module"], season=season,
                                                   granted_by=request.user)
        except IntegrityError:
            raise RuleError("Bu rol allaqachon berilgan.")
        log_action(request.user, "role.saved", ra, after={"user": user.pk, "role": ra.role, "module": ra.module,
                                                          "season": ra.season_id})
        return Response({"id": ra.pk}, status=status.HTTP_201_CREATED)


class RoleDeleteView(AdminView):
    def delete(self, request, pk):
        ra = get_object_or_404(RoleAssignment, pk=pk)
        if ra.role == Role.ADMIN and ra.user_id == request.user.pk:
            raise RuleError("O'zingizdan bosh admin rolini olib bo'lmaydi.")
        log_action(request.user, "role.deleted", ra, before={"user": ra.user_id, "role": ra.role,
                                                             "module": ra.module, "season": ra.season_id})
        ra.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserSearchView(AdminView):
    """Rol berish uchun faol akkaunt qidirish."""

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        qs = User.objects.filter(status=User.Status.ACTIVE).select_related("employee__branch")
        if q:
            qs = qs.filter(Q(employee__full_name__icontains=q) | Q(display_name__icontains=q) | Q(username__icontains=q))
        return Response([{"id": u.pk, "name": str(u), "branch": u.employee.branch.name if u.employee_id else None}
                         for u in qs.order_by("employee__full_name")[:20]])


# ================================================================== mavsumlar

class SeasonSer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class SeasonsView(AdminView):
    def get(self, request):
        return Response([{"id": s.pk, "name": s.name, "start_date": s.start_date, "end_date": s.end_date,
                          "is_active": s.is_active} for s in Season.objects.all()])

    def post(self, request):
        d = validated(SeasonSer, request.data)
        s = Season(**d)
        from django.core.exceptions import ValidationError
        try:
            s.full_clean()
        except ValidationError as exc:
            raise RuleError("; ".join(exc.messages))
        s.save()
        log_action(request.user, "season.created", s, after={"name": s.name})
        return Response({"id": s.pk}, status=status.HTTP_201_CREATED)


class SeasonActivateView(AdminView):
    @transaction.atomic
    def post(self, request, pk):
        s = get_object_or_404(Season, pk=pk)
        prev = Season.current()
        Season.objects.filter(is_active=True).update(is_active=False)
        s.is_active = True
        s.save(update_fields=["is_active"])
        log_action(request.user, "season.activated", s, before={"active": prev.pk if prev else None})
        return Response({"id": s.pk, "is_active": True})


# ================================================================== jurnal

class AuditView(AdminView):
    """?q= (amal yoki izoh) &action="""

    def get(self, request):
        p = request.query_params
        qs = AuditLog.objects.select_related("actor__employee").order_by("-created_at")
        if p.get("q"):
            qs = qs.filter(Q(action__icontains=p["q"]) | Q(note__icontains=p["q"]) | Q(object_type__icontains=p["q"]))
        if p.get("action"):
            qs = qs.filter(action__startswith=p["action"])
        return Response([{
            "id": a.pk, "created_at": a.created_at, "actor": str(a.actor) if a.actor_id else "Tizim",
            "action": a.action, "object_type": a.object_type, "object_id": a.object_id,
            "before": a.before, "after": a.after, "note": a.note,
        } for a in qs[:200]])


# ================================================================== e'lonlar

def can_announce(user, module) -> bool:
    if is_admin(user):
        return True
    if module == Module.ZAKOVAT:
        return has_role(user, Role.TG_MEMBER, Module.ZAKOVAT)
    if module == Module.KITOBXONLIK:
        return has_role(user, Role.ORGANIZER, Module.KITOBXONLIK)
    return False


def announcement_payload(a: Announcement, user) -> dict:
    return {
        "id": a.pk, "title": a.title, "body": a.body, "module": a.module, "pinned": a.pinned,
        "is_active": a.is_active, "expires_at": a.expires_at, "created_at": a.created_at,
        "author": str(a.author) if a.author_id else None, "can_edit": can_announce(user, a.module),
    }


class AnnouncementSer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    body = serializers.CharField(required=False, allow_blank=True)
    module = serializers.ChoiceField(choices=Module.choices, required=False)
    pinned = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class AnnouncementsView(APIView):
    """GET: ko'rinadigan e'lonlar (?module=, ?all=1 — muallif/admin uchun yashirinlari ham). POST: yangi."""

    def get(self, request):
        qs = Announcement.objects.select_related("author__employee")
        module = request.query_params.get("module")
        if module:
            qs = qs.filter(module__in=[module, Module.CORE])
        if not (request.query_params.get("all") in ("1", "true") and is_admin(request.user)):
            now = timezone.now()
            qs = qs.filter(is_active=True).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        return Response({
            "can_post": [m for m, _ in Module.choices if can_announce(request.user, m)],
            "items": [announcement_payload(a, request.user) for a in qs[:50]],
        })

    def post(self, request):
        d = validated(AnnouncementSer, request.data)
        module = d.get("module", Module.CORE)
        if not can_announce(request.user, module):
            raise PermissionDenied("Bu modulga e'lon yozish huquqingiz yo'q.")
        if not d.get("title", "").strip():
            raise RuleError("Sarlavha majburiy.")
        a = Announcement.objects.create(author=request.user, **{**d, "module": module})
        log_action(request.user, "announcement.created", a, after={"title": a.title, "module": a.module})
        return Response(announcement_payload(a, request.user), status=status.HTTP_201_CREATED)


class AnnouncementDetailView(APIView):
    def patch(self, request, pk):
        a = get_object_or_404(Announcement, pk=pk)
        d = validated(AnnouncementSer, request.data)
        if not can_announce(request.user, a.module) or ("module" in d and not can_announce(request.user, d["module"])):
            raise PermissionDenied()
        for k, v in d.items():
            setattr(a, k, v)
        a.save()
        log_action(request.user, "announcement.updated", a, after={k: str(v) for k, v in d.items()})
        return Response(announcement_payload(a, request.user))

    def delete(self, request, pk):
        a = get_object_or_404(Announcement, pk=pk)
        if not can_announce(request.user, a.module):
            raise PermissionDenied()
        log_action(request.user, "announcement.deleted", a, before={"title": a.title})
        a.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
