from datetime import date, datetime, timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from core.models import Module, PointsEntry, Role, RoleAssignment, Season
from core.services import points_total
from zakovat import services as svc
from zakovat.models import Game, GameRegistration, GameResult, Team


def aware(*args):
    return timezone.make_aware(datetime(*args))


class Base(TestCase):
    def setUp(self):
        self.season = Season.objects.create(name="2026–2027", start_date=date(2026, 9, 1),
                                            end_date=date(2027, 8, 31), is_active=True)
        self.before_season = aware(2026, 8, 20, 10)
        self.in_season = aware(2026, 10, 1, 10)
        self.tg = self.user("tg")
        RoleAssignment.objects.create(user=self.tg, role=Role.TG_MEMBER, module=Module.ZAKOVAT)
        self._n = 0

    def user(self, name):
        return User.objects.create(username=name, status=User.Status.ACTIVE)

    def team(self, name, size=4, approve=True):
        captain = self.user(f"{name}_cap")
        team = svc.create_team(self.season, captain, name, now=self.before_season)
        for i in range(size - 1):
            u = self.user(f"{name}_{i}")
            m = svc.invite_member(team, captain, u, now=self.before_season)
            svc.respond_invite(m, u, True, now=self.before_season)
        if approve:
            svc.submit_team(team, captain)
            svc.approve_team(team, self.tg)
        return team

    def players(self, team):
        return [m.user for m in team.members.filter(status="active").select_related("user")]

    def game(self, starts=None, **kw):
        g = Game.objects.create(season=self.season, title="1-tur", starts_at=starts or aware(2026, 10, 17, 15),
                                rounds=kw.pop("rounds", 1), questions_per_round=kw.pop("qpr", 4), **kw)
        svc.open_registration(g, self.tg)
        return g

    def play(self, game, answers, players=3):
        """answers: {team: {to'g'ri savollar}} — ro'yxat, tarkib, belgilar, dastlabki natija."""
        for t in answers:
            reg = svc.register_team(game, t, t.captain, now=game.starts_at - timedelta(days=3))
            svc.approve_registration(reg, self.tg)
        svc.start_game(game, self.tg)
        for t, correct in answers.items():
            for r in range(1, game.rounds + 1):
                for u in self.players(t)[:players]:
                    svc.add_to_lineup(game, t, r, u, self.tg, from_question=game.first_question_of(r))
            for q in range(1, game.total_questions + 1):
                svc.set_mark(game, t, q, q in correct, self.tg)
        return svc.publish_preliminary(game, self.tg)


class TeamRuleTests(Base):
    def test_size_limits(self):
        t = self.team("Alfa", size=3, approve=False)
        with self.assertRaisesMessage(svc.RuleError, "N-3.2"):
            svc.submit_team(t, t.captain)
        big = self.team("Beta", size=8, approve=False)
        with self.assertRaisesMessage(svc.RuleError, "N-3.2"):
            svc.invite_member(big, big.captain, self.user("x"), now=self.before_season)

    def test_one_team_per_player(self):
        a = self.team("Alfa")
        b = self.team("Beta", approve=False)
        with self.assertRaisesMessage(svc.RuleError, "N-3.2"):
            svc.invite_member(b, b.captain, self.players(a)[1], now=self.before_season)

    def test_duplicate_name_ignores_case_and_quotes(self):
        self.team("Alfa")
        with self.assertRaisesMessage(svc.RuleError, "N-3.3"):
            svc.create_team(self.season, self.user("z"), '"ALFA"')

    def test_roster_and_name_locked_during_season(self):
        t = self.team("Alfa")
        with self.assertRaisesMessage(svc.RuleError, "N-3.5"):
            svc.invite_member(t, t.captain, self.user("new"), now=self.in_season)
        with self.assertRaisesMessage(svc.RuleError, "N-3.4"):
            svc.rename_team(t, t.captain, "Omega", now=self.in_season)
        # Tashkiliy guruh istisno qila oladi
        svc.invite_member(t, self.tg, self.user("new2"), now=self.in_season)

    def test_only_tg_approves(self):
        t = self.team("Alfa", approve=False)
        svc.submit_team(t, t.captain)
        with self.assertRaises(svc.RuleError):
            svc.approve_team(t, t.captain)


class ScheduleTests(Base):
    def test_third_saturday(self):
        self.assertEqual(svc.third_saturday(2026, 11), date(2026, 11, 21))
        self.assertEqual(svc.third_saturday(2026, 8), date(2026, 8, 15))

    def test_generate_schedule_idempotent(self):
        months = {9, 10, 11, 12, 1, 2, 3, 4, 5}
        games = svc.generate_league_schedule(self.season, self.tg, months=months)
        self.assertEqual(len(games), 9)
        self.assertTrue(all(timezone.localtime(g.starts_at).weekday() == 5 for g in games))
        self.assertEqual(svc.generate_league_schedule(self.season, self.tg, months=months), [])
        self.assertEqual(Game.objects.filter(kind="league", starts_at__month=10).count(), 1)

    def test_late_change_requires_reason(self):
        g = self.game(starts=aware(2026, 10, 17, 15))
        late = aware(2026, 10, 17, 9)
        with self.assertRaisesMessage(svc.RuleError, "N-1.4"):
            svc.update_game(g, self.tg, now=late, venue="Boshqa zal")
        svc.update_game(g, self.tg, now=late, venue="Boshqa zal", reason="Zal ta'mirda")
        g.refresh_from_db()
        self.assertEqual(g.venue, "Boshqa zal")


class RegistrationTests(Base):
    def test_deadline_one_day_before(self):
        g = self.game(starts=aware(2026, 10, 17, 15))
        t = self.team("Alfa")
        with self.assertRaisesMessage(svc.RuleError, "N-3.2"):
            svc.register_team(g, t, t.captain, now=aware(2026, 10, 16, 16))

    def test_capacity_waitlist(self):
        g = self.game(max_teams=1)
        a, b = self.team("Alfa"), self.team("Beta")
        now = g.starts_at - timedelta(days=3)
        svc.register_team(g, a, a.captain, now=now)
        reg_b = svc.register_team(g, b, b.captain, now=now)
        self.assertEqual(reg_b.status, GameRegistration.Status.WAITLIST)


class LineupTests(Base):
    def setUp(self):
        super().setUp()
        self.g = self.game(rounds=2, qpr=3)
        self.t = self.team("Alfa", size=7)
        reg = svc.register_team(self.g, self.t, self.t.captain, now=self.g.starts_at - timedelta(days=3))
        svc.approve_registration(reg, self.tg)

    def test_max_six_on_stage(self):
        p = self.players(self.t)
        for u in p[:6]:
            svc.add_to_lineup(self.g, self.t, 1, u, self.tg)
        with self.assertRaisesMessage(svc.RuleError, "N-5.2"):
            svc.add_to_lineup(self.g, self.t, 1, p[6], self.tg)

    def test_no_substitution_mid_round_but_late_join_allowed(self):
        p = self.players(self.t)
        entry = svc.add_to_lineup(self.g, self.t, 1, p[0], self.tg)
        svc.start_game(self.g, self.tg)
        svc.set_current_question(self.g, self.tg, 2)
        with self.assertRaisesMessage(svc.RuleError, "N-5.2"):
            svc.remove_from_lineup(entry, self.tg)
        late = svc.add_to_lineup(self.g, self.t, 1, p[1], self.tg)
        self.assertEqual(late.from_question, 2)
        with self.assertRaises(svc.RuleError):
            svc.add_to_lineup(self.g, self.t, 1, p[2], self.tg, from_question=1)  # orqaga sana yo'q


class ResultFlowTests(Base):
    def test_full_flow_with_appeal_and_points(self):
        a, b, c = self.team("Alfa"), self.team("Beta"), self.team("Gamma")
        g = self.game()
        self.play(g, {a: {1, 2}, b: {1}, c: set()})

        with self.assertRaisesMessage(svc.RuleError, "N-6.4"):
            svc.set_mark(g, b, 2, True, self.tg)
        with self.assertRaisesMessage(svc.RuleError, "N-7.4"):
            svc.submit_appeal(g, b, self.players(b)[1], number=2, content="x", evidence="y")
        with self.assertRaisesMessage(svc.RuleError, "N-7.4"):
            svc.submit_appeal(g, b, b.captain, number=2, content="x", evidence="")
        with self.assertRaisesMessage(svc.RuleError, "N-7.2"):
            svc.submit_appeal(g, a, a.captain, number=1, content="x", evidence="y")

        appeal = svc.submit_appeal(g, b, b.captain, number=2, content="Javobimiz to'g'ri",
                                   evidence="Manba: ...")
        with self.assertRaisesMessage(svc.RuleError, "apellyatsiya"):
            svc.finalize_game(g, self.tg)
        svc.decide_appeal(appeal, self.tg, accept=True, reason="Javob ma'nosi bir xil")
        self.assertEqual(GameResult.objects.get(game=g, team=b).points, 2)

        svc.finalize_game(g, self.tg)
        with self.assertRaisesMessage(svc.RuleError, "N-7.3"):
            svc.submit_appeal(g, c, c.captain, number=1, content="x", evidence="y")

        tot = lambda t: points_total(season=self.season, module=Module.ZAKOVAT, subject_type="team",
                                     subject_id=t.pk)
        self.assertEqual((tot(a), tot(b), tot(c)), (2, 2, 0))
        # A va B: ball 2 tadan, J ham teng (ikkalasi 1 va 2-savol) → teng guruh
        ra, rb = GameResult.objects.get(game=g, team=a), GameResult.objects.get(game=g, team=b)
        self.assertEqual(ra.place, 1)
        self.assertEqual(ra.tie_group, rb.tie_group)

        # Qo'shimcha o'yin: B yutadi
        tb = svc.create_tiebreak(self.season, self.tg, [a.pk, b.pk], starts_at=aware(2026, 10, 24, 15), parent=g)
        svc.start_game(tb, self.tg)
        for t in (a, b):
            for u in self.players(t)[:3]:
                svc.add_to_lineup(tb, t, 1, u, self.tg)
        svc.set_mark(tb, b, 1, True, self.tg)
        svc.publish_preliminary(tb, self.tg)
        svc.finalize_game(tb, self.tg)
        ra.refresh_from_db()
        rb.refresh_from_db()
        self.assertEqual((rb.place, ra.place), (1, 2))
        self.assertIsNone(ra.tie_group)
        # qo'shimcha o'yin ball bermaydi
        self.assertEqual(tot(b), 2)

    def test_practice_gives_no_points(self):
        a = self.team("Alfa")
        g = self.game(kind=Game.Kind.PRACTICE)
        self.play(g, {a: {1}})
        svc.finalize_game(g, self.tg)
        self.assertFalse(PointsEntry.objects.exists())

    def test_two_players_round_not_counted(self):
        a, b = self.team("Alfa"), self.team("Beta")
        g = self.game()
        self.play(g, {a: {1}, b: {1, 2}}, players=2)
        self.assertFalse(GameResult.objects.get(game=g, team=b).eligible)

    def test_withdraw_zeroes_points_others_untouched(self):
        a, b = self.team("Alfa"), self.team("Beta")
        g = self.game()
        self.play(g, {a: {1, 2}, b: {1}})
        svc.finalize_game(g, self.tg)
        svc.take_team_out(a, a.captain, reason="Ishtirokni to'xtatdik")
        tot = lambda t: points_total(season=self.season, module=Module.ZAKOVAT, subject_type="team",
                                     subject_id=t.pk)
        self.assertEqual((tot(a), tot(b)), (0, 1))
        standings = svc.season_standings(self.season)
        self.assertEqual(standings[0]["team"], b)
        self.assertIsNone(standings[-1]["place"])

    def test_reopen_only_admin_and_reverses_points(self):
        a = self.team("Alfa")
        g = self.game()
        self.play(g, {a: {1, 2, 3}})
        svc.finalize_game(g, self.tg)
        with self.assertRaises(svc.RuleError):
            svc.reopen_game(g, self.tg, reason="xato")
        admin = User.objects.create(username="adm", is_superuser=True, status=User.Status.ACTIVE)
        svc.reopen_game(g, admin, reason="Hisob xatosi")
        self.assertEqual(points_total(season=self.season, module=Module.ZAKOVAT, subject_type="team",
                                      subject_id=a.pk), 0)
        svc.finalize_game(g, self.tg)
        self.assertEqual(points_total(season=self.season, module=Module.ZAKOVAT, subject_type="team",
                                      subject_id=a.pk), 3)

    def test_season_tie_broken_by_j_total(self):
        a, b, c = self.team("Alfa"), self.team("Beta"), self.team("Gamma")
        g = self.game()
        # hammada 1 ball; 2-savolni faqat B topdi (R=3), 1-savolni A va C (R=2)
        self.play(g, {a: {1}, b: {2}, c: {1}})
        svc.finalize_game(g, self.tg)
        st = svc.season_standings(self.season)
        self.assertEqual(st[0]["team"], b)
        self.assertEqual((st[0]["place"], st[0]["rating_j"], st[0]["tie_group"]), (1, 3, None))
        self.assertEqual({st[1]["team"], st[2]["team"]}, {a, c})
        self.assertEqual(st[1]["tie_group"], st[2]["tie_group"])  # J ham teng → qo'shimcha o'yin kerak
        self.assertIsNotNone(st[1]["tie_group"])

    def test_season_tie_resolved_by_season_tiebreak(self):
        a, b = self.team("Alfa"), self.team("Beta")
        g = self.game()
        self.play(g, {a: {1}, b: {2}})
        svc.finalize_game(g, self.tg)
        st = svc.season_standings(self.season)
        self.assertEqual(st[0]["tie_group"], st[1]["tie_group"])
        tb = svc.create_tiebreak(self.season, self.tg, [a.pk, b.pk], starts_at=aware(2027, 5, 29, 15))
        svc.start_game(tb, self.tg)
        for t in (a, b):
            for u in self.players(t)[:3]:
                svc.add_to_lineup(tb, t, 1, u, self.tg)
        svc.set_mark(tb, a, 1, True, self.tg)
        svc.publish_preliminary(tb, self.tg)
        svc.finalize_game(tb, self.tg)
        st = svc.season_standings(self.season)
        self.assertEqual([r["team"] for r in st], [a, b])
        self.assertEqual([r["place"] for r in st], [1, 2])
