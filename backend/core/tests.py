from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from core.models import Module, Role, RoleAssignment, Season
from core.services import has_role


class SeasonTests(TestCase):
    def test_only_one_active(self):
        Season.objects.create(name="2025–2026", start_date=date(2025, 9, 1),
                              end_date=date(2026, 8, 31), is_active=True)
        s = Season(name="2026–2027", start_date=date(2026, 9, 1), end_date=date(2027, 8, 31),
                   is_active=True)
        with self.assertRaises(ValidationError):
            s.full_clean()

    def test_overlap_rejected(self):
        Season.objects.create(name="A", start_date=date(2025, 9, 1), end_date=date(2026, 8, 31))
        s = Season(name="B", start_date=date(2026, 6, 1), end_date=date(2027, 5, 31))
        with self.assertRaises(ValidationError):
            s.full_clean()


class RoleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="u", status=User.Status.ACTIVE)
        self.s1 = Season.objects.create(name="A", start_date=date(2025, 9, 1), end_date=date(2026, 8, 31))
        self.s2 = Season.objects.create(name="B", start_date=date(2026, 9, 1), end_date=date(2027, 8, 31))

    def test_role_scoped_by_module_and_season(self):
        RoleAssignment.objects.create(user=self.user, role=Role.SCORER, module=Module.ZAKOVAT, season=self.s1)
        self.assertTrue(has_role(self.user, Role.SCORER, Module.ZAKOVAT, self.s1))
        self.assertFalse(has_role(self.user, Role.SCORER, Module.ZAKOVAT, self.s2))
        self.assertFalse(has_role(self.user, Role.SCORER, Module.KITOBXONLIK))

    def test_role_without_season_applies_everywhere(self):
        RoleAssignment.objects.create(user=self.user, role=Role.REVIEWER, module=Module.KITOBXONLIK)
        self.assertTrue(has_role(self.user, Role.REVIEWER, Module.KITOBXONLIK, self.s2))

    def test_admin_has_all_roles(self):
        RoleAssignment.objects.create(user=self.user, role=Role.ADMIN)
        self.assertTrue(has_role(self.user, Role.SCORER, Module.ZAKOVAT, self.s1))
