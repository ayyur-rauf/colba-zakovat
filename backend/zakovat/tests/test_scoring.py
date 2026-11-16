from django.test import SimpleTestCase

from zakovat import scoring


def full_lineup(team_ids, rounds=3, players=4, qpr=12):
    return [(t, r, (r - 1) * qpr + 1) for t in team_ids for r in range(1, rounds + 1) for _ in range(players)]


class ScoringTests(SimpleTestCase):
    def score(self, teams, correct, lineup=None, total=6, qpr=6):
        marks = {(t, q): True for t, qs in correct.items() for q in qs}
        lineup = lineup if lineup is not None else full_lineup(teams, rounds=total // qpr, qpr=qpr)
        return scoring.score_game(teams, marks, lineup, total_questions=total, questions_per_round=qpr)

    def test_points_and_question_rating(self):
        # 3 jamoa, 6 savol. 1-savolni hamma topdi (N=0, R=1), 2-savolni faqat A (N=2, R=3)
        s = self.score([1, 2, 3], {1: {1, 2}, 2: {1, 3}, 3: {1}})
        self.assertEqual(s.question_rating[1], 1)
        self.assertEqual(s.question_rating[2], 3)
        self.assertEqual(s.question_rating[3], 3)
        self.assertEqual(s.question_rating[4], 4)  # hech kim topmadi
        self.assertEqual((s.teams[1].points, s.teams[1].rating_j), (2, 4))
        self.assertEqual((s.teams[2].points, s.teams[2].rating_j), (2, 4))
        self.assertEqual(s.teams[3].points, 1)

    def test_tie_broken_by_j(self):
        # A: 1,2 ; B: 1,3 ; C: 2 ; D: hech narsa. 2-savolni 2 jamoa (R=3), 3-savolni 1 jamoa (R=4)
        s = self.score([1, 2, 3, 4], {1: {1, 2}, 2: {1, 3}, 3: {2}, 4: set()})
        self.assertEqual(s.teams[2].place, 1)  # B: R(1)=3 + R(3)=4 = 7
        self.assertEqual(s.teams[1].place, 2)  # A: 3 + 3 = 6
        self.assertIsNone(s.teams[1].tie_group)

    def test_full_tie_creates_group(self):
        s = self.score([1, 2, 3], {1: {1}, 2: {1}, 3: set()})
        self.assertEqual(s.teams[1].place, 1)
        self.assertEqual(s.teams[2].place, 1)
        self.assertEqual(s.teams[1].tie_group, s.teams[2].tie_group)
        self.assertIsNotNone(s.teams[1].tie_group)
        self.assertEqual(s.teams[3].place, 3)

    def test_fewer_than_three_players_not_counted(self):
        lineup = full_lineup([1]) + [(2, 1, 1), (2, 1, 1)]  # 2-jamoada faqat 2 o'yinchi
        s = self.score([1, 2], {1: {1}, 2: {1, 2}}, lineup=lineup)
        self.assertFalse(s.teams[2].eligible)
        self.assertEqual(s.teams[2].points, 0)
        self.assertIsNone(s.teams[2].place)
        # N faqat reytingdagi jamoalar orasida: 1-savolni yagona reytingdagi jamoa topdi
        self.assertEqual(s.question_rating[1], 1)

    def test_third_player_joins_mid_round(self):
        # 2 o'yinchi boshidan, 3-o'yinchi 4-savoldan — 1..3 savollar hisobga olinmaydi
        lineup = [(1, 1, 1), (1, 1, 1), (1, 1, 4)]
        s = self.score([1], {1: {1, 2, 4, 5}}, lineup=lineup)
        self.assertEqual(s.teams[1].counted, {4, 5, 6})
        self.assertEqual(s.teams[1].points, 2)

    def test_lineup_per_round(self):
        # 2 raund × 3 savol; jamoa 2-raundga faqat 2 kishi bilan qoldi
        lineup = [(1, 1, 1)] * 3 + [(1, 2, 4)] * 2
        s = self.score([1], {1: {1, 4}}, lineup=lineup, total=6, qpr=3)
        self.assertEqual(s.teams[1].counted, {1, 2, 3})
        self.assertEqual(s.teams[1].points, 1)

    def test_tiebreak_groups(self):
        tb = self.score([1, 2, 3], {1: {1, 2}, 2: {1}, 3: {1}})
        self.assertEqual(scoring.apply_tiebreak([2, 3, 1], tb), [[1], [2, 3]])

    def test_nizom_example_formula(self):
        # 10 jamoa, 5-savolni 2 jamoa topdi → N=8, R=9
        teams = list(range(1, 11))
        s = self.score(teams, {1: {5}, 2: {5}}, total=6, qpr=6)
        self.assertEqual(s.question_rating[5], 9)
