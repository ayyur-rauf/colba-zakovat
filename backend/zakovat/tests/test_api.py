from datetime import timedelta
from unittest import mock

from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Branch, Employee, User
from zakovat.models import Game, Team
from zakovat.tests.test_services import Base, aware


class ApiBase(Base):
    def setUp(self):
        super().setUp()
        self.api = APIClient()

    def as_user(self, user):
        self.api.force_authenticate(user)
        return self.api


class ParticipantApiTests(ApiBase):
    def test_requires_login(self):
        self.assertEqual(APIClient().get("/api/zakovat/games/").status_code, 401)

    def test_team_creation_invite_and_accept(self):
        branch = Branch.objects.create(name="Chilonzor")
        cap = self.user("cap")
        friend = self.user("friend")
        friend.employee = Employee.objects.create(full_name="Do'st Odam", branch=branch)
        friend.save()

        with mock.patch("zakovat.services.timezone.now", return_value=self.before_season):
            r = self.as_user(cap).post("/api/zakovat/teams/", {"name": "Bilimdonlar"}, format="json")
            self.assertEqual(r.status_code, 201, r.data)
            team_id = r.data["id"]
            r = self.api.get("/api/zakovat/players/?q=do'st")
            self.assertEqual(r.data[0]["name"], "Do'st Odam")
            self.assertNotIn("phone", r.data[0])
            r = self.api.post(f"/api/zakovat/teams/{team_id}/invite/", {"user_id": friend.pk}, format="json")
            self.assertEqual(r.status_code, 201, r.data)

            me = self.as_user(friend).get("/api/zakovat/me/").data
            self.assertEqual(len(me["invitations"]), 1)
            r = self.api.post(f"/api/zakovat/invitations/{me['invitations'][0]['id']}/respond/",
                              {"accept": True}, format="json")
            self.assertEqual(r.data["status"], "active")
            self.assertEqual(self.api.get("/api/zakovat/me/").data["team"]["id"], team_id)

    def test_rule_error_returns_400_with_message(self):
        t = self.team("Alfa", size=4, approve=False)
        r = self.as_user(t.captain).post(f"/api/zakovat/teams/{t.pk}/approve/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("ruxsat", r.data["detail"])

    def test_full_game_via_api(self):
        a, b = self.team("Alfa"), self.team("Beta")
        g = self.game(starts=timezone.now() + timedelta(days=5))
        for t in (a, b):
            r = self.as_user(t.captain).post(f"/api/zakovat/games/{g.pk}/register/", format="json")
            self.assertEqual(r.status_code, 201, r.data)
        regs = self.as_user(self.tg).get(f"/api/zakovat/games/{g.pk}/registrations/").data
        for reg in regs:
            self.assertEqual(self.api.post(f"/api/zakovat/registrations/{reg['id']}/approve/").status_code, 200)

        # natija hali ko'rinmaydi
        r = self.as_user(a.captain).get(f"/api/zakovat/games/{g.pk}/results/")
        self.assertEqual(r.status_code, 400)
        # oddiy o'yinchi jadvalni ko'ra olmaydi
        self.assertEqual(self.api.get(f"/api/zakovat/games/{g.pk}/sheet/").status_code, 403)

        tg = self.as_user(self.tg)
        self.assertEqual(tg.post(f"/api/zakovat/games/{g.pk}/start/").status_code, 200)
        for t in (a, b):
            for u in self.players(t)[:3]:
                r = tg.post(f"/api/zakovat/games/{g.pk}/lineup/",
                            {"team_id": t.pk, "round_no": 1, "user_id": u.pk}, format="json")
                self.assertEqual(r.status_code, 201, r.data)
        r = tg.post(f"/api/zakovat/games/{g.pk}/marks/", {"marks": [
            {"team_id": a.pk, "number": 1, "correct": True},
            {"team_id": a.pk, "number": 2, "correct": True},
            {"team_id": b.pk, "number": 1, "correct": True},
            {"team_id": b.pk, "number": 2, "correct": False},
        ]}, format="json")
        self.assertEqual(r.data["saved"], 4)
        sheet = tg.get(f"/api/zakovat/games/{g.pk}/sheet/").data
        alfa = next(x for x in sheet["teams"] if x["team"]["id"] == a.pk)
        self.assertEqual((alfa["points"], alfa["answers"][:3]), (2, [True, True, None]))

        # katta ekran: reyting yashirilsa ko'rinmaydi
        Game.objects.filter(pk=g.pk).update(hide_standings=True)
        live = self.as_user(a.captain).get(f"/api/zakovat/games/{g.pk}/live/").data
        self.assertTrue(live["standings_hidden"])
        self.assertEqual(live["standings"], [])

        self.assertEqual(self.as_user(self.tg).post(f"/api/zakovat/games/{g.pk}/publish/").status_code, 200)
        r = self.as_user(b.captain).post(f"/api/zakovat/games/{g.pk}/appeals/",
                                         {"number": 2, "content": "To'g'ri edi", "evidence": "Manba"},
                                         format="json")
        self.assertEqual(r.status_code, 201, r.data)
        appeal_id = r.data["id"]
        # A jamoa B ning apellyatsiyasini ko'rmaydi
        self.assertEqual(self.as_user(a.captain).get(f"/api/zakovat/games/{g.pk}/appeals/").data, [])
        r = self.as_user(self.tg).post(f"/api/zakovat/appeals/{appeal_id}/decide/",
                                       {"accept": False, "reason": "Javob boshqa"}, format="json")
        self.assertEqual(r.data["status"], "rejected")
        r = self.api.post(f"/api/zakovat/games/{g.pk}/finalize/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([row["team"]["name"] for row in r.data["rows"]], ["Alfa", "Beta"])
        self.assertEqual(r.data["rows"][0]["answers"][:2], [True, True])

        st = self.as_user(b.captain).get("/api/zakovat/standings/").data
        self.assertEqual([(x["team"]["name"], x["points"]) for x in st["rows"]], [("Alfa", 2), ("Beta", 1)])


class OrganizerApiTests(ApiBase):
    def test_schedule_and_late_change(self):
        tg = self.as_user(self.tg)
        r = tg.post("/api/zakovat/games/generate-schedule/",
                    {"start_time": "16:00", "venue": "Majlislar zali", "months": [9, 10, 11]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(len(r.data), 3)
        g = Game.objects.filter(season=self.season).order_by("starts_at").last()
        with mock.patch("zakovat.services.timezone.now", return_value=g.starts_at - timedelta(hours=5)):
            r = tg.patch(f"/api/zakovat/games/{g.pk}/", {"venue": "Boshqa zal"}, format="json")
            self.assertEqual(r.status_code, 400)
            self.assertIn("N-1.4", r.data["detail"])
            r = tg.patch(f"/api/zakovat/games/{g.pk}/", {"venue": "Boshqa zal", "reason": "Ta'mir"},
                         format="json")
            self.assertEqual(r.status_code, 200, r.data)

    def test_non_tg_cannot_create_game(self):
        u = self.user("oddiy")
        r = self.as_user(u).post("/api/zakovat/games/", {"title": "X", "starts_at": "2026-12-19T15:00:00+05:00"},
                                 format="json")
        self.assertEqual(r.status_code, 403)
