from django.core.management.base import BaseCommand, CommandError

from accounts.importer import ImportFormatError, import_employees
from core.services import log_action


class Command(BaseCommand):
    help = "Xodimlar ro'yxatini Excel (.xlsx) faylidan yuklaydi."

    def add_arguments(self, parser):
        parser.add_argument("path", help=".xlsx fayl yo'li")
        parser.add_argument("--dry-run", action="store_true", help="Bazaga yozmasdan tekshirish")
        parser.add_argument("--deactivate-missing", action="store_true",
                            help="Faylda yo'q xodimlarni 'ishlamaydi' deb belgilash")

    def handle(self, *args, path, dry_run, deactivate_missing, **opts):
        try:
            report = import_employees(path, dry_run=dry_run, deactivate_missing=deactivate_missing)
        except ImportFormatError as exc:
            raise CommandError(str(exc))
        for row, reason in report.errors:
            self.stderr.write(f"  XATO {row}-qator: {reason}")
        for row, reason in report.warnings:
            self.stdout.write(f"  Ogohlantirish {row}-qator: {reason}")
        self.stdout.write(report.summary())
        if not report.ok:
            raise CommandError("Xatolar bor — hech narsa saqlanmadi. Faylni tuzatib qayta yuklang.")
        if dry_run:
            self.stdout.write("Sinov rejimi: bazaga hech narsa yozilmadi.")
        else:
            log_action(None, "employees.imported", note=report.summary())
            self.stdout.write(self.style.SUCCESS("Saqlandi."))
