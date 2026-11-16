import shutil
import tempfile
from datetime import date, datetime, timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Branch, Employee, User
from core.models import Module, Role, RoleAssignment, Season
from core.services import points_total
from kitobxonlik import services as svc
from kitobxonlik.models import ReadingRound, Review, SeasonConfig

TMP = tempfile.mkdtemp()
LONG = "Bu kitob menga juda yoqdi. " * 30  # ~800 belgi


def pdf(name="kitob.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 test", content_type="application/pdf")


@override_settings(PRIVATE_MEDIA_ROOT=TMP, MEDIA_ROOT=TMP)
class Base(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def setUp(self):
        self.season = Season.objects.create(name="2026–2027", start_date=date(2026, 9, 1),
                                            end_date=date(2027, 8, 31), is_active=True)
        self.branch = Branch.objects.create(name="Chilonzor")
        self.org = self.employee("Tashkilotchi")
        RoleAssignment.objects.create(user=self.org, role=Role.ORGANIZER, module=Module.KITOBXONLIK)
        self.rev = self.employee("Tekshiruvchi")
        RoleAssignment.objects.create(user=self.rev, role=Role.REVIEWER, module=Module.KITOBXONLIK)
        self.a, self.b, self.c = (self.employee(n) for n in ("Ali", "Bek", "Gulya"))
        self.book1 = svc.add_book(self.org, title="O'tkan kunlar", author="A. Qodiriy", pdf=pdf(),
                                  rights_confirmed=True)
        self.book2 = svc.add_book(self.org, title="Kecha va kunduz", author="Cho'lpon", pdf=pdf(),
                                  rights_confirmed=True)
        self.t0 = timezone.make_aware(datetime(2026, 11, 1, 9))

    def employee(self, name):
        emp = Employee.objects.create(full_name=name, branch=self.branch)
        return User.objects.create(username=name.lower(), employee=emp, status=User.Status.ACTIVE)

    def new_round(self, **kw):
        return svc.create_round(self.season, self.org, title="Noyabr kitobi",
                                book_ids=[self.book1.pk, self.book2.pk],
                                criteria=[{"name": "Mazmun", "max_points": 10},
                                          {"name": "Shaxsiy fikr", "max_points": 10},
                                          {"name": "Savodxonlik", "max_points": 5}], **kw)

    def to_reading(self, rnd, votes):
        svc.start_voting(rnd, self.org, vote_ends=self.t0 + timedelta(days=3), now=self.t0)
        for user, book in votes:
            svc.cast_vote(rnd, user, book, now=self.t0 + timedelta(hours=1))
        return svc.close_voting(rnd, self.org, now=self.t0 + timedelta(days=3))

    def scores(self, rnd, *pts):
        return {c.pk: p for c, p in zip(rnd.criteria.all(), pts)}


class RuleTests(Base):
    def test_book_requires_rights(self):
        with self.assertRaisesMessage(svc.RuleError, "huquq"):
            svc.add_book(self.org, title="X", author="Y", pdf=pdf())

    def test_only_organizer_creates_round(self):
        with self.assertRaises(svc.RuleError):
            svc.create_round(self.season, self.a, title="X", book_ids=[self.book1.pk, self.book2.pk],
                             criteria=[{"name": "M", "max_points": 5}])

    def test_most_votes_wins_and_reading_is_ten_days_for_all(self):
        rnd = self.to_reading(self.new_round(), [(self.a, self.book1), (self.b, self.book2), (self.c, self.book2)])
        self.assertEqual(rnd.selected_book, self.book2)
        self.assertEqual(rnd.reading_ends - rnd.reading_starts, timedelta(days=10))

    def test_vote_can_change_until_end(self):
        rnd = self.new_round()
        svc.start_voting(rnd, self.org, vote_ends=self.t0 + timedelta(days=3), now=self.t0)
        svc.cast_vote(rnd, self.a, self.book1, now=self.t0)
        svc.cast_vote(rnd, self.a, self.book2, now=self.t0)
        self.assertEqual(svc.vote_counts(rnd), {self.book2.pk: 1})
        with self.assertRaisesMessage(svc.RuleError, "yopiq"):
            svc.cast_vote(rnd, self.a, self.book1, now=self.t0 + timedelta(days=4))

    def test_tie_requires_organizer_pick(self):
        rnd = self.new_round()
        svc.start_voting(rnd, self.org, vote_ends=self.t0 + timedelta(days=3), now=self.t0)
        svc.cast_vote(rnd, self.a, self.book1, now=self.t0)
        svc.cast_vote(rnd, self.b, self.book2, now=self.t0)
        with self.assertRaisesMessage(svc.RuleError, "teng"):
            svc.close_voting(rnd, self.org, now=self.t0 + timedelta(days=3))
        rnd = svc.close_voting(rnd, self.org, pick_book=self.book1, now=self.t0 + timedelta(days=3))
        self.assertEqual(rnd.selected_book, self.book1)

    def test_review_rules(self):
        rnd = self.to_reading(self.new_round(), [(self.a, self.book1)])
        day = rnd.reading_starts + timedelta(days=2)
        with self.assertRaisesMessage(svc.RuleError, "500"):
            svc.submit_review(rnd, self.a, text="Qisqa", now=day)
        # fayl bo'lsa qisqa matn ham bo'ladi
        f = SimpleUploadedFile("izoh.docx", b"x" * 100)
        svc.submit_review(rnd, self.b, text="", file=f, now=day)
        bad = SimpleUploadedFile("izoh.exe", b"x")
        with self.assertRaisesMessage(svc.RuleError, "Fayl turi"):
            svc.submit_review(rnd, self.c, file=bad, now=day)
        # muddatdan keyin — yopiq
        with self.assertRaisesMessage(svc.RuleError, "muddati tugagan"):
            svc.submit_review(rnd, self.a, text=LONG, now=rnd.reading_ends + timedelta(minutes=1))

    def test_extension_allows_late_submission(self):
        rnd = self.to_reading(self.new_round(), [(self.a, self.book1)])
        late = rnd.reading_ends + timedelta(days=1)
        svc.grant_extension(rnd, self.org, self.a, until=rnd.reading_ends + timedelta(days=2),
                            reason="Kasal bo'ldi")
        svc.submit_review(rnd, self.a, text=LONG, now=late)
        with self.assertRaises(svc.RuleError):
            svc.submit_review(rnd, self.b, text=LONG, now=late)


class GradingFlowTests(Base):
    def setUp(self):
        super().setUp()
        self.rnd = self.to_reading(self.new_round(reviewers_per_review=2), [(self.a, self.book1)])
        day = self.rnd.reading_starts + timedelta(days=1)
        self.ra = svc.submit_review(self.rnd, self.a, text=LONG, now=day)
        self.rb = svc.submit_review(self.rnd, self.b, text=LONG, now=day)
        self.after = self.rnd.reading_ends + timedelta(hours=1)

    def test_cannot_grade_before_deadline_or_own(self):
        with self.assertRaisesMessage(svc.RuleError, "baholash bosqichida emas"):
            svc.grade_review(self.ra, self.rev, scores=self.scores(self.rnd, 5, 5, 5))
        svc.start_grading(self.rnd, self.org, now=self.after)
        with self.assertRaisesMessage(svc.RuleError, "ruxsat"):
            svc.grade_review(self.rb, self.a, scores={})  # oddiy xodim baholay olmaydi
        RoleAssignment.objects.create(user=self.a, role=Role.REVIEWER, module=Module.KITOBXONLIK)
        with self.assertRaisesMessage(svc.RuleError, "O'z izohingizni"):
            svc.grade_review(self.ra, self.a, scores={})
        with self.assertRaisesMessage(svc.RuleError, "0–5"):
            svc.grade_review(self.ra, self.rev, scores=self.scores(self.rnd, 5, 5, 9), now=self.after)
        with self.assertRaisesMessage(svc.RuleError, "Barcha mezonlar"):
            svc.grade_review(self.ra, self.rev, scores={self.rnd.criteria.first().pk: 3}, now=self.after)

    def test_average_points_go_to_ledger(self):
        svc.start_grading(self.rnd, self.org, now=self.after)
        svc.grade_review(self.ra, self.rev, scores=self.scores(self.rnd, 8, 7, 4), comment="Yaxshi", now=self.after)
        with self.assertRaisesMessage(svc.RuleError, "to'liq baholanmagan"):
            svc.approve_results(self.rnd, self.org)
        svc.grade_review(self.ra, self.org, scores=self.scores(self.rnd, 9, 8, 4), now=self.after)  # 21
        svc.grade_review(self.rb, self.rev, scores=self.scores(self.rnd, 5, 5, 5), now=self.after)
        svc.grade_review(self.rb, self.org, scores=self.scores(self.rnd, 5, 5, 5), now=self.after)
        self.assertEqual(svc.approve_results(self.rnd, self.org), 2)
        self.ra.refresh_from_db()
        self.assertEqual(str(self.ra.final_score), "20.00")  # (19 + 21) / 2
        self.assertEqual(points_total(season=self.season, module=Module.KITOBXONLIK, subject_type="user",
                                      subject_id=self.a.pk), 20)
        card = svc.personal_card(self.season, self.a)
        self.assertEqual(card["season_points"], 20)
        self.assertEqual(len(card["reviews"][0]["grades"]), 2)
        self.assertNotIn("reviewer", card["reviews"][0]["grades"][0])
        with self.assertRaisesMessage(svc.RuleError, "baholash bosqichida emas"):
            svc.grade_review(self.ra, self.rev, scores=self.scores(self.rnd, 1, 1, 1), now=self.after)

    def test_review_locked_once_graded(self):
        svc.grant_extension(self.rnd, self.org, self.a, until=self.rnd.reading_ends + timedelta(days=3),
                            reason="Safar")
        svc.start_grading(self.rnd, self.org, now=self.after)
        svc.grade_review(self.rb, self.rev, scores=self.scores(self.rnd, 5, 5, 5), now=self.after)
        # A ning muddati uzaytirilgan — hali baholab bo'lmaydi, lekin u tahrirlay oladi
        with self.assertRaisesMessage(svc.RuleError, "hali tugamagan"):
            svc.grade_review(self.ra, self.rev, scores=self.scores(self.rnd, 5, 5, 5), now=self.after)
        svc.submit_review(self.rnd, self.a, text=LONG + "!", now=self.after)
        with self.assertRaisesMessage(svc.RuleError, "baholanmoqda"):
            svc.submit_review(self.rnd, self.b, text=LONG, now=self.after - timedelta(days=2))


class ApiTests(Base):
    def setUp(self):
        super().setUp()
        self.api = APIClient()

    def as_(self, user):
        self.api.force_authenticate(user)
        return self.api

    def test_employee_flow_and_privacy(self):
        rnd = self.new_round()
        # qoralama tur xodimga ko'rinmaydi
        self.assertEqual(self.as_(self.a).get("/api/kitob/rounds/").data, [])
        self.as_(self.org).post(f"/api/kitob/rounds/{rnd.pk}/start-voting/",
                                {"vote_ends": (timezone.now() + timedelta(days=2)).isoformat()}, format="json")
        r = self.as_(self.a).post(f"/api/kitob/rounds/{rnd.pk}/vote/", {"book_id": self.book1.pk}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIsNone(r.data["votes"])  # ovozlar ovoz berish davomida yashirin
        self.assertEqual(r.data["my_vote"], self.book1.pk)
        # kitob hali ochilmagan
        self.assertEqual(self.api.get(f"/api/kitob/rounds/{rnd.pk}/book/").status_code, 400)

        self.as_(self.org).post(f"/api/kitob/rounds/{rnd.pk}/close-voting/", format="json")
        r = self.as_(self.a).get(f"/api/kitob/rounds/{rnd.pk}/book/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        # PDF ochiq /media/ manzilida yo'q
        self.assertNotIn("pdf", str(self.api.get(f"/api/kitob/rounds/{rnd.pk}/").data["selected_book"]))

        r = self.api.post(f"/api/kitob/rounds/{rnd.pk}/my-review/", {"text": LONG}, format="multipart")
        self.assertEqual(r.status_code, 200, r.data)
        self.as_(self.b).post(f"/api/kitob/rounds/{rnd.pk}/my-review/", {"text": LONG}, format="multipart")

        # tekshiruvchi muallifni ko'radi (baho beradigan u); oddiy xodimga ro'yxat yopiq
        ReadingRound.objects.filter(pk=rnd.pk).update(reading_ends=timezone.now() - timedelta(minutes=1))
        self.as_(self.org).post(f"/api/kitob/rounds/{rnd.pk}/start-grading/")
        rows = self.as_(self.rev).get(f"/api/kitob/rounds/{rnd.pk}/reviews/").data
        self.assertEqual({r["author"]["name"] for r in rows}, {"Ali", "Bek"})
        self.assertEqual(self.as_(self.a).get(f"/api/kitob/rounds/{rnd.pk}/reviews/").status_code, 403)

        crit = rnd.criteria.all()
        for row in rows:
            r = self.as_(self.rev).post(f"/api/kitob/reviews/{row['id']}/grade/", {
                "scores": [{"criterion_id": c.pk, "points": 4} for c in crit], "comment": "Yaxshi"},
                format="json")
            self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.as_(self.org).post(f"/api/kitob/rounds/{rnd.pk}/approve/").data["approved"], 2)
        card = self.as_(self.a).get("/api/kitob/my-card/").data
        self.assertEqual(card["season_points"], 12)

        # reyting jadvali yopiq, keyin ochiladi
        self.assertEqual(self.api.get("/api/kitob/leaderboard/").status_code, 403)
        SeasonConfig.objects.create(season=self.season, leaderboard_public=True)
        lb = self.api.get("/api/kitob/leaderboard/").data
        self.assertEqual([x["points"] for x in lb], [12, 12])
        self.assertEqual([x["place"] for x in lb], [1, 1])

    def test_review_file_access(self):
        rnd = self.to_reading(self.new_round(), [(self.a, self.book1)])
        Review.objects.all().delete()
        rv = svc.submit_review(rnd, self.a, file=SimpleUploadedFile("izoh.pdf", b"%PDF x"),
                               now=rnd.reading_starts + timedelta(hours=1))
        self.assertEqual(self.as_(self.a).get(f"/api/kitob/reviews/{rv.pk}/file/").status_code, 200)
        self.assertEqual(self.as_(self.b).get(f"/api/kitob/reviews/{rv.pk}/file/").status_code, 403)
        self.assertEqual(self.as_(self.rev).get(f"/api/kitob/reviews/{rv.pk}/file/").status_code, 200)
