import io
from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from openpyxl import Workbook
from rest_framework.test import APIClient

from accounts.models import Branch, Employee, User
from core.models import Announcement, AuditLog, Module, Role, RoleAssignment, Season


def xlsx(rows):
    wb = Workbook()
    for r in rows:
        wb.active.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    buf.name = "xodimlar.xlsx"
    return buf


class ManageTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(name="Chilonzor")
        emp = Employee.objects.create(full_name="Bosh Admin", branch=self.branch, email="a@x.uz")
        self.admin = User.objects.create(username="adm", employee=emp, status=User.Status.ACTIVE)
        RoleAssignment.objects.create(user=self.admin, role=Role.ADMIN)
        self.plain = User.objects.create(username="oddiy", status=User.Status.ACTIVE,
                                         employee=Employee.objects.create(full_name="Oddiy Xodim", branch=self.branch))
        self.api = APIClient()
        self.api.force_authenticate(self.admin)

    def test_non_admin_forbidden(self):
        self.api.force_authenticate(self.plain)
        for url in ("/api/manage/employees/", "/api/manage/users/", "/api/manage/roles/", "/api/manage/audit/"):
            self.assertEqual(self.api.get(url).status_code, 403, url)

    def test_import_dry_run_then_save(self):
        f = xlsx([["F.I.Sh.", "Filial", "Telefon"], ["Yangi Xodim", "Sergeli", "901112233"]])
        r = self.api.post("/api/manage/employees/import/", {"file": f, "dry_run": "true"}, format="multipart")
        self.assertEqual((r.status_code, r.data["created"], r.data["saved"]), (200, 1, False))
        self.assertFalse(Employee.objects.filter(full_name="Yangi Xodim").exists())
        f = xlsx([["F.I.Sh.", "Filial", "Telefon"], ["Yangi Xodim", "Sergeli", "901112233"]])
        r = self.api.post("/api/manage/employees/import/", {"file": f, "dry_run": "false"}, format="multipart")
        self.assertTrue(r.data["saved"])
        self.assertTrue(Employee.objects.filter(full_name="Yangi Xodim").exists())
        self.assertTrue(AuditLog.objects.filter(action="employees.imported").exists())

    def test_import_errors_reported(self):
        f = xlsx([["F.I.Sh.", "Filial"], ["", "Sergeli"]])
        r = self.api.post("/api/manage/employees/import/", {"file": f, "dry_run": "false"}, format="multipart")
        self.assertFalse(r.data["ok"])
        self.assertEqual(r.data["errors"][0]["row"], 2)

    def test_employee_list_masks_phone_and_deactivate(self):
        e = Employee.objects.create(full_name="Tel Egasi", branch=self.branch, phone="901234567")
        data = self.api.get("/api/manage/employees/?q=Tel").data
        self.assertEqual(data["items"][0]["phone"], "****4567")
        r = self.api.patch(f"/api/manage/employees/{e.pk}/", {"is_active": False}, format="json")
        self.assertFalse(r.data["is_active"])

    def test_approve_pending_user_by_linking_employee(self):
        pending = User.objects.create(username="p", status=User.Status.PENDING, display_name="Tg User")
        emp = Employee.objects.create(full_name="Bog'lanadigan", branch=self.branch)
        r = self.api.post(f"/api/manage/users/{pending.pk}/approve/", {}, format="json")
        self.assertEqual(r.status_code, 400)  # xodimsiz tasdiqlanmaydi
        r = self.api.post(f"/api/manage/users/{pending.pk}/approve/", {"employee_id": emp.pk}, format="json")
        self.assertEqual(r.data["status"], "active")
        # bir xodim — bitta akkaunt
        other = User.objects.create(username="p2", status=User.Status.PENDING)
        r = self.api.post(f"/api/manage/users/{other.pk}/approve/", {"employee_id": emp.pk}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_block_and_not_self(self):
        r = self.api.post(f"/api/manage/users/{self.plain.pk}/block/", format="json")
        self.assertEqual(r.data["status"], "blocked")
        self.assertEqual(self.api.post(f"/api/manage/users/{self.admin.pk}/block/", format="json").status_code, 400)

    def test_roles_grant_duplicate_and_delete(self):
        body = {"user_id": self.plain.pk, "role": "scorer", "module": "zakovat"}
        self.assertEqual(self.api.post("/api/manage/roles/", body, format="json").status_code, 201)
        self.assertEqual(self.api.post("/api/manage/roles/", body, format="json").status_code, 400)
        rid = RoleAssignment.objects.get(user=self.plain).pk
        self.assertEqual(self.api.delete(f"/api/manage/roles/{rid}/").status_code, 204)
        own = RoleAssignment.objects.get(user=self.admin, role=Role.ADMIN).pk
        self.assertEqual(self.api.delete(f"/api/manage/roles/{own}/").status_code, 400)

    def test_seasons_create_and_activate(self):
        r = self.api.post("/api/manage/seasons/", {"name": "2027–2028", "start_date": "2027-09-01",
                                                   "end_date": "2028-08-31"}, format="json")
        self.assertEqual(r.status_code, 201)
        bad = self.api.post("/api/manage/seasons/", {"name": "X", "start_date": "2028-01-01",
                                                     "end_date": "2028-06-01"}, format="json")
        self.assertEqual(bad.status_code, 400)  # ustma-ust
        self.api.post(f"/api/manage/seasons/{r.data['id']}/activate/")
        self.assertEqual(Season.current().name, "2027–2028")


class AnnouncementTests(TestCase):
    def setUp(self):
        b = Branch.objects.create(name="F")
        self.tg = User.objects.create(username="tg", status="active", employee=Employee.objects.create(full_name="TG", branch=b))
        RoleAssignment.objects.create(user=self.tg, role=Role.TG_MEMBER, module=Module.ZAKOVAT)
        self.plain = User.objects.create(username="u", status="active", employee=Employee.objects.create(full_name="U", branch=b))
        self.api = APIClient()

    def test_permissions_and_visibility(self):
        self.api.force_authenticate(self.tg)
        r = self.api.post("/api/announcements/", {"title": "Ertaga 3-tur", "module": "zakovat"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.api.post("/api/announcements/", {"title": "X", "module": "kitobxonlik"},
                                       format="json").status_code, 403)
        Announcement.objects.create(title="Eskirgan", expires_at=timezone.now() - timedelta(days=1))
        Announcement.objects.create(title="Yashirin", is_active=False)
        self.api.force_authenticate(self.plain)
        data = self.api.get("/api/announcements/").data
        self.assertEqual([a["title"] for a in data["items"]], ["Ertaga 3-tur"])
        self.assertEqual(data["can_post"], [])
        self.assertEqual(self.api.post("/api/announcements/", {"title": "Y"}, format="json").status_code, 403)
