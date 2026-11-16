"""Zakovat API. Barcha holat o'zgarishlari services.py orqali — Nizom qoidalari va ruxsatlar
o'sha yerda tekshiriladi; bu fayl faqat so'rovni o'qiydi va javobni shakllantiradi.

Shaxsiy ma'lumotlar (telefon, email) bu API'da qaytarilmaydi.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from accounts.models import User
from core.models import Season

from . import services as svc
from .models import (
    Appeal, AnswerMark, Game, GameRegistration, GameResult, LineupEntry, Team, TeamMember,
)

RESULTS_VISIBLE = (Game.Status.PRELIMINARY, Game.Status.FINAL)


# ================================================================== yordamchilar

def get_season(request) -> Season:
    sid = request.query_params.get("season")
    if sid:
        return get_object_or_404(Season, pk=sid)
    season = Season.current()
    if season is None:
        raise svc.RuleError("Faol mavsum yo'q.")
    return season


def validated(serializer_cls, data):
    s = serializer_cls(data=data)
    s.is_valid(raise_exception=True)
    return s.validated_data


def user_brief(u: User) -> dict:
    emp = u.employee
    return {"id": u.pk, "name": str(u), "branch": emp.branch.name if emp else None}


def team_brief(t: Team) -> dict:
    return {"id": t.pk, "name": t.name, "status": t.status}


def team_detail(t: Team, viewer) -> dict:
    members = t.members.select_related("user__employee__branch").exclude(
        status__in=[TeamMember.Status.DECLINED])
    can_see_invites = viewer.pk == t.captain_id or svc.is_tg(viewer, t.season)
    return {
        **team_brief(t),
        "season": t.season_id,
        "captain": user_brief(t.captain),
        "status_reason": t.status_reason,
        "members": [
            {"id": m.pk, "user": user_brief(m.user), "status": m.status, "joined_at": m.joined_at}
            for m in members
            if m.status == TeamMember.Status.ACTIVE or (can_see_invites and m.status == TeamMember.Status.INVITED)
        ],
    }


def game_brief(g: Game, my_team=None) -> dict:
    data = {
        "id": g.pk, "title": g.title, "kind": g.kind, "status": g.status,
        "starts_at": g.starts_at, "venue": g.venue, "max_teams": g.max_teams,
        "registration_deadline": g.effective_deadline,
        "rounds": g.rounds, "questions_per_round": g.questions_per_round,
        "hide_standings": g.hide_standings,
        "approved_teams": g.registrations.filter(status=GameRegistration.Status.APPROVED).count(),
    }
    if my_team is not None:
        reg = g.registrations.filter(team=my_team).first()
        data["my_registration"] = None if reg is None else {
            "id": reg.pk, "status": reg.status, "table_number": reg.table_number}
    return data


def results_payload(game: Game) -> dict:
    results = list(GameResult.objects.filter(game=game).select_related("team")
                   .order_by("place", "team__name"))
    marks = {}
    for m in game.marks.all():
        marks.setdefault(m.team_id, {})[m.number] = m.correct
    score = svc.compute(game)
    return {
        "game": game_brief(game),
        "final": game.status == Game.Status.FINAL,
        "question_rating": score.question_rating,
        "rows": [
            {
                "place": r.place, "team": team_brief(r.team), "points": r.points, "rating_j": r.rating_j,
                "eligible": r.eligible, "tie_group": r.tie_group,
                "answers": [marks.get(r.team_id, {}).get(q) for q in range(1, game.total_questions + 1)],
                "counted": sorted(score.teams[r.team_id].counted) if r.team_id in score.teams else [],
            }
            for r in results
        ],
    }


def live_standings(game: Game) -> list:
    score = svc.compute(game)
    names = dict(Team.objects.filter(pk__in=score.teams).values_list("pk", "name"))
    return [{"place": ts.place, "team": {"id": ts.team_id, "name": names[ts.team_id]},
             "points": ts.points, "rating_j": ts.rating_j, "eligible": ts.eligible}
            for ts in score.ranking()]


def appeal_payload(a: Appeal) -> dict:
    return {
        "id": a.pk, "game": a.game_id, "team": team_brief(a.team), "number": a.number,
        "content": a.content, "evidence": a.evidence, "status": a.status,
        "decision_reason": a.decision_reason, "created_at": a.created_at, "decided_at": a.decided_at,
    }


# ================================================================== kirish ma'lumotlari

class NameSer(serializers.Serializer):
    name = serializers.CharField(max_length=100)


class UserIdSer(serializers.Serializer):
    user_id = serializers.IntegerField()


class ReasonSer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True, default="")


class WithdrawSer(serializers.Serializer):
    reason = serializers.CharField()
    disqualify = serializers.BooleanField(default=False)


class AcceptSer(serializers.Serializer):
    accept = serializers.BooleanField()


class DecideSer(serializers.Serializer):
    accept = serializers.BooleanField()
    reason = serializers.CharField()


class RegisterSer(serializers.Serializer):
    team_id = serializers.IntegerField(required=False)


class AppealSer(serializers.Serializer):
    number = serializers.IntegerField(min_value=1)
    content = serializers.CharField()
    evidence = serializers.CharField()


class GameUpdateSer(serializers.Serializer):
    title = serializers.CharField(max_length=150, required=False)
    starts_at = serializers.DateTimeField(required=False)
    venue = serializers.CharField(max_length=200, required=False, allow_blank=True)
    max_teams = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    registration_deadline = serializers.DateTimeField(required=False, allow_null=True)
    rounds = serializers.IntegerField(min_value=1, max_value=10, required=False)
    questions_per_round = serializers.IntegerField(min_value=1, max_value=50, required=False)
    hide_standings = serializers.BooleanField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class GameCreateSer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=[Game.Kind.LEAGUE, Game.Kind.PRACTICE], default=Game.Kind.LEAGUE)
    title = serializers.CharField(max_length=150)
    starts_at = serializers.DateTimeField()
    venue = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    max_teams = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    rounds = serializers.IntegerField(min_value=1, max_value=10, default=3)
    questions_per_round = serializers.IntegerField(min_value=1, max_value=50, default=12)


class ScheduleSer(serializers.Serializer):
    start_time = serializers.TimeField(default="15:00")
    venue = serializers.CharField(required=False, allow_blank=True, default="")
    months = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=12),
                                   required=False, allow_empty=True)


class MarkSer(serializers.Serializer):
    team_id = serializers.IntegerField()
    number = serializers.IntegerField(min_value=1)
    correct = serializers.BooleanField()


class MarksSer(serializers.Serializer):
    marks = MarkSer(many=True)


class NumberSer(serializers.Serializer):
    number = serializers.IntegerField(min_value=1)


class LineupSer(serializers.Serializer):
    team_id = serializers.IntegerField()
    round_no = serializers.IntegerField(min_value=1)
    user_id = serializers.IntegerField()
    from_question = serializers.IntegerField(min_value=1, required=False)


class CopyLineupSer(serializers.Serializer):
    team_id = serializers.IntegerField()
    from_round = serializers.IntegerField(min_value=1)
    to_round = serializers.IntegerField(min_value=1)


class TiebreakSer(serializers.Serializer):
    team_ids = serializers.ListField(child=serializers.IntegerField(), min_length=2)
    starts_at = serializers.DateTimeField()
    questions = serializers.IntegerField(min_value=1, max_value=36, default=6)
    venue = serializers.CharField(required=False, allow_blank=True, default="")


# ================================================================== men (ishtirokchi)

class MeView(APIView):
    """Joriy mavsumdagi jamoam, sardorligim, takliflar, rollarim."""

    def get(self, request):
        season = get_season(request)
        team = svc._user_team(season, request.user)
        invites = TeamMember.objects.filter(season=season, user=request.user,
                                            status=TeamMember.Status.INVITED).select_related("team")
        return Response({
            "season": {"id": season.pk, "name": season.name},
            "team": team_detail(team, request.user) if team else None,
            "is_captain": bool(team and team.captain_id == request.user.pk),
            "invitations": [{"id": m.pk, "team": team_brief(m.team)} for m in invites],
            "is_tg": svc.is_tg(request.user, season),
            "is_scorer": svc.is_scorer(request.user, season),
        })


class InvitationRespondView(APIView):
    def post(self, request, pk):
        member = get_object_or_404(TeamMember, pk=pk)
        if member.user_id != request.user.pk:
            raise PermissionDenied()
        d = validated(AcceptSer, request.data)
        member = svc.respond_invite(member, request.user, d["accept"])
        return Response({"status": member.status})


class PlayersView(APIView):
    """Taklif qilish uchun xodim qidirish. ?q=ism  ?free=1 — jamoasizlar."""

    def get(self, request):
        season = get_season(request)
        q = (request.query_params.get("q") or "").strip()
        busy = set(TeamMember.objects.filter(season=season, status=TeamMember.Status.ACTIVE)
                   .values_list("user_id", flat=True))
        users = (User.objects.filter(status=User.Status.ACTIVE, is_active=True,
                                     employee__isnull=False, employee__is_active=True)
                 .select_related("employee__branch").order_by("employee__full_name"))
        if q:
            users = users.filter(Q(employee__full_name__icontains=q) | Q(display_name__icontains=q))
        if request.query_params.get("free") in ("1", "true"):
            users = users.exclude(pk__in=busy)
        return Response([{**user_brief(u), "has_team": u.pk in busy} for u in users[:50]])


# ================================================================== jamoalar

class TeamViewSet(ViewSet):
    def list(self, request):
        season = get_season(request)
        teams = (Team.objects.filter(season=season)
                 .exclude(status=Team.Status.DRAFT).order_by("name"))
        return Response([{**team_brief(t), "members": t.members.filter(status="active").count()}
                         for t in teams])

    def retrieve(self, request, pk):
        return Response(team_detail(get_object_or_404(Team, pk=pk), request.user))

    def create(self, request):
        d = validated(NameSer, request.data)
        team = svc.create_team(get_season(request), request.user, d["name"])
        return Response(team_detail(team, request.user), status=status.HTTP_201_CREATED)

    def _team(self, pk):
        return get_object_or_404(Team, pk=pk)

    @action(detail=True, methods=["post"])
    def invite(self, request, pk):
        team = self._team(pk)
        d = validated(UserIdSer, request.data)
        member = svc.invite_member(team, request.user, get_object_or_404(User, pk=d["user_id"]))
        return Response({"id": member.pk, "status": member.status}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path=r"members/(?P<member_id>\d+)/remove")
    def remove_member(self, request, pk, member_id):
        member = get_object_or_404(TeamMember, pk=member_id, team_id=pk)
        svc.remove_member(member, request.user)
        return Response(team_detail(member.team, request.user))

    @action(detail=True, methods=["post"])
    def submit(self, request, pk):
        return Response(team_detail(svc.submit_team(self._team(pk), request.user), request.user))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk):
        return Response(team_detail(svc.approve_team(self._team(pk), request.user), request.user))

    @action(detail=True, methods=["post"])
    def rename(self, request, pk):
        d = validated(NameSer, request.data)
        return Response(team_detail(svc.rename_team(self._team(pk), request.user, d["name"]), request.user))

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk):
        d = validated(WithdrawSer, request.data)
        team = svc.take_team_out(self._team(pk), request.user, reason=d["reason"], disqualify=d["disqualify"])
        return Response(team_detail(team, request.user))


# ================================================================== o'yinlar

class GameViewSet(ViewSet):
    def _game(self, pk) -> Game:
        return get_object_or_404(Game.objects.select_related("season"), pk=pk)

    def _require_scorer(self, request, game):
        if not svc.is_scorer(request.user, game.season):
            raise PermissionDenied("Faqat hisob hay'ati va Tashkiliy guruh uchun.")

    # ---------------------------------------------------------- hamma uchun
    def list(self, request):
        season = get_season(request)
        my_team = svc._user_team(season, request.user)
        games = Game.objects.filter(season=season).exclude(status=Game.Status.CANCELLED)
        kind = request.query_params.get("kind")
        if kind:
            games = games.filter(kind=kind)
        return Response([game_brief(g, my_team) for g in games.order_by("starts_at")])

    def retrieve(self, request, pk):
        game = self._game(pk)
        return Response(game_brief(game, svc._user_team(game.season, request.user)))

    @action(detail=True, methods=["get"])
    def results(self, request, pk):
        game = self._game(pk)
        if game.status not in RESULTS_VISIBLE and not svc.is_scorer(request.user, game.season):
            raise svc.RuleError("Natija hali e'lon qilinmagan.")
        if game.status not in RESULTS_VISIBLE:
            return Response({"game": game_brief(game), "final": False, "rows": live_standings(game)})
        return Response(results_payload(game))

    @action(detail=True, methods=["get"])
    def live(self, request, pk):
        """Katta ekran: joriy savol va (yashirilmagan bo'lsa) jonli reyting."""
        game = self._game(pk)
        hidden = game.hide_standings and game.status == Game.Status.IN_PROGRESS
        return Response({
            "game": game_brief(game), "current_round": game.current_round,
            "current_question": game.current_question, "standings_hidden": hidden,
            "standings": [] if hidden else live_standings(game),
        })

    @action(detail=True, methods=["post"])
    def register(self, request, pk):
        game = self._game(pk)
        d = validated(RegisterSer, request.data)
        team = (get_object_or_404(Team, pk=d["team_id"]) if d.get("team_id")
                else svc._user_team(game.season, request.user))
        if team is None:
            raise svc.RuleError("Siz jamoa a'zosi emassiz.")
        reg = svc.register_team(game, team, request.user)
        return Response({"id": reg.pk, "status": reg.status}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def appeals(self, request, pk):
        game = self._game(pk)
        if request.method == "POST":
            team = svc._user_team(game.season, request.user)
            if team is None:
                raise svc.RuleError("Siz jamoa a'zosi emassiz.")
            d = validated(AppealSer, request.data)
            appeal = svc.submit_appeal(game, team, request.user, **d)
            return Response(appeal_payload(appeal), status=status.HTTP_201_CREATED)
        qs = game.appeals.select_related("team")
        if not svc.is_tg(request.user, game.season):
            team = svc._user_team(game.season, request.user)
            qs = qs.filter(team=team) if team else qs.none()
        return Response([appeal_payload(a) for a in qs])

    # ---------------------------------------------------------- Tashkiliy guruh
    def create(self, request):
        season = get_season(request)
        if not svc.is_tg(request.user, season):
            raise PermissionDenied()
        d = validated(GameCreateSer, request.data)
        game = Game.objects.create(season=season, **d)
        svc.log_action(request.user, "zakovat.game_created", game)
        return Response(game_brief(game), status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk):
        d = dict(validated(GameUpdateSer, request.data))
        reason = d.pop("reason", "")
        game = svc.update_game(self._game(pk), request.user, reason=reason, **d)
        return Response(game_brief(game))

    @action(detail=False, methods=["post"], url_path="generate-schedule")
    def generate_schedule(self, request):
        d = validated(ScheduleSer, request.data)
        games = svc.generate_league_schedule(get_season(request), request.user, start_time=d["start_time"],
                                             venue=d["venue"], months=set(d.get("months") or []) or None)
        return Response([game_brief(g) for g in games], status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="open-registration")
    def open_registration(self, request, pk):
        return Response(game_brief(svc.open_registration(self._game(pk), request.user)))

    @action(detail=True, methods=["get"])
    def registrations(self, request, pk):
        game = self._game(pk)
        regs = game.registrations.select_related("team")
        return Response([{"id": r.pk, "team": team_brief(r.team), "status": r.status,
                          "table_number": r.table_number, "created_at": r.created_at} for r in regs])

    @action(detail=True, methods=["post"])
    def start(self, request, pk):
        return Response(game_brief(svc.start_game(self._game(pk), request.user)))

    @action(detail=True, methods=["post"])
    def publish(self, request, pk):
        game = self._game(pk)
        svc.publish_preliminary(game, request.user)
        return Response(results_payload(game))

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk):
        game = self._game(pk)
        svc.finalize_game(game, request.user)
        return Response(results_payload(game))

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk):
        d = validated(ReasonSer, request.data)
        return Response(game_brief(svc.reopen_game(self._game(pk), request.user, reason=d["reason"])))

    @action(detail=True, methods=["post"])
    def tiebreak(self, request, pk):
        game = self._game(pk)
        d = validated(TiebreakSer, request.data)
        tb = svc.create_tiebreak(game.season, request.user, d["team_ids"], starts_at=d["starts_at"],
                                 questions=d["questions"], parent=game, venue=d["venue"])
        return Response(game_brief(tb), status=status.HTTP_201_CREATED)

    # ---------------------------------------------------------- hisob hay'ati
    @action(detail=True, methods=["get"])
    def sheet(self, request, pk):
        """Javoblar jadvali: jamoalar × savollar, tarkib, hisobga olinadigan savollar, jonli ball."""
        game = self._game(pk)
        self._require_scorer(request, game)
        regs = (game.registrations.filter(status=GameRegistration.Status.APPROVED)
                .select_related("team").order_by("table_number"))
        marks = {}
        for m in game.marks.all():
            marks.setdefault(m.team_id, {})[m.number] = m.correct
        lineup = {}
        for e in game.lineup.select_related("user__employee__branch").order_by("round_no", "from_question"):
            lineup.setdefault(e.team_id, []).append(
                {"id": e.pk, "round_no": e.round_no, "user": user_brief(e.user), "from_question": e.from_question})
        score = svc.compute(game)
        return Response({
            "game": game_brief(game), "current_round": game.current_round,
            "current_question": game.current_question,
            "teams": [{
                "table_number": r.table_number, "team": team_brief(r.team),
                "players": [user_brief(m.user) for m in r.team.members.filter(status="active")
                            .select_related("user__employee__branch")],
                "lineup": lineup.get(r.team_id, []),
                "answers": [marks.get(r.team_id, {}).get(q) for q in range(1, game.total_questions + 1)],
                "counted": sorted(score.teams[r.team_id].counted),
                "points": score.teams[r.team_id].points, "rating_j": score.teams[r.team_id].rating_j,
                "place": score.teams[r.team_id].place,
            } for r in regs],
        })

    @action(detail=True, methods=["post"])
    def marks(self, request, pk):
        """Bitta yoki bir nechta belgi: {"marks": [{team_id, number, correct}, ...]}."""
        game = self._game(pk)
        data = request.data if "marks" in request.data else {"marks": [request.data]}
        d = validated(MarksSer, data)
        teams = {t.pk: t for t in Team.objects.filter(pk__in={m["team_id"] for m in d["marks"]})}
        for m in d["marks"]:
            team = teams.get(m["team_id"])
            if team is None:
                raise svc.RuleError(f"Jamoa topilmadi: {m['team_id']}")
            svc.set_mark(game, team, m["number"], m["correct"], request.user)
        return Response({"saved": len(d["marks"])})

    @action(detail=True, methods=["post"])
    def current(self, request, pk):
        d = validated(NumberSer, request.data)
        game = svc.set_current_question(self._game(pk), request.user, d["number"])
        return Response({"current_round": game.current_round, "current_question": game.current_question})

    @action(detail=True, methods=["post"])
    def lineup(self, request, pk):
        game = self._game(pk)
        d = validated(LineupSer, request.data)
        entry = svc.add_to_lineup(game, get_object_or_404(Team, pk=d["team_id"]), d["round_no"],
                                  get_object_or_404(User, pk=d["user_id"]), request.user,
                                  from_question=d.get("from_question"))
        return Response({"id": entry.pk, "from_question": entry.from_question}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path=r"lineup/(?P<entry_id>\d+)/remove")
    def lineup_remove(self, request, pk, entry_id):
        svc.remove_from_lineup(get_object_or_404(LineupEntry, pk=entry_id, game_id=pk), request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="lineup/copy")
    def lineup_copy(self, request, pk):
        d = validated(CopyLineupSer, request.data)
        n = svc.copy_lineup(self._game(pk), get_object_or_404(Team, pk=d["team_id"]),
                            d["from_round"], d["to_round"], request.user)
        return Response({"copied": n})


class RegistrationApproveView(APIView):
    def post(self, request, pk):
        reg = svc.approve_registration(get_object_or_404(GameRegistration, pk=pk), request.user)
        return Response({"id": reg.pk, "status": reg.status, "table_number": reg.table_number})


class AppealDecideView(APIView):
    def post(self, request, pk):
        d = validated(DecideSer, request.data)
        appeal = svc.decide_appeal(get_object_or_404(Appeal, pk=pk), request.user, **d)
        return Response(appeal_payload(appeal))


# ================================================================== mavsum reytingi

class StandingsView(APIView):
    def get(self, request):
        season = get_season(request)
        bd = svc.season_breakdown(season)
        empty = {"by_game": {}, "other_points": 0, "played": 0, "wins": 0, "best": 0}
        rows = []
        for r in svc.season_standings(season):
            d = bd["teams"].get(r["team"].pk, empty)
            rows.append({
                "place": r["place"], "team": team_brief(r["team"]), "points": r["points"],
                "rating_j": r["rating_j"], "tie_group": r["tie_group"],
                "prev_place": bd["prev_places"].get(r["team"].pk),
                "by_game": {str(k): v for k, v in d["by_game"].items()},
                "other_points": d["other_points"], "played": d["played"], "wins": d["wins"], "best": d["best"],
            })
        return Response({
            "season": {"id": season.pk, "name": season.name},
            "games": [{"id": g.pk, "title": g.title, "starts_at": g.starts_at} for g in bd["games"]],
            "rows": rows,
        })


class SeasonTiebreakView(APIView):
    def post(self, request):
        season = get_season(request)
        d = validated(TiebreakSer, request.data)
        tb = svc.create_tiebreak(season, request.user, d["team_ids"], starts_at=d["starts_at"],
                                 questions=d["questions"], venue=d["venue"])
        return Response(game_brief(tb), status=status.HTTP_201_CREATED)
