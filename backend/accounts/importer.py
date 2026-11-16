"""Xodimlar ro'yxatini Excel (.xlsx) faylidan yuklash.

Fayl birinchi varag'ining birinchi qatori — sarlavhalar. Tanilgan ustunlar:
    F.I.Sh. (majburiy) | Filial (majburiy) | Lavozim | Telefon | Email | Telegram

Moslash tartibi (mavjud xodimni topish): telefon → email → Telegram username.
Hech biri bo'lmasa yoki mos topilmasa — yangi xodim yaratiladi.
`dry_run=True` bo'lsa bazaga hech narsa yozilmaydi, faqat hisobot qaytadi.
"""
from dataclasses import dataclass, field

from django.db import transaction
from openpyxl import load_workbook

from .models import (
    Branch, Employee, normalize_email, normalize_phone, normalize_telegram_username,
)

HEADER_ALIASES = {
    "full_name": {"f.i.sh.", "f.i.sh", "fish", "fio", "ф.и.о.", "ф.и.о", "фио", "ism familiya", "xodim"},
    "branch": {"filial", "филиал", "bo'lim", "bo‘lim"},
    "position": {"lavozim", "lavozimi", "должность"},
    "phone": {"telefon", "телефон", "tel", "phone"},
    "email": {"email", "e-mail", "pochta", "почта"},
    "telegram_username": {"telegram", "telegram username", "телеграм"},
}
REQUIRED = ("full_name", "branch")


class ImportFormatError(Exception):
    pass


@dataclass
class ImportReport:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    deactivated: int = 0
    errors: list = field(default_factory=list)  # (qator, sabab)
    warnings: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.errors

    def summary(self) -> str:
        return (f"Yangi: {self.created}, yangilandi: {self.updated}, o'zgarmadi: {self.unchanged}, "
                f"nofaol qilindi: {self.deactivated}, xato: {len(self.errors)}, "
                f"ogohlantirish: {len(self.warnings)}")


def _norm_header(value) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _map_headers(row) -> dict:
    mapping = {}
    for idx, cell in enumerate(row):
        h = _norm_header(cell)
        for key, aliases in HEADER_ALIASES.items():
            if h in aliases and key not in mapping:
                mapping[key] = idx
    missing = [k for k in REQUIRED if k not in mapping]
    if missing:
        names = {"full_name": "F.I.Sh.", "branch": "Filial"}
        raise ImportFormatError("Majburiy ustun topilmadi: " + ", ".join(names[m] for m in missing))
    return mapping


def _cell(row, mapping, key):
    idx = mapping.get(key)
    if idx is None or idx >= len(row):
        return ""
    value = row[idx]
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return " ".join(str(value).split())


def _find_existing(phone, email, tg):
    if phone:
        e = Employee.objects.filter(phone=phone).first()
        if e:
            return e
    if email:
        e = Employee.objects.filter(email=email).first()
        if e:
            return e
    if tg:
        return Employee.objects.filter(telegram_username=tg).first()
    return None


def import_employees(path_or_file, *, dry_run=False, deactivate_missing=False) -> ImportReport:
    wb = load_workbook(path_or_file, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = ws.iter_rows(values_only=True)
    try:
        header = next(rows)
    except StopIteration:
        raise ImportFormatError("Fayl bo'sh.")
    mapping = _map_headers(header)

    report = ImportReport()
    seen_ids = set()
    seen_keys = {}  # telefon/email/tg -> qator raqami (fayl ichidagi takrorlar)

    with transaction.atomic():
        for row_no, row in enumerate(rows, start=2):
            if row is None or all(v in (None, "") for v in row):
                continue
            full_name = _cell(row, mapping, "full_name")
            branch_name = _cell(row, mapping, "branch")
            position = _cell(row, mapping, "position")
            raw_phone = _cell(row, mapping, "phone")
            phone = normalize_phone(raw_phone)
            email = normalize_email(_cell(row, mapping, "email"))
            tg = normalize_telegram_username(_cell(row, mapping, "telegram_username"))

            if not full_name or not branch_name:
                report.errors.append((row_no, "F.I.Sh. yoki Filial bo'sh"))
                continue
            if raw_phone and not phone:
                report.warnings.append((row_no, "Telefon formati tanilmadi, telefonsiz yozildi"))
            if email and "@" not in email:
                report.errors.append((row_no, "Email noto'g'ri"))
                continue

            dup = False
            for key in (("phone", phone), ("email", email), ("tg", tg)):
                if key[1]:
                    if key in seen_keys:
                        report.errors.append(
                            (row_no, f"Fayl ichida takror ({key[0]}): {seen_keys[key]}-qator bilan bir xil"))
                        dup = True
                        break
            if dup:
                continue
            for key in (("phone", phone), ("email", email), ("tg", tg)):
                if key[1]:
                    seen_keys[key] = row_no

            branch, _ = Branch.objects.get_or_create(name=branch_name)
            employee = _find_existing(phone, email, tg)
            new_values = {
                "full_name": full_name, "branch_id": branch.pk, "position": position,
                "phone": phone, "email": email, "telegram_username": tg, "is_active": True,
            }
            if employee is None:
                employee = Employee(**new_values)
                try:
                    employee.full_clean(exclude=["branch"])
                except Exception as exc:  # noqa: BLE001 — sababni hisobotga yozamiz
                    report.errors.append((row_no, f"Tekshiruvdan o'tmadi: {exc}"))
                    continue
                employee.save()
                report.created += 1
            else:
                # Faylda bo'sh kelgan aloqa maydonlari mavjud qiymatni o'chirmaydi
                for key in ("phone", "email", "telegram_username", "position"):
                    if not new_values[key]:
                        new_values[key] = getattr(employee, key)
                changed = {k: v for k, v in new_values.items() if getattr(employee, k) != v}
                if changed:
                    for k, v in changed.items():
                        setattr(employee, k, v)
                    try:
                        employee.validate_constraints()
                    except Exception as exc:  # noqa: BLE001
                        report.errors.append((row_no, f"Boshqa xodim bilan to'qnashuv: {exc}"))
                        continue
                    employee.save()
                    report.updated += 1
                else:
                    report.unchanged += 1
            seen_ids.add(employee.pk)

        if deactivate_missing and report.ok:
            missing = Employee.objects.filter(is_active=True).exclude(pk__in=seen_ids)
            report.deactivated = missing.update(is_active=False)

        if dry_run or not report.ok:
            # Xato bo'lsa — hech narsa saqlanmaydi (hammasi yoki hech narsa).
            transaction.set_rollback(True)

    wb.close()
    return report
