"""Zakovat qoidalari xizmati. Har bir funksiya Nizom qoidasini va ruxsatni tekshiradi.

Xato bo'lsa `RuleError` (foydalanuvchiga ko'rsatiladigan matn bilan) ko'tariladi.
`now` parametri — testlar uchun; odatda berilmaydi.
"""
import calendar
from datetime import date, datetime, time, timedelta

import django.dispatch
from django.db import IntegrityError, transaction
from django.db.models import Max, Sum
from django.utils import timezone

from core.api import RuleError as BaseRuleError
from core.models import Module, PointsEntry, Role
from core.services import add_points, has_role, log_action, points_by_subject, points_total

from . import scoring
from .models import (
    Appeal, AnswerMark, Game, GameQuestion, GameRegistration, GameResult, LineupEntry, Question,
    Team, TeamMember, team_name_key,
)

MIN_TEAM, MAX_TEAM = 4, 8        # [N-3.2]
MAX_ON_STAGE = 6                 # [N-5.2]
CHANGE_NOTICE = timedelta(days=1)  # [N-1.4]
POINTS_REASON = "zakovat.game"
OUT_REASON = "zakovat.team_out"

game_changed = django.dispatch.Signal()  # kwargs: game, changes, actor — bildirishnomalar uchun


class RuleError(BaseRuleError):
    pass


def _now(now):
    return now or timezone.now()


# ------------------------------------------------------------------ ruxsatlar

def is_tg(user, season) -> bool:
    return has_role(user, Role.TG_MEMBER, Module.ZAKOVAT, season)


def is_scorer(user, season) -> bool:
    return is_tg(user, season) or has_role(user, Role.SCORER, Module.ZAKOVAT, season)


def is_admin(user) -> bool:
    return has_role(user, Role.ADMIN)


def _require(cond, msg="Bu amal uchun ruxsatingiz yo'q."):
    if not cond:
        raise RuleError(msg)


def season_started(season, now=None) -> bool:
    return timezone.localdate(_now(now)) >= season.start_date


# ------------------------------------------------------------------ jamoalar

def _active_members(team):
    return team.members.filter(status=TeamMember.Status.ACTIVE)


def _user_team(season, user):
    m = (TeamMember.objects.filter(season=season, user=user, status=TeamMember.Status.ACTIVE)
         .select_related("team").first())
    return m.team if m else None


def _roster_locked(team, now=None) -> bool:
    """[N-3.5] mavsum boshlangach faol jamoa tarkibi qulflanadi."""
    return team.status == Team.Status.ACTIVE and season_started(team.season, now)


@transaction.atomic
def create_team(season, captain, name, *, now=None) -> Team:
    _require(captain.can_login, "Akkaunt faol emas.")
    if _user_team(season, captain):
        raise RuleError("Siz bu mavsumda boshqa jamoa a'zosisiz [N-3.2].")
    if Team.objects.filter(season=season, name_key=team_name_key(name)).exists():
        raise RuleError("Bu nomli jamoa allaqachon bor. Boshqa nom tanlang [N-3.3].")
    team = Team.objects.create(season=season, name=name, captain=captain)
    TeamMember.objects.create(team=team, user=captain, status=TeamMember.Status.ACTIVE,
                              joined_at=_now(now))
    log_action(captain, "zakovat.team_created", team, after={"name": team.name})
    return team


@transaction.atomic
def invite_member(team, actor, user, *, now=None) -> TeamMember:
    tg = is_tg(actor, team.season)
    _require(actor.pk == team.captain_id or tg)
    if team.is_out:
        raise RuleError("Jamoa musobaqadan chiqqan.")
    if _roster_locked(team, now) and not tg:
        raise RuleError("Mavsum davomida tarkibni faqat Tashkiliy guruh o'zgartiradi [N-3.5].")
    if not user.can_login:
        raise RuleError("Bu xodimning akkaunti faol emas.")
    if _user_team(team.season, user):
        raise RuleError("Bu xodim boshqa jamoa a'zosi [N-3.2].")
    if _active_members(team).count() >= MAX_TEAM:
        raise RuleError(f"Jamoada ko'pi bilan {MAX_TEAM} o'yinchi bo'ladi [N-3.2].")
    member, _ = TeamMember.objects.update_or_create(
        team=team, user=user, status=TeamMember.Status.INVITED, defaults={})
    log_action(actor, "zakovat.member_invited", member)
    return member


@transaction.atomic
def respond_invite(member, user, accept: bool, *, now=None) -> TeamMember:
    _require(member.user_id == user.pk)
    if member.status != TeamMember.Status.INVITED:
        raise RuleError("Taklif faol emas.")
    if not accept:
        member.status = TeamMember.Status.DECLINED
        member.save(update_fields=["status"])
        return member
    if _user_team(member.team.season, user):
        raise RuleError("Siz boshqa jamoa a'zosisiz. Avval undan chiqing [N-3.2].")
    if _active_members(member.team).count() >= MAX_TEAM:
        raise RuleError(f"Jamoa to'lgan ({MAX_TEAM} o'yinchi) [N-3.2].")
    member.status = TeamMember.Status.ACTIVE
    member.joined_at = _now(now)
    member.save(update_fields=["status", "joined_at"])
    # boshqa jamoalardan kelgan takliflar bekor bo'ladi
    TeamMember.objects.filter(season=member.season, user=user, status=TeamMember.Status.INVITED) \
        .update(status=TeamMember.Status.DECLINED)
    log_action(user, "zakovat.member_joined", member)
    return member


@transaction.atomic
def remove_member(member, actor, *, now=None) -> TeamMember:
    team = member.team
    tg = is_tg(actor, team.season)
    _require(actor.pk in (team.captain_id, member.user_id) or tg)
    if member.user_id == team.captain_id:
        raise RuleError("Sardor jamoadan chiqa olmaydi. Avval sardorlikni boshqaga bering.")
    if _roster_locked(team, now) and not tg:
        raise RuleError("Mavsum davomida tarkibni faqat Tashkiliy guruh o'zgartiradi [N-3.5].")
    member.status = TeamMember.Status.LEFT
    member.left_at = _now(now)
    member.save(update_fields=["status", "left_at"])
    log_action(actor, "zakovat.member_removed", member)
    return member


def _check_size(team):
    n = _active_members(team).count()
    if not MIN_TEAM <= n <= MAX_TEAM:
        raise RuleError(f"Jamoada {MIN_TEAM} dan {MAX_TEAM} gacha o'yinchi bo'lishi kerak, hozir {n} ta [N-3.2].")


@transaction.atomic
def submit_team(team, actor) -> Team:
    _require(actor.pk == team.captain_id)
    if team.status != Team.Status.DRAFT:
        raise RuleError("Jamoa allaqachon yuborilgan.")
    _check_size(team)
    team.status = Team.Status.PENDING
    team.save(update_fields=["status"])
    log_action(actor, "zakovat.team_submitted", team)
    return team


@transaction.atomic
def approve_team(team, actor, *, now=None) -> Team:
    _require(is_tg(actor, team.season))
    if team.status != Team.Status.PENDING:
        raise RuleError("Faqat tasdiq kutayotgan jamoani tasdiqlash mumkin.")
    _check_size(team)
    team.status = Team.Status.ACTIVE
    team.approved_by = actor
    team.approved_at = _now(now)
    team.save(update_fields=["status", "approved_by", "approved_at"])
    log_action(actor, "zakovat.team_approved", team)
    return team


@transaction.atomic
def rename_team(team, actor, new_name, *, now=None) -> Team:
    _require(actor.pk == team.captain_id or is_tg(actor, team.season))
    if team.status not in (Team.Status.DRAFT, Team.Status.PENDING) and season_started(team.season, now):
        raise RuleError("Mavsum davomida jamoa nomini o'zgartirib bo'lmaydi [N-3.4].")
    old = team.name
    team.name = new_name
    try:
        with transaction.atomic():
            team.save()
    except IntegrityError:
        raise RuleError("Bu nomli jamoa allaqachon bor [N-3.3].")
    log_action(actor, "zakovat.team_renamed", team, before={"name": old}, after={"name": team.name})
    return team


@transaction.atomic
def take_team_out(team, actor, *, reason, disqualify=False, now=None) -> Team:
    """[N-3.7–3.9] Jamoa chiqadi yoki chetlatiladi: mavsumdagi barcha ballari nolga tushadi,
    boshqa jamoalarniki qayta hisoblanmaydi."""
    if disqualify:
        _require(is_tg(actor, team.season))
    else:
        _require(actor.pk == team.captain_id or is_tg(actor, team.season))
    if team.is_out:
        raise RuleError("Jamoa allaqachon chiqqan.")
    if not reason.strip():
        raise RuleError("Sababini yozing.")
    team.status = Team.Status.DISQUALIFIED if disqualify else Team.Status.WITHDRAWN
    team.status_reason = reason.strip()
    team.save(update_fields=["status", "status_reason"])
    total = points_total(season=team.season, module=Module.ZAKOVAT,
                         subject_type=PointsEntry.Subject.TEAM, subject_id=team.pk)
    add_points(season=team.season, module=Module.ZAKOVAT, subject_type=PointsEntry.Subject.TEAM,
               subject_id=team.pk, amount=-total, reason_type=OUT_REASON, reason_id=team.pk,
               note=f"{team.get_status_display()}: {reason}"[:300], actor=actor)
    # kelgusi o'yinlarga arizalar bekor qilinadi
    GameRegistration.objects.filter(team=team, game__starts_at__gt=_now(now)).exclude(
        status=GameRegistration.Status.WITHDRAWN).update(status=GameRegistration.Status.WITHDRAWN)
    log_action(actor, "zakovat.team_out", team, after={"status": team.status, "zeroed": total},
               note=reason)
    return team


# ------------------------------------------------------------------ o'yinlar jadvali

def third_saturday(year: int, month: int) -> date:
    first_weekday, _ = calendar.monthrange(year, month)  # 0 = dushanba
    first_saturday = 1 + (calendar.SATURDAY - first_weekday) % 7
    return date(year, month, first_saturday + 14)


@transaction.atomic
def generate_league_schedule(season, actor, *, start_time=time(15, 0), venue="", months=None):
    """[N-1.2] mavsum oralig'idagi har oyning 3-shanbasiga liga o'yini yaratadi.

    months — faqat shu oylar (masalan {9,10,11,12,1,2,3,4,5}); bo'sh bo'lsa — hammasi.
    Shu sanada liga o'yini bo'lsa, qayta yaratilmaydi.
    """
    _require(is_tg(actor, season))
    created = []
    y, m = season.start_date.year, season.start_date.month
    while (y, m) <= (season.end_date.year, season.end_date.month):
        d = third_saturday(y, m)
        if season.start_date <= d <= season.end_date and (not months or m in months):
            starts = timezone.make_aware(datetime.combine(d, start_time))
            exists = Game.objects.filter(season=season, kind=Game.Kind.LEAGUE,
                                         starts_at__date=d).exists()
            if not exists:
                n = Game.objects.filter(season=season, kind=Game.Kind.LEAGUE).count() + 1
                created.append(Game.objects.create(
                    season=season, kind=Game.Kind.LEAGUE, title=f"{n}-tur", starts_at=starts, venue=venue))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    if created:
        log_action(actor, "zakovat.schedule_generated", note=f"{len(created)} ta o'yin")
    return created


@transaction.atomic
def update_game(game, actor, *, reason="", now=None, **changes) -> Game:
    """Sana, vaqt, joy va h.k. o'zgarishi. [N-1.4] o'yinga 1 kundan kam qolganda sababi majburiy."""
    _require(is_tg(actor, game.season))
    if game.status in (Game.Status.FINAL, Game.Status.CANCELLED) and set(changes) != {"hide_standings"}:
        raise RuleError("Yakunlangan yoki bekor qilingan o'yinni o'zgartirib bo'lmaydi.")
    allowed = {"title", "starts_at", "venue", "max_teams", "registration_deadline", "rounds",
               "questions_per_round", "hide_standings"}
    bad = set(changes) - allowed
    if bad:
        raise RuleError(f"Bu maydonlarni o'zgartirib bo'lmaydi: {', '.join(sorted(bad))}")
    if {"rounds", "questions_per_round"} & set(changes) and game.marks.exists():
        raise RuleError("Javoblar kiritilgan o'yinda savollar sonini o'zgartirib bo'lmaydi.")
    before = {k: str(getattr(game, k)) for k in changes}
    notice_fields = {"starts_at", "venue"} & set(changes)
    late = game.starts_at - _now(now) < CHANGE_NOTICE
    if notice_fields and late and not reason.strip():
        raise RuleError("O'yinga 1 kundan kam qoldi. O'zgartirish sababini yozing [N-1.4].")
    for k, v in changes.items():
        setattr(game, k, v)
    game.save()
    log_action(actor, "zakovat.game_updated", game, before=before,
               after={k: str(v) for k, v in changes.items()}, note=reason)
    if notice_fields:
        transaction.on_commit(lambda: game_changed.send(
            sender=Game, game=game, changes=sorted(notice_fields), actor=actor, late=late))
    return game


# ------------------------------------------------------------------ ro'yxatdan o'tish

@transaction.atomic
def open_registration(game, actor) -> Game:
    _require(is_tg(actor, game.season))
    if game.status != Game.Status.PLANNED:
        raise RuleError("Ro'yxatdan o'tishni faqat rejalashtirilgan o'yinda ochish mumkin.")
    game.status = Game.Status.REGISTRATION
    game.save(update_fields=["status"])
    log_action(actor, "zakovat.registration_opened", game)
    return game


@transaction.atomic
def register_team(game, team, actor, *, now=None) -> GameRegistration:
    tg = is_tg(actor, game.season)
    _require(actor.pk == team.captain_id or tg)
    if team.season_id != game.season_id:
        raise RuleError("Jamoa boshqa mavsumga tegishli.")
    if team.status != Team.Status.ACTIVE:
        raise RuleError("Jamoa Tashkiliy guruh tomonidan tasdiqlanmagan [N-3.1].")
    if game.status != Game.Status.REGISTRATION:
        raise RuleError("Bu o'yinga ro'yxatdan o'tish ochiq emas.")
    if _now(now) > game.effective_deadline and not tg:
        raise RuleError("Ro'yxatdan o'tish muddati tugagan (o'yindan 1 kun oldin) [N-3.2].")
    _check_size(team)
    taken = game.registrations.filter(
        status__in=[GameRegistration.Status.PENDING, GameRegistration.Status.APPROVED]).count()
    full = game.max_teams is not None and taken >= game.max_teams
    reg, created = GameRegistration.objects.get_or_create(game=game, team=team)
    if not created and reg.status not in (GameRegistration.Status.WITHDRAWN, GameRegistration.Status.REJECTED):
        raise RuleError("Jamoa bu o'yinga allaqachon ro'yxatdan o'tgan.")
    reg.status = GameRegistration.Status.WAITLIST if full else GameRegistration.Status.PENDING
    reg.save(update_fields=["status"])
    log_action(actor, "zakovat.registered", reg, after={"status": reg.status})
    return reg


@transaction.atomic
def approve_registration(reg, actor) -> GameRegistration:
    game = reg.game
    _require(is_tg(actor, game.season))
    if reg.status not in (GameRegistration.Status.PENDING, GameRegistration.Status.WAITLIST):
        raise RuleError("Bu arizani tasdiqlab bo'lmaydi.")
    approved = game.registrations.filter(status=GameRegistration.Status.APPROVED)
    if game.max_teams is not None and approved.count() >= game.max_teams:
        raise RuleError(f"O'yinda joy qolmagan ({game.max_teams} ta jamoa) [N-4.1].")
    reg.status = GameRegistration.Status.APPROVED
    reg.table_number = (approved.aggregate(m=Max("table_number"))["m"] or 0) + 1
    reg.save(update_fields=["status", "table_number"])
    log_action(actor, "zakovat.registration_approved", reg)
    return reg


def _approved_team_ids(game):
    return list(game.registrations.filter(status=GameRegistration.Status.APPROVED)
                .values_list("team_id", flat=True))


# ------------------------------------------------------------------ o'yin kuni

@transaction.atomic
def start_game(game, actor) -> Game:
    _require(is_tg(actor, game.season))
    if game.status not in (Game.Status.PLANNED, Game.Status.REGISTRATION):
        raise RuleError("O'yin allaqachon boshlangan yoki yakunlangan.")
    if not _approved_team_ids(game):
        raise RuleError("Tasdiqlangan jamoa yo'q.")
    game.status = Game.Status.IN_PROGRESS
    game.current_round, game.current_question = 1, 1
    game.save(update_fields=["status", "current_round", "current_question"])
    log_action(actor, "zakovat.game_started", game)
    return game


@transaction.atomic
def set_current_question(game, actor, number) -> Game:
    """Boshlovchi yoki sekundant joriy savolni belgilaydi (katta ekran va tarkib qulfi uchun)."""
    _require(is_scorer(actor, game.season) or has_role(actor, Role.HOST, Module.ZAKOVAT, game.season)
             or has_role(actor, Role.SECOND, Module.ZAKOVAT, game.season))
    if game.status != Game.Status.IN_PROGRESS:
        raise RuleError("O'yin ketmayapti.")
    if not 1 <= number <= game.total_questions:
        raise RuleError("Savol raqami noto'g'ri.")
    game.current_question = number
    game.current_round = game.round_of(number)
    game.save(update_fields=["current_question", "current_round"])
    return game


def _round_started(game, round_no) -> bool:
    if game.status != Game.Status.IN_PROGRESS:
        return game.status in (Game.Status.PRELIMINARY, Game.Status.FINAL)
    return game.current_question >= game.first_question_of(round_no)


@transaction.atomic
def add_to_lineup(game, team, round_no, user, actor, *, from_question=None) -> LineupEntry:
    """Raund tarkibiga o'yinchi qo'shadi.

    - [N-5.2] bir raundda ko'pi bilan 6 o'yinchi; almashtirish faqat raundlar orasida.
    - [N-4.3] raund boshlangach kelgan o'yinchi joriy savoldan boshlab qo'shiladi
      (bu almashtirish emas — tarkib 6 tadan oshmasligi kerak).
    """
    _require(is_scorer(actor, game.season))
    if game.status in (Game.Status.PRELIMINARY, Game.Status.FINAL, Game.Status.CANCELLED):
        raise RuleError("O'yin yakunlangan.")
    if not 1 <= round_no <= game.rounds:
        raise RuleError("Raund raqami noto'g'ri.")
    if team.pk not in _approved_team_ids(game):
        raise RuleError("Jamoa bu o'yinga tasdiqlanmagan.")
    if not TeamMember.objects.filter(team=team, user=user, status=TeamMember.Status.ACTIVE).exists():
        raise RuleError("O'yinchi jamoa ro'yxatida yo'q [N-3.2].")
    if LineupEntry.objects.filter(game=game, team=team, round_no=round_no).count() >= MAX_ON_STAGE:
        raise RuleError(f"Bir vaqtda ko'pi bilan {MAX_ON_STAGE} o'yinchi o'ynaydi [N-5.2].")
    first = game.first_question_of(round_no)
    last = first + game.questions_per_round - 1
    if _round_started(game, round_no):
        if game.current_question > last:
            raise RuleError("Bu raund tugagan.")
        earliest = game.current_question
    else:
        earliest = first
    fq = from_question or earliest
    if not earliest <= fq <= last:
        raise RuleError(f"O'yinchi {earliest}–{last}-savollar oralig'idan qo'shilishi mumkin.")
    try:
        with transaction.atomic():
            entry = LineupEntry.objects.create(game=game, team=team, round_no=round_no, user=user,
                                               from_question=fq, created_by=actor)
    except IntegrityError:
        raise RuleError("O'yinchi bu raund tarkibida allaqachon bor.")
    log_action(actor, "zakovat.lineup_added", entry,
               after={"team": team.pk, "round": round_no, "user": user.pk, "from": fq})
    return entry


@transaction.atomic
def remove_from_lineup(entry, actor) -> None:
    game = entry.game
    _require(is_scorer(actor, game.season))
    if _round_started(game, entry.round_no):
        raise RuleError("Raund boshlangan — almashtirish faqat raundlar orasida [N-5.2].")
    log_action(actor, "zakovat.lineup_removed", entry,
               before={"team": entry.team_id, "round": entry.round_no, "user": entry.user_id})
    entry.delete()


@transaction.atomic
def copy_lineup(game, team, from_round, to_round, actor) -> int:
    """Oldingi raund tarkibini keyingi raundga ko'chiradi (tez kiritish uchun)."""
    n = 0
    for e in LineupEntry.objects.filter(game=game, team=team, round_no=from_round):
        if not LineupEntry.objects.filter(game=game, team=team, round_no=to_round, user=e.user).exists():
            add_to_lineup(game, team, to_round, e.user, actor)
            n += 1
    return n


@transaction.atomic
def set_mark(game, team, number, correct: bool, actor) -> AnswerMark:
    """Hisob hay'ati belgisi. Dastlabki natija e'lon qilingach — faqat apellyatsiya orqali [N-6.4]."""
    _require(is_scorer(actor, game.season))
    if game.status != Game.Status.IN_PROGRESS:
        raise RuleError("Belgilarni faqat o'yin davomida kiritish mumkin. "
                        "Natija e'lon qilingach — apellyatsiya orqali [N-6.4].")
    if not 1 <= number <= game.total_questions:
        raise RuleError("Savol raqami noto'g'ri.")
    if team.pk not in _approved_team_ids(game):
        raise RuleError("Jamoa bu o'yinga tasdiqlanmagan.")
    mark = AnswerMark.objects.filter(game=game, team=team, number=number).first()
    if mark is None:
        mark = AnswerMark.objects.create(game=game, team=team, number=number, correct=correct,
                                         updated_by=actor)
    elif mark.correct != correct:
        log_action(actor, "zakovat.mark_changed", mark, before={"correct": mark.correct},
                   after={"correct": correct}, note=f"jamoa {team.pk}, {number}-savol")
        mark.correct = correct
        mark.updated_by = actor
        mark.save(update_fields=["correct", "updated_by", "updated_at"])
    return mark


# ------------------------------------------------------------------ hisoblash va natijalar

def compute(game) -> scoring.GameScore:
    marks = {(m.team_id, m.number): m.correct for m in game.marks.all()}
    lineup = list(game.lineup.values_list("team_id", "round_no", "from_question"))
    return scoring.score_game(_approved_team_ids(game), marks, lineup,
                              total_questions=game.total_questions,
                              questions_per_round=game.questions_per_round)


def _save_results(game, score):
    GameResult.objects.filter(game=game).exclude(team_id__in=score.teams.keys()).delete()
    for ts in score.teams.values():
        GameResult.objects.update_or_create(
            game=game, team_id=ts.team_id,
            defaults={"points": ts.points, "rating_j": ts.rating_j, "eligible": ts.eligible,
                      "place": ts.place, "tie_group": ts.tie_group})


@transaction.atomic
def publish_preliminary(game, actor) -> scoring.GameScore:
    """[N-7.2] dastlabki natija e'lon qilinadi — apellyatsiya oynasi ochiladi."""
    _require(is_tg(actor, game.season))
    if game.status != Game.Status.IN_PROGRESS:
        raise RuleError("Dastlabki natijani faqat o'yin davomida e'lon qilish mumkin.")
    score = compute(game)
    _save_results(game, score)
    game.status = Game.Status.PRELIMINARY
    game.save(update_fields=["status"])
    log_action(actor, "zakovat.preliminary_published", game)
    return score


@transaction.atomic
def submit_appeal(game, team, user, *, number, content, evidence) -> Appeal:
    """[N-7.2–7.4] apellyatsiyani faqat sardor, dastlabki natijadan keyin, yakuniygacha beradi."""
    if game.status != Game.Status.PRELIMINARY:
        raise RuleError("Apellyatsiya faqat dastlabki natija e'lon qilingandan keyin, "
                        "yakuniy natija tasdiqlanguncha qabul qilinadi [N-7.3].")
    if user.pk != team.captain_id:
        raise RuleError("Apellyatsiyani faqat jamoa sardori beradi [N-7.4].")
    if team.pk not in _approved_team_ids(game):
        raise RuleError("Jamoa bu o'yinda qatnashmagan.")
    if not 1 <= int(number) <= game.total_questions:
        raise RuleError("Savol raqami noto'g'ri [N-7.4].")
    if not (content or "").strip() or not (evidence or "").strip():
        raise RuleError("E'tiroz mazmuni va dalillar majburiy [N-7.4].")
    mark = AnswerMark.objects.filter(game=game, team=team, number=number).first()
    if mark is not None and mark.correct:
        raise RuleError("Bu savol bo'yicha javobingiz allaqachon hisobga olingan [N-7.2].")
    if Appeal.objects.filter(game=game, team=team, number=number, status=Appeal.Status.PENDING).exists():
        raise RuleError("Bu savol bo'yicha apellyatsiya ko'rib chiqilmoqda.")
    appeal = Appeal.objects.create(game=game, team=team, number=number, content=content.strip(),
                                   evidence=evidence.strip(), submitted_by=user)
    log_action(user, "zakovat.appeal_submitted", appeal)
    return appeal


@transaction.atomic
def decide_appeal(appeal, actor, *, accept: bool, reason: str, now=None) -> Appeal:
    game = appeal.game
    _require(is_tg(actor, game.season))
    if appeal.status != Appeal.Status.PENDING:
        raise RuleError("Apellyatsiya allaqachon ko'rib chiqilgan.")
    if game.status != Game.Status.PRELIMINARY:
        raise RuleError("O'yin natijasi yakunlangan.")
    if not reason.strip():
        raise RuleError("Qaror sababini yozing.")
    appeal.status = Appeal.Status.ACCEPTED if accept else Appeal.Status.REJECTED
    appeal.decided_by = actor
    appeal.decision_reason = reason.strip()
    appeal.decided_at = _now(now)
    appeal.save()
    if accept:
        mark, _ = AnswerMark.objects.get_or_create(
            game=game, team=appeal.team, number=appeal.number,
            defaults={"correct": True, "updated_by": actor})
        if not mark.correct:
            log_action(actor, "zakovat.mark_changed", mark, before={"correct": False},
                       after={"correct": True}, note=f"apellyatsiya #{appeal.pk}")
            mark.correct = True
            mark.updated_by = actor
            mark.save(update_fields=["correct", "updated_by", "updated_at"])
        _save_results(game, compute(game))  # [N-6.4] qayta hisoblash
    log_action(actor, "zakovat.appeal_decided", appeal, after={"status": appeal.status}, note=reason)
    return appeal


@transaction.atomic
def finalize_game(game, actor) -> scoring.GameScore:
    """[N-8.1] apellyatsiyalardan keyin yakuniy natija. Liga o'yini bo'lsa — ballar reestrga."""
    _require(is_tg(actor, game.season))
    if game.status != Game.Status.PRELIMINARY:
        raise RuleError("Avval dastlabki natijani e'lon qiling.")
    if game.appeals.filter(status=Appeal.Status.PENDING).exists():
        raise RuleError("Ko'rib chiqilmagan apellyatsiyalar bor.")
    score = compute(game)
    _save_results(game, score)
    game.status = Game.Status.FINAL
    game.save(update_fields=["status"])
    if game.gives_points:
        out_ids = set(Team.objects.filter(pk__in=score.teams.keys(),
                                          status__in=[Team.Status.WITHDRAWN, Team.Status.DISQUALIFIED])
                      .values_list("pk", flat=True))
        for ts in score.teams.values():
            if ts.eligible and ts.team_id not in out_ids:
                add_points(season=game.season, module=Module.ZAKOVAT, subject_type=PointsEntry.Subject.TEAM,
                           subject_id=ts.team_id, amount=ts.points, reason_type=POINTS_REASON,
                           reason_id=game.pk, note=game.title, actor=actor)
    Question.objects.filter(gamequestion__game=game).update(status=Question.Status.USED)
    if game.kind == Game.Kind.TIEBREAK and game.tiebreak_for_id:
        _apply_tiebreak_to_game(game.tiebreak_for, score)
    log_action(actor, "zakovat.game_finalized", game)
    return score


@transaction.atomic
def reopen_game(game, actor, *, reason) -> Game:
    """Yakuniy natijani qayta ochish — faqat bosh admin. Ballar tuzatuvchi yozuv bilan qaytariladi."""
    _require(is_admin(actor), "Yakuniy natijani faqat bosh admin qayta ocha oladi.")
    if game.status != Game.Status.FINAL:
        raise RuleError("O'yin yakunlanmagan.")
    if not reason.strip():
        raise RuleError("Sababini yozing.")
    totals = (PointsEntry.objects.filter(season=game.season, module=Module.ZAKOVAT,
                                         reason_type=POINTS_REASON, reason_id=str(game.pk))
              .values_list("subject_id", flat=True).distinct())
    for team_id in list(totals):
        s = points_total(season=game.season, module=Module.ZAKOVAT, subject_type=PointsEntry.Subject.TEAM,
                         subject_id=team_id, reason_type=POINTS_REASON, reason_id=game.pk)
        add_points(season=game.season, module=Module.ZAKOVAT, subject_type=PointsEntry.Subject.TEAM,
                   subject_id=team_id, amount=-s, reason_type=POINTS_REASON, reason_id=game.pk,
                   note=f"Qayta ochildi: {reason}", actor=actor)
    game.status = Game.Status.PRELIMINARY
    game.save(update_fields=["status"])
    log_action(actor, "zakovat.game_reopened", game, note=reason)
    return game


# ------------------------------------------------------------------ teng holat va mavsum reytingi

@transaction.atomic
def create_tiebreak(season, actor, team_ids, *, starts_at, questions=6, parent=None, venue="") -> Game:
    """Ball va J teng jamoalar o'rtasida qo'shimcha o'yin (parent=None — mavsum reytingi uchun)."""
    _require(is_tg(actor, season))
    if len(set(team_ids)) < 2:
        raise RuleError("Qo'shimcha o'yin uchun kamida 2 jamoa kerak.")
    if parent is not None:
        groups = set(GameResult.objects.filter(game=parent, team_id__in=team_ids)
                     .values_list("tie_group", flat=True))
        if parent.status != Game.Status.FINAL or len(groups) != 1 or None in groups:
            raise RuleError("Jamoalar shu o'yinning bitta teng guruhida bo'lishi kerak (yakuniy natijada).")
    game = Game.objects.create(
        season=season, kind=Game.Kind.TIEBREAK, title="Qo'shimcha o'yin", starts_at=starts_at,
        venue=venue, rounds=1, questions_per_round=questions, status=Game.Status.REGISTRATION,
        tiebreak_for=parent, tiebreak_for_season=parent is None)
    for i, t in enumerate(team_ids, start=1):
        GameRegistration.objects.create(game=game, team_id=t, status=GameRegistration.Status.APPROVED,
                                        table_number=i)
    log_action(actor, "zakovat.tiebreak_created", game, after={"teams": list(team_ids)})
    return game


def _apply_tiebreak_to_game(parent, tb_score):
    tb_ids = set(tb_score.teams)
    results = {r.team_id: r for r in GameResult.objects.filter(game=parent, team_id__in=tb_ids)}
    if not results:
        return
    start_place = min(r.place for r in results.values())
    next_group = (GameResult.objects.filter(game=parent).aggregate(m=Max("tie_group"))["m"] or 0) + 1
    place = start_place
    for group in scoring.apply_tiebreak(list(results), tb_score):
        for t in group:
            r = results[t]
            r.place = place
            r.tie_group = next_group if len(group) > 1 else None
            r.save(update_fields=["place", "tie_group"])
        if len(group) > 1:
            next_group += 1
        place += len(group)


def season_standings(season) -> list[dict]:
    """Mavsum reytingi (qaror: 2026-11-16):
    1) ball reestri yig'indisi; 2) teng bo'lsa — yakunlangan liga o'yinlaridagi J yig'indisi;
    3) u ham teng bo'lsa — mavsum uchun qo'shimcha o'yin (yaratilgan tartibda qo'llanadi)."""
    totals = points_by_subject(season=season, module=Module.ZAKOVAT, subject_type=PointsEntry.Subject.TEAM)
    j_totals = dict(
        GameResult.objects.filter(game__season=season, game__kind=Game.Kind.LEAGUE,
                                  game__status=Game.Status.FINAL, eligible=True)
        .values("team_id").annotate(j=Sum("rating_j")).values_list("team_id", "j"))
    teams = list(Team.objects.filter(season=season).exclude(status__in=[Team.Status.DRAFT]))
    rows = [scoring.TeamScore(team_id=t.pk, points=totals.get(t.pk, 0), rating_j=j_totals.get(t.pk, 0))
            for t in teams if not t.is_out]
    scoring.assign_places(rows)  # (ball, J)
    by_id = {r.team_id: r for r in rows}

    for tb in Game.objects.filter(season=season, kind=Game.Kind.TIEBREAK, tiebreak_for_season=True,
                                  status=Game.Status.FINAL).order_by("created_at"):
        tb_score = compute(tb)
        members = [t for t in tb_score.teams if t in by_id]
        groups_present = {by_id[t].tie_group for t in members}
        if len(groups_present) != 1 or None in groups_present:
            continue  # ballar o'zgargan — bu qo'shimcha o'yin endi amal qilmaydi
        place = min(by_id[t].place for t in members)
        next_group = max((r.tie_group or 0) for r in rows) + 1
        for group in scoring.apply_tiebreak(members, tb_score):
            for t in group:
                by_id[t].place = place
                by_id[t].tie_group = next_group if len(group) > 1 else None
            if len(group) > 1:
                next_group += 1
            place += len(group)

    names = {t.pk: t for t in teams}
    out = [{"team": names[r.team_id], "points": r.points, "rating_j": r.rating_j, "place": r.place,
            "tie_group": r.tie_group}
           for r in sorted(rows, key=lambda r: (r.place, names[r.team_id].name))]
    out += [{"team": t, "points": 0, "rating_j": 0, "place": None, "tie_group": None}
            for t in teams if t.is_out]
    return out


def season_breakdown(season) -> dict:
    """Mavsum reytingi tafsiloti: har bir liga turida qancha ball, J va o'rin; o'yindan tashqari
    tuzatishlar (masalan, chiqib ketgan jamoaning nolga tushirilishi) va oldingi turdan keyingi o'rin.

    Ballar ball reestridan olinadi (reyting bilan aynan mos), J va o'rin — o'yin natijalaridan.
    """
    games = list(Game.objects.filter(season=season, kind=Game.Kind.LEAGUE, status=Game.Status.FINAL)
                 .order_by("starts_at"))
    game_ids = {str(g.pk) for g in games}
    results = {}
    for r in GameResult.objects.filter(game__in=games):
        results.setdefault(r.team_id, {})[r.game_id] = r

    # reestr: jamoa → {o'yin_id: ball}, boshqa sabablar alohida
    by_game, other = {}, {}
    for e in PointsEntry.objects.filter(season=season, module=Module.ZAKOVAT,
                                        subject_type=PointsEntry.Subject.TEAM):
        if e.reason_type == POINTS_REASON and e.reason_id in game_ids:
            d = by_game.setdefault(e.subject_id, {})
            d[int(e.reason_id)] = d.get(int(e.reason_id), 0) + e.amount
        else:
            other[e.subject_id] = other.get(e.subject_id, 0) + e.amount

    teams = {}
    for team_id in set(results) | set(by_game) | set(other):
        per = {}
        for g in games:
            r = results.get(team_id, {}).get(g.pk)
            if r is None:
                continue
            per[g.pk] = {"points": by_game.get(team_id, {}).get(g.pk, 0), "rating_j": r.rating_j,
                         "place": r.place, "eligible": r.eligible}
        played = [v for v in per.values() if v["eligible"]]
        teams[team_id] = {
            "by_game": per,
            "other_points": other.get(team_id, 0),
            "played": len(played),
            "wins": sum(1 for v in played if v["place"] == 1),
            "best": max((v["points"] for v in played), default=0),
        }

    # oldingi o'rin: oxirgi yakunlangan turgacha bo'lgan holat
    prev_places = {}
    if len(games) >= 2:
        last = games[-1].pk
        rows = []
        for st in season_standings(season):
            t = st["team"]
            if st["place"] is None:
                continue
            g = teams.get(t.pk, {}).get("by_game", {}).get(last)
            rows.append(scoring.TeamScore(team_id=t.pk, points=st["points"] - (g["points"] if g else 0),
                                          rating_j=st["rating_j"] - (g["rating_j"] if g and g["eligible"] else 0)))
        scoring.assign_places(rows)
        prev_places = {r.team_id: r.place for r in rows}

    return {"games": games, "teams": teams, "prev_places": prev_places}
