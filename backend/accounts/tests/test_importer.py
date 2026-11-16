import io

from django.test import TestCase
from openpyxl import Workbook

from accounts.importer import ImportFormatError, import_employees
from accounts.models import Branch, Employee


def make_xlsx(rows):
    wb = Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


HEADER = ["F.I.Sh.", "Filial", "Lavozim", "Telefon", "Email", "Telegram"]


class ImporterTests(TestCase):
    def test_creates_employees_and_branches(self):
        f = make_xlsx([
            HEADER,
            ["Aliyev Vali", "Chilonzor", "O'qituvchi", "90 123 45 67", "Vali@Mail.uz", "@vali"],
            ["Karimova Laylo", "Yunusobod", "Metodist", "+998 (91) 765-43-21", "", ""],
        ])
        r = import_employees(f)
        self.assertTrue(r.ok, r.errors)
        self.assertEqual(r.created, 2)
        self.assertEqual(Branch.objects.count(), 2)
        vali = Employee.objects.get(full_name="Aliyev Vali")
        self.assertEqual(vali.phone, "+998901234567")
        self.assertEqual(vali.email, "vali@mail.uz")
        self.assertEqual(vali.telegram_username, "vali")

    def test_second_import_updates_by_phone_and_keeps_missing_contacts(self):
        import_employees(make_xlsx([HEADER, ["Aliyev Vali", "Chilonzor", "", "901234567", "v@x.uz", ""]]))
        r = import_employees(make_xlsx([HEADER, ["Aliyev Vali", "Sergeli", "Direktor", "+998901234567", "", ""]]))
        self.assertEqual((r.created, r.updated), (0, 1))
        e = Employee.objects.get()
        self.assertEqual(e.branch.name, "Sergeli")
        self.assertEqual(e.email, "v@x.uz")  # bo'sh kelgan email o'chirilmadi

    def test_errors_roll_back_everything(self):
        f = make_xlsx([
            HEADER,
            ["Aliyev Vali", "Chilonzor", "", "901234567", "", ""],
            ["", "Chilonzor", "", "", "", ""],
            ["Boshqa odam", "Chilonzor", "", "90-123-45-67", "", ""],  # fayl ichida takror telefon
        ])
        r = import_employees(f)
        self.assertFalse(r.ok)
        self.assertEqual([row for row, _ in r.errors], [3, 4])
        self.assertEqual(Employee.objects.count(), 0)

    def test_dry_run_saves_nothing(self):
        r = import_employees(make_xlsx([HEADER, ["Aliyev Vali", "Chilonzor"]]), dry_run=True)
        self.assertEqual(r.created, 1)
        self.assertEqual(Employee.objects.count(), 0)

    def test_deactivate_missing(self):
        import_employees(make_xlsx([HEADER, ["A", "F1", "", "901111111"], ["B", "F1", "", "902222222"]]))
        r = import_employees(make_xlsx([HEADER, ["A", "F1", "", "901111111"]]), deactivate_missing=True)
        self.assertEqual(r.deactivated, 1)
        self.assertFalse(Employee.objects.get(full_name="B").is_active)

    def test_missing_required_column(self):
        with self.assertRaises(ImportFormatError):
            import_employees(make_xlsx([["Ism", "Telefon"], ["A", "901111111"]]))

    def test_russian_headers(self):
        r = import_employees(make_xlsx([["ФИО", "Филиал", "Телефон"], ["Иванов", "Центр", "901111111"]]))
        self.assertEqual(r.created, 1)
