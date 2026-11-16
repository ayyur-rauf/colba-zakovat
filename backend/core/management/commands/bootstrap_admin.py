"""Serverda birinchi ishga tushirish: bosh admin va joriy mavsum.

Har deploy oldidan avtomatik ishlaydi (railway.json → preDeployCommand) va takror ishga tushsa ham
hech narsani buzmaydi: mavjud bo'lsa — o'tkazib yuboradi.

O'zgaruvchilar:
    ADMIN_EMAIL     — bosh admin emaili (saytga shu email bilan kod orqali kiriladi). Bo'lmasa — hech narsa qilinmaydi.
    ADMIN_NAME      — F.I.Sh. (standart: "Bosh admin")
    ADMIN_BRANCH    — filial nomi (standart: "Bosh ofis")
    ADMIN_PASSWORD  — ixtiyoriy: /admin/ (Django admin panel) uchun parol; login = "admin"
    DEMO_DATA=1     — (faqat TEST_MODE=1 bilan) demo ma'lumotlar bir marta yuklanadi
"""
import os
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Branch, Employee, User
from core.models import Role, RoleAssignment, Season


class Command(BaseCommand):
    help = "Bosh admin va joriy mavsumni yaratadi (takror ishga tushirish xavfsiz)."

    def handle(self, *args, **opts):
        self._demo()
        self._admin()

    def _demo(self):
        from django.conf import settings
        from django.core.management import call_command

        from zakovat.management.commands.seed_demo import DEMO_SEASON
        if os.getenv("DEMO_DATA") != "1":
            return
        if not getattr(settings, "TEST_MODE", False):
            self.stdout.write("DEMO_DATA faqat TEST_MODE=1 bilan ishlaydi — o'tkazib yuborildi.")
            return
        if Season.objects.filter(name=DEMO_SEASON).exists():
            self.stdout.write("Demo ma'lumotlar allaqachon bor.")
            return
        call_command("seed_demo", stdout=self.stdout)

    @transaction.atomic
    def _admin(self):
        self._season()
        email = os.getenv("ADMIN_EMAIL", "").strip().lower()
        if not email:
            self.stdout.write("ADMIN_EMAIL berilmagan — bosh admin yaratilmadi.")
            return
        branch, _ = Branch.objects.get_or_create(name=os.getenv("ADMIN_BRANCH", "Bosh ofis").strip() or "Bosh ofis")
        emp = Employee.objects.filter(email=email).first()
        if emp is None:
            emp = Employee.objects.create(full_name=os.getenv("ADMIN_NAME", "Bosh admin").strip() or "Bosh admin",
                                          branch=branch, position="Bosh admin", email=email)
            self.stdout.write(f"Xodim yaratildi: {emp.full_name}")
        user = getattr(emp, "user", None)
        if user is None:
            user = User(username=f"admin_{emp.pk}", employee=emp, display_name=emp.full_name,
                        email=email, status=User.Status.ACTIVE)
            user.set_unusable_password()
            user.save()
            self.stdout.write(f"Akkaunt yaratildi: {email}")
        elif user.status != User.Status.ACTIVE:
            user.status = User.Status.ACTIVE
            user.save(update_fields=["status"])
        RoleAssignment.objects.get_or_create(user=user, role=Role.ADMIN, module="core", season=None)

        password = os.getenv("ADMIN_PASSWORD", "")
        if password:
            su, created = User.objects.get_or_create(username="admin", defaults={"status": User.Status.ACTIVE})
            su.is_staff = su.is_superuser = True
            su.status = User.Status.ACTIVE
            su.set_password(password)
            su.save()
            self.stdout.write("Django admin panel uchun 'admin' foydalanuvchisi " + ("yaratildi" if created else "yangilandi"))
        self.stdout.write(self.style.SUCCESS(f"Bosh admin tayyor: {email}"))

    def _season(self):
        if Season.objects.filter(is_active=True).exists():
            return
        today = timezone.localdate()
        start_year = today.year if today.month >= 9 else today.year - 1
        name = f"{start_year}–{start_year + 1}"
        season, created = Season.objects.get_or_create(
            name=name, defaults={"start_date": date(start_year, 9, 1), "end_date": date(start_year + 1, 8, 31)})
        season.is_active = True
        season.save(update_fields=["is_active"])
        self.stdout.write(f"Joriy mavsum: {name}" + (" (yaratildi)" if created else ""))
