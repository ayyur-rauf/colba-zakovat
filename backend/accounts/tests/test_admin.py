from django.test import TestCase

from accounts.models import Employee, User
from accounts.tests.test_importer import HEADER, make_xlsx


class AdminImportViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create(username="admin", is_staff=True, is_superuser=True,
                                         status=User.Status.ACTIVE)
        self.client.force_login(self.admin)

    def test_pages_render(self):
        for url in ("/admin/", "/admin/accounts/employee/", "/admin/accounts/employee/import/",
                    "/admin/accounts/user/", "/admin/core/roleassignment/add/", "/admin/core/auditlog/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_upload_saves_employees(self):
        f = make_xlsx([HEADER, ["Aliyev Vali", "Chilonzor", "", "901234567", "", ""]])
        f.name = "xodimlar.xlsx"
        r = self.client.post("/admin/accounts/employee/import/", {"file": f, "dry_run": ""})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Yangi: 1")
        self.assertEqual(Employee.objects.count(), 1)

    def test_non_superuser_cannot_import(self):
        staff = User.objects.create(username="s", is_staff=True, status=User.Status.ACTIVE)
        self.client.force_login(staff)
        r = self.client.get("/admin/accounts/employee/import/")
        self.assertEqual(r.status_code, 302)
