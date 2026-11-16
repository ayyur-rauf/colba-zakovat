"""Kitobxonlik API. Qoidalar va ruxsatlar services.py da."""
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from accounts.models import User
from core.exports import xlsx_response
from core.models import Season

from . import services as svc
from .models import Book, ReadingRound, Review

S = ReadingRound.Status


def get_season(request) -> Season:
    sid = request.query_params.get("season")
    if sid:
        return get_object_or_404(Season, pk=sid)
    season = Season.current()
    if season is None:
        raise svc.RuleError("Faol mavsum yo'q.")
    return season


def validated(ser_cls, data):
    s = ser_cls(data=data)
    s.is_valid(raise_exception=True)
    return s.validated_data


def book_brief(b: Book, request) -> dict:
    return {"id": b.pk, "title": b.title, "author": b.author, "description": b.description,
            "cover": request.build_absolute_uri(b.cover.url) if b.cover else None}


def round_payload(rnd: ReadingRound, request) -> dict:
    user = request.user
    organizer = svc.is_organizer(user, rnd.season)
    my_vote = rnd.votes.filter(user=user).values_list("book_id", flat=True).first()
    my_review = rnd.reviews.filter(user=user).first()
    deadline = rnd.deadline_for(user)
    votes_visible = organizer or rnd.status != S.VOTING
    return {
        "id": rnd.pk, "title": rnd.title, "status": rnd.status,
        "candidates": [book_brief(b, request) for b in rnd.candidates.all()],
        "vote_ends": rnd.vote_ends,
        "votes": svc.vote_counts(rnd) if votes_visible else None,
        "my_vote": my_vote,
        "selected_book": book_brief(rnd.selected_book, request) if rnd.selected_book_id else None,
        "reading_days": rnd.reading_days, "reading_starts": rnd.reading_starts,
        "my_deadline": deadline,
        "min_review_length": rnd.min_review_length,
        "criteria": [{"id": c.pk, "name": c.name, "max_points": c.max_points} for c in rnd.criteria.all()],
        "my_review": None if my_review is None else {
            "id": my_review.pk, "status": my_review.status, "submitted_at": my_review.submitted_at,
            "text": my_review.text, "has_file": bool(my_review.file),
        },
        "can_read": svc.can_read(rnd, user),
    }


def review_for_grading(r: Review, request) -> dict:
    my_grade = r.grades.filter(reviewer=request.user).prefetch_related("scores").first()
    return {
        "id": r.id, "author": {"id": r.user_id, "name": str(r.user)},
        "text": r.text, "has_file": bool(r.file), "submitted_at": r.submitted_at,
        "status": r.status, "grades_count": r.grades.count(), "average": svc.average_score(r),
        "my_grade": None if my_grade is None else {
            "comment": my_grade.comment, "total": my_grade.total,
            "scores": {s.criterion_id: s.points for s in my_grade.scores.all()}},
    }


# ------------------------------------------------------------------ kirish ma'lumotlari

class CriterionSer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    max_points = serializers.IntegerField(min_value=1, max_value=100)


class RoundCreateSer(serializers.Serializer):
    title = serializers.CharField(max_length=150)
    book_ids = serializers.ListField(child=serializers.IntegerField(), min_length=2)
    criteria = CriterionSer(many=True)
    reading_days = serializers.IntegerField(min_value=1, max_value=60, default=10)
    min_review_length = serializers.IntegerField(min_value=0, default=500)
    reviewers_per_review = serializers.IntegerField(min_value=1, max_value=5, default=1)


class VoteEndsSer(serializers.Serializer):
    vote_ends = serializers.DateTimeField()


class BookIdSer(serializers.Serializer):
    book_id = serializers.IntegerField()


class PickSer(serializers.Serializer):
    book_id = serializers.IntegerField(required=False)


class ExtensionSer(serializers.Serializer):
    user_id = serializers.IntegerField()
    until = serializers.DateTimeField()
    reason = serializers.CharField()


class ScoreSer(serializers.Serializer):
    criterion_id = serializers.IntegerField()
    points = serializers.IntegerField(min_value=0)


class GradeSer(serializers.Serializer):
    scores = ScoreSer(many=True)
    comment = serializers.CharField(allow_blank=True, default="")


class BookCreateSer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    author = serializers.CharField(max_length=200)
    description = serializers.CharField(allow_blank=True, default="")
    pdf = serializers.FileField()
    cover = serializers.ImageField(required=False)
    rights_confirmed = serializers.BooleanField(default=False)


# ------------------------------------------------------------------ kitoblar

class BookViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def list(self, request):
        if not svc.is_organizer(request.user):
            raise PermissionDenied()
        return Response([book_brief(b, request) for b in Book.objects.all()])

    def create(self, request):
        d = validated(BookCreateSer, request.data)
        book = svc.add_book(request.user, **d)
        return Response(book_brief(book, request), status=status.HTTP_201_CREATED)


# ------------------------------------------------------------------ turlar

class RoundViewSet(ViewSet):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def _round(self, pk) -> ReadingRound:
        return get_object_or_404(ReadingRound.objects.select_related("season", "selected_book"), pk=pk)

    def list(self, request):
        season = get_season(request)
        qs = ReadingRound.objects.filter(season=season)
        if not svc.is_organizer(request.user, season):
            qs = qs.exclude(status=S.DRAFT)
        return Response([round_payload(r, request) for r in qs])

    def retrieve(self, request, pk):
        rnd = self._round(pk)
        if rnd.status == S.DRAFT and not svc.is_organizer(request.user, rnd.season):
            raise PermissionDenied()
        return Response(round_payload(rnd, request))

    def create(self, request):
        d = validated(RoundCreateSer, request.data)
        rnd = svc.create_round(get_season(request), request.user, **d)
        return Response(round_payload(rnd, request), status=status.HTTP_201_CREATED)

    # ---------------------------------------------------------- xodim
    @action(detail=True, methods=["post"])
    def vote(self, request, pk):
        rnd = self._round(pk)
        d = validated(BookIdSer, request.data)
        svc.cast_vote(rnd, request.user, get_object_or_404(Book, pk=d["book_id"]))
        return Response(round_payload(rnd, request))

    @action(detail=True, methods=["get"])
    def book(self, request, pk):
        """Tanlangan kitob PDF fayli (faqat o'qish bosqichidan boshlab, kirgan xodimga)."""
        rnd = self._round(pk)
        if not svc.can_read(rnd, request.user):
            raise svc.RuleError("Kitob hali ochilmagan.")
        f = rnd.selected_book.pdf
        download = request.query_params.get("download") in ("1", "true")
        return FileResponse(f.open("rb"), as_attachment=download,
                            filename=f"{rnd.selected_book.title}.pdf", content_type="application/pdf")

    @action(detail=True, methods=["get", "post"], url_path="my-review")
    def my_review(self, request, pk):
        rnd = self._round(pk)
        if request.method == "POST":
            svc.submit_review(rnd, request.user, text=request.data.get("text", ""),
                              file=request.FILES.get("file"))
            return Response(round_payload(rnd, request)["my_review"])
        return Response(round_payload(rnd, request)["my_review"])

    # ---------------------------------------------------------- tashkilotchi
    @action(detail=True, methods=["post"], url_path="start-voting")
    def start_voting(self, request, pk):
        d = validated(VoteEndsSer, request.data)
        return Response(round_payload(svc.start_voting(self._round(pk), request.user, **d), request))

    @action(detail=True, methods=["post"], url_path="close-voting")
    def close_voting(self, request, pk):
        d = validated(PickSer, request.data)
        pick = get_object_or_404(Book, pk=d["book_id"]) if d.get("book_id") else None
        return Response(round_payload(svc.close_voting(self._round(pk), request.user, pick_book=pick), request))

    @action(detail=True, methods=["post"])
    def extensions(self, request, pk):
        d = validated(ExtensionSer, request.data)
        ext = svc.grant_extension(self._round(pk), request.user, get_object_or_404(User, pk=d["user_id"]),
                                  until=d["until"], reason=d["reason"])
        return Response({"id": ext.pk, "until": ext.until}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="start-grading")
    def start_grading(self, request, pk):
        return Response(round_payload(svc.start_grading(self._round(pk), request.user), request))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk):
        n = svc.approve_results(self._round(pk), request.user)
        return Response({"approved": n})

    @action(detail=True, methods=["get"])
    def missing(self, request, pk):
        """Izoh yubormagan faol xodimlar (tashkilotchi uchun)."""
        rnd = self._round(pk)
        if not svc.is_organizer(request.user, rnd.season):
            raise PermissionDenied()
        submitted = set(rnd.reviews.values_list("user_id", flat=True))
        ext = {e.user_id: e.until for e in rnd.extensions.all()}
        users = (User.objects.filter(status=User.Status.ACTIVE, employee__isnull=False, employee__is_active=True)
                 .exclude(pk__in=submitted).select_related("employee__branch").order_by("employee__full_name"))
        return Response({
            "submitted": len(submitted),
            "items": [{"id": u.pk, "name": str(u), "branch": u.employee.branch.name, "extended_until": ext.get(u.pk)}
                      for u in users],
        })

    @action(detail=True, methods=["get"])
    def export(self, request, pk):
        rnd = self._round(pk)
        if not svc.is_organizer(request.user, rnd.season):
            raise PermissionDenied()
        criteria = list(rnd.criteria.all())
        rows = []
        for r in rnd.reviews.select_related("user__employee__branch").prefetch_related("grades__scores"):
            per = {}
            for g in r.grades.all():
                for sc in g.scores.all():
                    per.setdefault(sc.criterion_id, []).append(sc.points)
            avg = svc.average_score(r)
            rows.append([str(r.user), r.user.employee.branch.name if r.user.employee_id else "",
                         r.submitted_at.strftime("%d.%m.%Y %H:%M"), r.get_status_display(), r.grades.count()]
                        + [round(sum(per[c.pk]) / len(per[c.pk]), 2) if per.get(c.pk) else "" for c in criteria]
                        + [float(r.final_score) if r.final_score is not None else (float(avg) if avg is not None else "")])
        return xlsx_response(f"{rnd.title} natija.xlsx", [(
            "Izohlar",
            ["Xodim", "Filial", "Yuborilgan", "Holat", "Baholar soni"] + [f"{c.name} (/{c.max_points})" for c in criteria]
            + ["Yakuniy ball"],
            rows,
        )])

    @action(detail=True, methods=["get"])
    def reviews(self, request, pk):
        """Tekshiruvchi va tashkilotchi uchun izohlar ro'yxati (muallif va o'rtacha ball bilan).
        O'z izohi ro'yxatga kirmaydi."""
        rnd = self._round(pk)
        if not svc.is_reviewer(request.user, rnd.season):
            raise PermissionDenied()
        qs = rnd.reviews.exclude(user=request.user).select_related("user__employee").order_by("id")
        return Response([review_for_grading(r, request) for r in qs])


class ReviewFileView(APIView):
    """Izoh fayli: muallifning o'ziga, tekshiruvchi va tashkilotchiga."""

    def get(self, request, pk):
        review = get_object_or_404(Review.objects.select_related("round__season"), pk=pk)
        if review.user_id != request.user.pk and not svc.is_reviewer(request.user, review.round.season):
            raise PermissionDenied()
        if not review.file:
            raise svc.RuleError("Fayl yuklanmagan.")
        name = f"izoh_{review.pk}.{review.file.name.rsplit('.', 1)[-1]}"
        return FileResponse(review.file.open("rb"), as_attachment=True, filename=name)


class GradeView(APIView):
    def post(self, request, pk):
        review = get_object_or_404(Review.objects.select_related("round__season"), pk=pk)
        d = validated(GradeSer, request.data)
        grade = svc.grade_review(review, request.user,
                                 scores={s["criterion_id"]: s["points"] for s in d["scores"]},
                                 comment=d["comment"])
        return Response({"id": grade.pk, "total": grade.total})


class MyCardView(APIView):
    def get(self, request):
        return Response(svc.personal_card(get_season(request), request.user))


class LeaderboardView(APIView):
    def get(self, request):
        season = get_season(request)
        if not svc.leaderboard_visible(season, request.user):
            raise PermissionDenied("Reyting jadvali hozircha yopiq.")
        return Response(svc.leaderboard(season))



class LeaderboardExportView(APIView):
    def get(self, request):
        season = get_season(request)
        if not svc.leaderboard_visible(season, request.user):
            raise PermissionDenied("Reyting jadvali hozircha yopiq.")
        rows = [[r["place"], r["user"]["name"], r["user"]["branch"], r["points"]] for r in svc.leaderboard(season)]
        return xlsx_response(f"Kitobxonlar reytingi {season.name}.xlsx",
                             [("Reyting", ["O'rin", "Xodim", "Filial", "Ball"], rows)])
