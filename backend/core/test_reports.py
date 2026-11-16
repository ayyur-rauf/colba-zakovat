"""Excel eksport, ball reestri, Yil sarhisobi, kitobxonlik yubormaganlar ro'yxati."""
import io
from datetime import timedelta

from openpyxl import load_workbook
from rest_framework.test import APIClient

from core.models import Module, PointsEntry, Role, RoleAssignment
from zakovat import services as svc
from zakovat.tests.test_services import Base


def read_xlsx(resp):
    wb = load_workbook(io.BytesIO(resp.content))
    return {ws.title: [list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets}


class ReportsTests(Base):
    def setUp(self):
        super().setUp()
        self.a, self.b = self.team("Alfa"), self.team("Beta")
        self.g = self.game()
        self.play(self.g, {self.a: {1, 2}, self.b: {1}})
        svc.finalize_game(self.g, self.tg)
        self.admin = self.user("adm")
        RoleAssignment.objects.create(user=self.admin, role=Role.ADMIN)
        self.api = APIClient()
        self.api.force_authenticate(self.admin)

    def test_game_and_standings_export(self):
        r = self.api.get(f"/api/zakovat/games/{self.g.pk}/export/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheetml", r["Content-Type"])
        sheets = read_xlsx(r)
        rows = sheets["Natija"]
        self.assertEqual(rows[0][:5], ["O'rin", "Stol", "Jamoa", "Ball", "J"])
        self.assertEqual((rows[1][2], rows[1][3], rows[1][6:8]), ("Alfa", 2, [1, 1]))
        st = read_xlsx(self.api.get("/api/zakovat/standings/export/"))["Reyting"]
        self.assertEqual(st[1][1], "Alfa")

    def test_points_ledger_list_and_manual_correction(self):
        data = self.api.get("/api/manage/points/?module=zakovat").data
        self.assertTrue(any(i["subject"] == "Alfa" and i["reason"].startswith("O'yin") for i in data["items"]))
        bad = self.api.post("/api/manage/points/", {"module": "zakovat", "subject_type": "team", "subject_id": self.b.pk,
                                                    "amount": 3, "note": " "}, format="json")
        self.assertEqual(bad.status_code, 400)
        ok = self.api.post("/api/manage/points/", {"module": "zakovat", "subject_type": "team", "subject_id": self.b.pk,
                                                   "amount": 3, "note": "Texnik xato tuzatildi"}, format="json")
        self.assertEqual(ok.status_code, 201)
        st = svc.season_standings(self.season)
        self.assertEqual([(r["team"].name, r["points"]) for r in st], [("Beta", 4), ("Alfa", 2)])
        self.assertEqual(PointsEntry.objects.get(pk=ok.data["id"]).reason_type, "manual")
        # oddiy foydalanuvchiga yopiq
        self.api.force_authenticate(self.a.captain)
        self.assertEqual(self.api.get("/api/manage/points/").status_code, 403)

    def test_summary(self):
        s = self.api.get("/api/manage/summary/").data
        self.assertEqual(s["zakovat"]["games_played"], 1)
        self.assertEqual(s["zakovat"]["top"][0]["team"], "Alfa")
        self.assertEqual(len(s["zakovat"]["top"][0]["members"]), 4)
        x = read_xlsx(self.api.get("/api/manage/summary/export/"))
        self.assertEqual(set(x), {"Zakovat g'oliblari", "Kitobxonlar", "Filiallar"})


class MissingReviewsTests(Base):
    def test_missing_list_and_permission(self):
        from kitobxonlik.tests.test_flow import pdf
        from kitobxonlik import services as ksvc
        from accounts.models import Branch, Employee
        org = self.user("org")
        RoleAssignment.objects.create(user=org, role=Role.ORGANIZER, module=Module.KITOBXONLIK)
        br = Branch.objects.create(name="Filial")
        for u in (org, self.user("ali"), self.user("vali")):
            u.employee = Employee.objects.create(full_name=u.username.title(), branch=br)
            u.save()
        from accounts.models import User
        ali, vali = User.objects.get(username="ali"), User.objects.get(username="vali")
        b1 = ksvc.add_book(org, title="A", author="X", pdf=pdf(), rights_confirmed=True)
        b2 = ksvc.add_book(org, title="B", author="Y", pdf=pdf(), rights_confirmed=True)
        rnd = ksvc.create_round(self.season, org, title="T", book_ids=[b1.pk, b2.pk],
                                criteria=[{"name": "M", "max_points": 5}], min_review_length=1)
        from django.utils import timezone
        t0 = timezone.now()
        ksvc.start_voting(rnd, org, vote_ends=t0 + timedelta(hours=1), now=t0)
        ksvc.cast_vote(rnd, ali, b1, now=t0)
        ksvc.close_voting(rnd, org, now=t0 + timedelta(hours=1))
        ksvc.submit_review(rnd, ali, text="Yaxshi kitob", now=t0 + timedelta(hours=2))
        api = APIClient()
        api.force_authenticate(org)
        data = api.get(f"/api/kitob/rounds/{rnd.pk}/missing/").data
        names = [i["name"] for i in data["items"]]
        self.assertIn("Vali", names)
        self.assertNotIn("Ali", names)
        self.assertEqual(data["submitted"], 1)
        api.force_authenticate(vali)
        self.assertEqual(api.get(f"/api/kitob/rounds/{rnd.pk}/missing/").status_code, 403)
