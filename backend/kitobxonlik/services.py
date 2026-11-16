"""Kitobxonlik qoidalari.

Tur bosqichlari: qoralama → ovoz berish → o'qish (hammaga bir xil 10 kun) → baholash → yakunlangan.
- Eng ko'p ovoz olgan kitob tanlanadi; teng bo'lsa — tashkilotchi tanlaydi.
- Izoh: matn (minimal uzunlik) yoki fayl; muddat tugaguncha tahrirlash mumkin.
- Tekshiruvchi o'z izohini baholay olmaydi; izoh muallifini ko'radi (qaror: 2026-11-16).
- Bir nechta tekshiruvchi bo'lsa — o'rtacha ball. Ball reestriga butun songa yaxlitlangan holda yoziladi.
"""
from collections import Counter
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.api import RuleError as BaseRuleError
from core.models import Module, PointsEntry, Role
from core.services import add_points, has_role, log_action, points_by_subject

from .models import (
    Book, Criterion, Extension, Grade, GradeScore, ReadingRound, Review, SeasonConfig, Vote,
)

POINTS_REASON = "kitobxonlik.review"
MAX_FILE_MB = 20


class RuleError(BaseRuleError):
    pass


def _now(now):
    return now or timezone.now()


def _require(cond, msg="Bu amal uchun ruxsatingiz yo'q."):
    if not cond:
        raise RuleError(msg)


def is_organizer(user, season=None) -> bool:
    return has_role(user, Role.ORGANIZER, Module.KITOBXONLIK, season)


def is_reviewer(user, season=None) -> bool:
    return is_organizer(user, season) or has_role(user, Role.REVIEWER, Module.KITOBXONLIK, season)


def _participant(user):
    _require(user.can_login and user.employee_id is not None, "Faqat xodimlar ishtirok etadi.")


S = ReadingRound.Status


# ------------------------------------------------------------------ kitoblar va tur

@transaction.atomic
def add_book(actor, *, title, author, pdf, description="", cover=None, rights_confirmed=False) -> Book:
    _require(is_organizer(actor))
    if not rights_confirmed:
        raise RuleError("Kitobni tarqatish huquqi borligini tasdiqlang (mualliflik huquqi).")
    if pdf.size > settings.FILE_UPLOAD_MAX_MB * 1024 * 1024:
        raise RuleError(f"PDF hajmi {settings.FILE_UPLOAD_MAX_MB} MB dan oshmasligi kerak.")
    if not pdf.name.lower().endswith(".pdf"):
        raise RuleError("Faqat PDF fayl qabul qilinadi.")
    book = Book(title=title, author=author, description=description, rights_confirmed=True, added_by=actor)
    book.pdf.save(pdf.name, pdf, save=False)
    if cover:
        book.cover.save(cover.name, cover, save=False)
    book.save()
    log_action(actor, "kitob.book_added", book)
    return book


@transaction.atomic
def create_round(season, actor, *, title, book_ids, criteria, reading_days=10, min_review_length=500,
                 reviewers_per_review=1) -> ReadingRound:
    """criteria: [{"name": ..., "max_points": ...}, ...]"""
    _require(is_organizer(actor, season))
    books = list(Book.objects.filter(pk__in=book_ids))
    if len(books) < 2:
        raise RuleError("Ovoz berish uchun kamida 2 ta kitob kerak.")
    if not criteria:
        raise RuleError("Kamida bitta baholash mezoni kerak.")
    if not 1 <= reading_days <= 60:
        raise RuleError("O'qish muddati 1–60 kun bo'lishi kerak.")
    rnd = ReadingRound.objects.create(
        season=season, title=title, reading_days=reading_days, min_review_length=min_review_length,
        reviewers_per_review=max(1, reviewers_per_review), created_by=actor)
    rnd.candidates.set(books)
    for i, c in enumerate(criteria):
        if int(c["max_points"]) < 1:
            raise RuleError("Mezon maksimal bali kamida 1 bo'lishi kerak.")
        Criterion.objects.create(round=rnd, name=c["name"], max_points=int(c["max_points"]), order=i)
    log_action(actor, "kitob.round_created", rnd)
    return rnd


@transaction.atomic
def start_voting(rnd, actor, *, vote_ends, now=None) -> ReadingRound:
    _require(is_organizer(actor, rnd.season))
    if rnd.status != S.DRAFT:
        raise RuleError("Ovoz berish faqat qoralama turda boshlanadi.")
    if vote_ends <= _now(now):
        raise RuleError("Ovoz berish tugash vaqti kelajakda bo'lishi kerak.")
    rnd.status, rnd.vote_ends = S.VOTING, vote_ends
    rnd.save(update_fields=["status", "vote_ends"])
    log_action(actor, "kitob.voting_started", rnd)
    return rnd


@transaction.atomic
def cast_vote(rnd, user, book, *, now=None) -> Vote:
    _participant(user)
    if rnd.status != S.VOTING or _now(now) > rnd.vote_ends:
        raise RuleError("Ovoz berish yopiq.")
    if not rnd.candidates.filter(pk=book.pk).exists():
        raise RuleError("Bu kitob ovozga qo'yilmagan.")
    vote, _ = Vote.objects.update_or_create(round=rnd, user=user, defaults={"book": book})
    return vote


def vote_counts(rnd) -> dict:
    return dict(Counter(rnd.votes.values_list("book_id", flat=True)))


def leaders(rnd) -> list[int]:
    counts = vote_counts(rnd)
    if not counts:
        return []
    top = max(counts.values())
    return sorted(b for b, n in counts.items() if n == top)


@transaction.atomic
def close_voting(rnd, actor, *, pick_book=None, now=None) -> ReadingRound:
    """Eng ko'p ovoz olgan kitob tanlanadi va o'qish boshlanadi (hammaga bir xil muddat).
    Ovozlar teng (yoki ovoz yo'q) bo'lsa — tashkilotchi pick_book bilan tanlaydi."""
    _require(is_organizer(actor, rnd.season))
    if rnd.status != S.VOTING:
        raise RuleError("Ovoz berish ketmayapti.")
    top = leaders(rnd)
    if len(top) == 1 and pick_book is None:
        book_id = top[0]
    else:
        allowed = top or list(rnd.candidates.values_list("pk", flat=True))
        if pick_book is None:
            raise RuleError("Ovozlar teng. Tashkilotchi kitobni tanlashi kerak: "
                            + ", ".join(str(b) for b in Book.objects.filter(pk__in=allowed)))
        if pick_book.pk not in allowed:
            raise RuleError("Faqat eng ko'p ovoz olgan kitoblardan birini tanlash mumkin.")
        book_id = pick_book.pk
    start = _now(now)
    rnd.selected_book_id = book_id
    rnd.status = S.READING
    rnd.reading_starts = start
    rnd.reading_ends = start + timedelta(days=rnd.reading_days)
    rnd.save(update_fields=["selected_book", "status", "reading_starts", "reading_ends"])
    log_action(actor, "kitob.voting_closed", rnd,
               after={"book": book_id, "votes": vote_counts(rnd), "manual_pick": pick_book is not None})
    return rnd


def can_read(rnd, user) -> bool:
    return (rnd.status in (S.READING, S.GRADING, S.DONE) and rnd.selected_book_id is not None
            and user.can_login)


# ------------------------------------------------------------------ izohlar

@transaction.atomic
def grant_extension(rnd, actor, user, *, until, reason) -> Extension:
    _require(is_organizer(actor, rnd.season))
    if rnd.status not in (S.READING, S.GRADING):
        raise RuleError("Muddatni faqat o'qish yoki baholash bosqichida uzaytirish mumkin.")
    if not reason.strip():
        raise RuleError("Sababini yozing.")
    if until <= rnd.reading_ends:
        raise RuleError("Yangi muddat umumiy muddatdan keyin bo'lishi kerak.")
    review = Review.objects.filter(round=rnd, user=user).first()
    if review and review.grades.exists():
        raise RuleError("Bu xodimning izohi allaqachon baholangan.")
    ext = Extension.objects.create(round=rnd, user=user, until=until, reason=reason.strip(), granted_by=actor)
    log_action(actor, "kitob.extension_granted", ext, after={"user": user.pk, "until": str(until)})
    return ext


@transaction.atomic
def submit_review(rnd, user, *, text="", file=None, now=None) -> Review:
    _participant(user)
    if rnd.status not in (S.READING, S.GRADING):
        raise RuleError("Izoh qabul qilinmaydi.")
    deadline = rnd.deadline_for(user)
    if _now(now) > deadline:
        raise RuleError("Izoh yuborish muddati tugagan.")
    text = (text or "").strip()
    review = Review.objects.filter(round=rnd, user=user).first()
    has_file = bool(file) or bool(review and review.file)
    if len(text) < rnd.min_review_length and not has_file:
        raise RuleError(f"Izoh kamida {rnd.min_review_length} belgi bo'lishi kerak yoki fayl yuklang.")
    if file is not None:
        ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
        from .models import REVIEW_FILE_TYPES
        if ext not in REVIEW_FILE_TYPES:
            raise RuleError("Fayl turi: " + ", ".join(REVIEW_FILE_TYPES))
        if file.size > MAX_FILE_MB * 1024 * 1024:
            raise RuleError(f"Fayl hajmi {MAX_FILE_MB} MB dan oshmasligi kerak.")
    if review is None:
        review = Review(round=rnd, user=user, submitted_at=_now(now))
    elif review.grades.exists():
        raise RuleError("Izoh baholanmoqda, uni endi o'zgartirib bo'lmaydi.")
    review.text = text
    review.submitted_at = _now(now)
    if file is not None:
        review.file.save(file.name, file, save=False)
    review.save()
    return review


# ------------------------------------------------------------------ baholash

@transaction.atomic
def start_grading(rnd, actor, *, now=None) -> ReadingRound:
    _require(is_organizer(actor, rnd.season))
    if rnd.status != S.READING:
        raise RuleError("Tur o'qish bosqichida emas.")
    if _now(now) <= rnd.reading_ends:
        raise RuleError("Izoh yuborish muddati hali tugamagan.")
    rnd.status = S.GRADING
    rnd.save(update_fields=["status"])
    log_action(actor, "kitob.grading_started", rnd)
    return rnd


@transaction.atomic
def grade_review(review, reviewer, *, scores: dict, comment="", now=None) -> Grade:
    """scores: {criterion_id: points}. Har mezon majburiy, 0..max oralig'ida."""
    rnd = review.round
    _require(is_reviewer(reviewer, rnd.season))
    if review.user_id == reviewer.pk:
        raise RuleError("O'z izohingizni baholay olmaysiz.")
    if rnd.status != S.GRADING:
        raise RuleError("Tur baholash bosqichida emas.")
    if review.status == Review.Status.APPROVED:
        raise RuleError("Natija tasdiqlangan, bahoni o'zgartirib bo'lmaydi.")
    if _now(now) <= rnd.deadline_for(review.user):
        raise RuleError("Bu xodimning izoh yuborish muddati hali tugamagan.")
    criteria = {c.pk: c for c in rnd.criteria.all()}
    scores = {int(k): int(v) for k, v in scores.items()}
    if set(scores) != set(criteria):
        raise RuleError("Barcha mezonlar bo'yicha ball qo'ying.")
    for cid, pts in scores.items():
        if not 0 <= pts <= criteria[cid].max_points:
            raise RuleError(f"'{criteria[cid].name}' uchun ball 0–{criteria[cid].max_points} oralig'ida bo'lishi kerak.")
    grade, _ = Grade.objects.update_or_create(
        review=review, reviewer=reviewer,
        defaults={"comment": comment.strip(), "total": sum(scores.values())})
    for cid, pts in scores.items():
        GradeScore.objects.update_or_create(grade=grade, criterion_id=cid, defaults={"points": pts})
    log_action(reviewer, "kitob.review_graded", grade, after={"scores": scores})
    return grade


def average_score(review) -> Decimal | None:
    totals = list(review.grades.values_list("total", flat=True))
    if not totals:
        return None
    return (Decimal(sum(totals)) / len(totals)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@transaction.atomic
def approve_results(rnd, actor) -> int:
    """Tashkilotchi barcha baholarni tasdiqlaydi → ballar reestrga yoziladi, tur yakunlanadi."""
    _require(is_organizer(actor, rnd.season))
    if rnd.status != S.GRADING:
        raise RuleError("Tur baholash bosqichida emas.")
    reviews = list(rnd.reviews.prefetch_related("grades"))
    missing = [r for r in reviews if r.grades.count() < rnd.reviewers_per_review]
    if missing:
        raise RuleError(f"{len(missing)} ta izoh hali to'liq baholanmagan "
                        f"(har biriga {rnd.reviewers_per_review} ta baho kerak).")
    open_ext = rnd.extensions.filter(until__gt=timezone.now()).exclude(
        user__in=[r.user_id for r in reviews])
    if open_ext.exists():
        raise RuleError("Muddati uzaytirilgan xodimlarning muddati hali tugamagan.")
    for r in reviews:
        r.final_score = average_score(r)
        r.status = Review.Status.APPROVED
        r.save(update_fields=["final_score", "status"])
        add_points(season=rnd.season, module=Module.KITOBXONLIK, subject_type=PointsEntry.Subject.USER,
                   subject_id=r.user_id,
                   amount=int(r.final_score.quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
                   reason_type=POINTS_REASON, reason_id=r.pk, note=rnd.title, actor=actor)
    rnd.status = S.DONE
    rnd.save(update_fields=["status"])
    log_action(actor, "kitob.results_approved", rnd, after={"reviews": len(reviews)})
    return len(reviews)


# ------------------------------------------------------------------ kartochka va reyting

def personal_card(season, user) -> dict:
    reviews = (Review.objects.filter(round__season=season, user=user)
               .select_related("round__selected_book").prefetch_related("grades__scores__criterion"))
    items = []
    for r in reviews:
        approved = r.status == Review.Status.APPROVED
        items.append({
            "round": {"id": r.round_id, "title": r.round.title},
            "book": str(r.round.selected_book) if r.round.selected_book_id else None,
            "submitted_at": r.submitted_at, "status": r.status,
            "score": r.final_score if approved else None,
            # baholar faqat tasdiqlangandan keyin ko'rinadi; tekshiruvchi ismi ko'rsatilmaydi
            "grades": [{
                "total": g.total, "comment": g.comment,
                "scores": [{"criterion": s.criterion.name, "points": s.points,
                            "max": s.criterion.max_points} for s in g.scores.all()],
            } for g in r.grades.all()] if approved else [],
        })
    total = points_by_subject(season=season, module=Module.KITOBXONLIK,
                              subject_type=PointsEntry.Subject.USER).get(user.pk, 0)
    return {"season_points": total, "reviews": items}


def leaderboard_visible(season, user) -> bool:
    cfg = SeasonConfig.objects.filter(season=season).first()
    return bool(cfg and cfg.leaderboard_public) or is_organizer(user, season)


def leaderboard(season) -> list[dict]:
    from accounts.models import User
    totals = points_by_subject(season=season, module=Module.KITOBXONLIK, subject_type=PointsEntry.Subject.USER)
    users = {u.pk: u for u in User.objects.filter(pk__in=totals).select_related("employee__branch")}
    rows = sorted(((uid, pts) for uid, pts in totals.items() if uid in users), key=lambda x: (-x[1], str(users[x[0]])))
    out, place, prev = [], 0, None
    for i, (uid, pts) in enumerate(rows, start=1):
        if pts != prev:
            place, prev = i, pts
        u = users[uid]
        out.append({"place": place, "user": {"id": uid, "name": str(u),
                                             "branch": u.employee.branch.name if u.employee_id else None},
                    "points": pts})
    return out
