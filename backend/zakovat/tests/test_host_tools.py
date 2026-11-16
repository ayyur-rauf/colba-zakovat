"""Savollar banki, o'yin savollari, taymer va o'yinni bekor qilish."""
from datetime import timedelta

from rest_framework.test import APIClient

from core.models import Module, Role, RoleAssignment
from zakovat import services as svc
from zakovat.models import Game, Question
from zakovat.tests.test_services import Base, aware


class QuestionBankTests(Base):
    def test_only_tg_manages_bank_and_validation(self):
        outsider = self.user("oddiy")
        with self.assertRaises(svc.RuleError):
            svc.save_question(outsider, text="Savol", answer="Javob")
        with self.assertRaisesMessage(svc.RuleError, "majburiy"):
            svc.save_question(self.tg, text="Savol", answer=" ")
        q = svc.save_question(self.tg, text="Poytaxt?", answer="Toshkent", topic="Geografiya", difficulty=2)
        self.assertEqual(q.author, self.tg)
        with self.assertRaisesMessage(svc.RuleError, "avtomatik"):
            svc.save_question(self.tg, q, status=Question.Status.USED)

    def test_assign_autofill_and_reuse_rules(self):
        g = self.game(rounds=1, qpr=4)
        qs = [svc.save_question(self.tg, text=f"S{i}", answer=f"J{i}", status="approved") for i in range(5)]
        svc.assign_question(g, self.tg, 2, qs[0])
        self.assertEqual(svc.autofill_questions(g, self.tg, [q.pk for q in qs[1:]]), 3)  # 1,3,4 bo'sh edi
        self.assertEqual(sorted(g.questions.values_list("number", flat=True)), [1, 2, 3, 4])
        g2 = self.game(starts=aware(2026, 11, 21, 15), rounds=1, qpr=4)
        with self.assertRaisesMessage(svc.RuleError, "allaqachon biriktirilgan"):
            svc.assign_question(g2, self.tg, 1, qs[0])
        with self.assertRaisesMessage(svc.RuleError, "o'chirib bo'lmaydi"):
            svc.delete_question(self.tg, qs[0])
        svc.assign_question(g, self.tg, 2, None)  # bo'shatish
        svc.delete_question(self.tg, qs[0])

    def test_used_after_final_and_not_reusable(self):
        a = self.team("Alfa")
        g = self.game(rounds=1, qpr=4)
        q = svc.save_question(self.tg, text="S", answer="J", status="approved")
        svc.assign_question(g, self.tg, 1, q)
        self.play(g, {a: {1}})
        svc.finalize_game(g, self.tg)
        q.refresh_from_db()
        self.assertEqual(q.status, Question.Status.USED)
        g2 = self.game(starts=aware(2026, 11, 21, 15))
        with self.assertRaisesMessage(svc.RuleError, "ishlatilgan"):
            svc.assign_question(g2, self.tg, 1, q)

    def test_questions_api_visibility(self):
        g = self.game(rounds=1, qpr=2)
        q = svc.save_question(self.tg, text="Maxfiy savol", answer="Javob")
        svc.assign_question(g, self.tg, 1, q)
        api = APIClient()
        player = self.user("oyinchi")
        api.force_authenticate(player)
        self.assertEqual(api.get(f"/api/zakovat/games/{g.pk}/questions/").status_code, 403)
        self.assertEqual(api.get("/api/zakovat/questions/").status_code, 403)
        host = self.user("boshlovchi")
        RoleAssignment.objects.create(user=host, role=Role.HOST, module=Module.ZAKOVAT)
        api.force_authenticate(host)
        rows = api.get(f"/api/zakovat/games/{g.pk}/questions/").data
        self.assertEqual(rows[0]["question"]["answer"], "Javob")
        self.assertIsNone(rows[1]["question"])
        api.force_authenticate(self.tg)
        data = api.get("/api/zakovat/questions/?free=1").data
        self.assertEqual(data["items"], [])  # yagona savol biriktirilgan


class TimerAndCancelTests(Base):
    def _started(self):
        a = self.team("Alfa")
        g = self.game()
        reg = svc.register_team(g, a, a.captain, now=g.starts_at - timedelta(days=3))
        svc.approve_registration(reg, self.tg)
        svc.start_game(g, self.tg)
        return g

    def test_timer_start_pause_resume_reset(self):
        g = self._started()
        t0 = aware(2026, 10, 17, 15, 5)
        svc.control_timer(g, self.tg, "start", now=t0)
        st = svc.timer_state(g, now=t0 + timedelta(seconds=20))
        self.assertTrue(st["running"])
        self.assertAlmostEqual(st["remaining"], 40, delta=0.2)
        svc.control_timer(g, self.tg, "pause", now=t0 + timedelta(seconds=20))
        self.assertEqual(svc.timer_state(g, now=t0 + timedelta(minutes=5))["remaining"], 40)
        svc.control_timer(g, self.tg, "start", now=t0 + timedelta(minutes=5))
        self.assertEqual(svc.timer_state(g, now=t0 + timedelta(minutes=6))["remaining"], 0)
        svc.control_timer(g, self.tg, "reset", seconds=30)
        st = svc.timer_state(g)
        self.assertEqual((st["running"], st["remaining"], st["seconds"]), (False, 30, 30))

    def test_new_question_resets_timer_and_host_can_control(self):
        g = self._started()
        host = self.user("boshlovchi")
        RoleAssignment.objects.create(user=host, role=Role.HOST, module=Module.ZAKOVAT)
        svc.control_timer(g, host, "start")
        svc.set_current_question(g, host, 2)
        self.assertFalse(svc.timer_state(g)["running"])
        with self.assertRaises(svc.RuleError):
            svc.control_timer(g, self.user("begona"), "start")

    def test_cancel_only_before_start_with_reason(self):
        g = self.game()
        with self.assertRaisesMessage(svc.RuleError, "sababini"):
            svc.cancel_game(g, self.tg, reason=" ")
        svc.cancel_game(g, self.tg, reason="Zal band")
        g.refresh_from_db()
        self.assertEqual(g.status, Game.Status.CANCELLED)
        started = self._started()
        with self.assertRaisesMessage(svc.RuleError, "boshlanmagan"):
            svc.cancel_game(started, self.tg, reason="x")
