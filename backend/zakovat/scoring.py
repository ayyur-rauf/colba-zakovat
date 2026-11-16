"""O'yin natijasini hisoblash. Bazaga bog'liq emas — toza funksiyalar.

Qoidalar:
- [N-6.1] har to'g'ri javob — 1 ball.
- [N-3.6, N-4.3] savol jamoa uchun hisobga olinadi, agar shu savolda jamoaning kamida
  3 o'yinchisi ishtirok etgan bo'lsa. O'yinchi raund tarkibida bo'lsa va `from_question`
  dan boshlab ishtirok etadi. Birorta ham savoli hisobga olinmagan jamoa reytingga kirmaydi.
- [N-8.2] savol reytingi R = N + 1, N — savolga to'g'ri javob bera olmagan jamoalar soni.
  N faqat reytingga kirgan jamoalar orasida sanaladi; hisobga olinmagan savoli bo'lgan
  jamoa o'sha savolga "javob bera olmagan" deb sanaladi.
- [N-8.3] jamoa reytingi J = to'g'ri javob bergan savollari R larining yig'indisi.
- [N-8.1] o'rinlar: avval ball, keyin J. Ikkalasi ham teng bo'lsa — teng guruh,
  qo'shimcha o'yin bilan hal qilinadi.
"""
from collections import defaultdict
from dataclasses import dataclass, field

MIN_PLAYERS = 3


@dataclass
class TeamScore:
    team_id: int
    points: int = 0
    rating_j: int = 0
    eligible: bool = False
    correct: set = field(default_factory=set)
    counted: set = field(default_factory=set)
    place: int | None = None
    tie_group: int | None = None


@dataclass
class GameScore:
    teams: dict  # team_id -> TeamScore
    question_rating: dict  # savol raqami -> R

    def ranking(self) -> list[TeamScore]:
        ranked = [t for t in self.teams.values() if t.eligible]
        ranked.sort(key=lambda t: (t.place, t.team_id))
        return ranked + [t for t in self.teams.values() if not t.eligible]


def counted_questions(lineup, *, total_questions, questions_per_round, min_players=MIN_PLAYERS):
    """lineup: [(team_id, round_no, from_question), ...] → {team_id: {hisobga olinadigan savollar}}."""
    present = defaultdict(int)  # (team, q) -> o'yinchilar soni
    for team_id, round_no, from_q in lineup:
        first = (round_no - 1) * questions_per_round + 1
        last = min(round_no * questions_per_round, total_questions)
        for q in range(max(first, from_q), last + 1):
            present[(team_id, q)] += 1
    result = defaultdict(set)
    for (team_id, q), n in present.items():
        if n >= min_players:
            result[team_id].add(q)
    return result


def score_game(team_ids, marks, lineup, *, total_questions, questions_per_round,
               min_players=MIN_PLAYERS) -> GameScore:
    """marks: {(team_id, savol): bool}; lineup: [(team_id, raund, from_question)]."""
    counted = counted_questions(lineup, total_questions=total_questions,
                                questions_per_round=questions_per_round, min_players=min_players)
    teams = {}
    for t in team_ids:
        ts = TeamScore(team_id=t, counted=counted.get(t, set()))
        ts.eligible = bool(ts.counted)
        ts.correct = {q for q in ts.counted if marks.get((t, q))}
        ts.points = len(ts.correct)
        teams[t] = ts

    eligible = [ts for ts in teams.values() if ts.eligible]
    rating = {}
    for q in range(1, total_questions + 1):
        n_failed = sum(1 for ts in eligible if q not in ts.correct)
        rating[q] = n_failed + 1
    for ts in eligible:
        ts.rating_j = sum(rating[q] for q in ts.correct)

    assign_places(eligible)
    return GameScore(teams=teams, question_rating=rating)


def assign_places(scores, key=lambda t: (t.points, t.rating_j)):
    """O'rinlarni beradi (1, 2, 2, 4 tartibida). Kaliti teng jamoalar teng guruhga tushadi."""
    ordered = sorted(scores, key=lambda t: tuple(-x for x in key(t)))
    group_no = 0
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and key(ordered[j + 1]) == key(ordered[i]):
            j += 1
        tie = j > i
        if tie:
            group_no += 1
        for k in range(i, j + 1):
            ordered[k].place = i + 1
            ordered[k].tie_group = group_no if tie else None
        i = j + 1
    return ordered


def apply_tiebreak(group_team_ids, tiebreak_score: GameScore) -> list[list[int]]:
    """Qo'shimcha o'yin natijasi bo'yicha teng guruh ichidagi tartib.

    Qaytaradi: guruhlar ro'yxati, masalan [[A], [B, C]] — B va C hamon teng.
    Qo'shimcha o'yinda hisobga olinmagan jamoa oxiriga tushadi.
    """
    def key(t):
        ts = tiebreak_score.teams.get(t)
        if ts is None or not ts.eligible:
            return (-1, -1)
        return (ts.points, ts.rating_j)

    ordered = sorted(group_team_ids, key=lambda t: tuple(-x for x in key(t)))
    groups = []
    for t in ordered:
        if groups and key(groups[-1][0]) == key(t):
            groups[-1].append(t)
        else:
            groups.append([t])
    return groups
