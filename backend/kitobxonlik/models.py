"""Kitobxonlik moduli: ovoz berish → o'qish (10 kun) → izoh → baholash → ball."""
from datetime import timedelta

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator
from django.db import models

from core.models import Season

class PrivateStorage(FileSystemStorage):
    """PDF kitoblar va izoh fayllari ochiq /media/ orqali berilmaydi — faqat API orqali,
    kirgan xodimga. Joylashuv har safar sozlamadan o'qiladi (testlarda almashtirish uchun)."""

    @property
    def base_location(self):
        return str(settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self):
        import os
        return os.path.abspath(self.base_location)

    @property
    def base_url(self):
        return None


_storage = PrivateStorage()


def _private_storage():
    return _storage


class SeasonConfig(models.Model):
    season = models.OneToOneField(Season, on_delete=models.CASCADE, related_name="kitobxonlik_config")
    leaderboard_public = models.BooleanField("reyting jadvali hammaga ochiq", default=False)

    class Meta:
        verbose_name = "kitobxonlik sozlamasi"
        verbose_name_plural = "kitobxonlik sozlamalari"

    def __str__(self):
        return f"{self.season}"


class Book(models.Model):
    title = models.CharField("nomi", max_length=200)
    author = models.CharField("muallif", max_length=200)
    description = models.TextField("qisqa tavsif", blank=True)
    cover = models.ImageField("muqova", upload_to="kitobxonlik/covers/", blank=True)
    pdf = models.FileField("PDF", storage=_private_storage, upload_to="books/",
                           validators=[FileExtensionValidator(["pdf"])])
    rights_confirmed = models.BooleanField(
        "tarqatish huquqi bor", default=False,
        help_text="Mualliflik muddati o'tgan, ruxsat olingan yoki sotib olingan nusxa")
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name="+", verbose_name="kim qo'shdi")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "kitob"
        verbose_name_plural = "kitoblar"
        ordering = ["title"]

    def __str__(self):
        return f"{self.author} — {self.title}"


class ReadingRound(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        VOTING = "voting", "Ovoz berish"
        READING = "reading", "O'qish"
        GRADING = "grading", "Baholash"
        DONE = "done", "Yakunlangan"

    season = models.ForeignKey(Season, on_delete=models.PROTECT, related_name="reading_rounds",
                               verbose_name="mavsum")
    title = models.CharField("nomi", max_length=150)
    status = models.CharField("holati", max_length=10, choices=Status.choices, default=Status.DRAFT)
    candidates = models.ManyToManyField(Book, related_name="rounds", verbose_name="nomzod kitoblar")
    vote_ends = models.DateTimeField("ovoz berish tugashi", null=True, blank=True)
    reading_days = models.PositiveSmallIntegerField("o'qish muddati (kun)", default=10)
    reading_starts = models.DateTimeField("o'qish boshlanishi", null=True, blank=True)
    reading_ends = models.DateTimeField("izoh yuborish muddati", null=True, blank=True)
    selected_book = models.ForeignKey(Book, on_delete=models.PROTECT, null=True, blank=True,
                                      related_name="+", verbose_name="tanlangan kitob")
    min_review_length = models.PositiveIntegerField("izoh minimal uzunligi (belgi)", default=500)
    reviewers_per_review = models.PositiveSmallIntegerField("bir izohni nechta tekshiruvchi baholaydi",
                                                            default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "kitobxonlik turi"
        verbose_name_plural = "kitobxonlik turlari"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def deadline_for(self, user):
        """Shaxsiy muddat: umumiy muddat yoki berilgan uzaytirish (qaysi biri kech bo'lsa)."""
        if self.reading_ends is None:
            return None
        ext = self.extensions.filter(user=user).order_by("-until").first()
        return max(self.reading_ends, ext.until) if ext else self.reading_ends


class Criterion(models.Model):
    round = models.ForeignKey(ReadingRound, on_delete=models.CASCADE, related_name="criteria")
    name = models.CharField("mezon", max_length=150)
    max_points = models.PositiveSmallIntegerField("maksimal ball")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "baholash mezoni"
        verbose_name_plural = "baholash mezonlari"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.name} (0–{self.max_points})"


class Vote(models.Model):
    round = models.ForeignKey(ReadingRound, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ovoz"
        verbose_name_plural = "ovozlar"
        constraints = [models.UniqueConstraint(fields=["round", "user"], name="one_vote_per_round")]


class Extension(models.Model):
    """Alohida xodimga izoh yuborish muddatini uzaytirish."""

    round = models.ForeignKey(ReadingRound, on_delete=models.CASCADE, related_name="extensions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+",
                             verbose_name="xodim")
    until = models.DateTimeField("yangi muddat")
    reason = models.CharField("sabab", max_length=300)
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "muddat uzaytirish"
        verbose_name_plural = "muddat uzaytirishlar"


REVIEW_FILE_TYPES = ["pdf", "docx", "doc", "jpg", "jpeg", "png"]


class Review(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Yuborilgan"
        APPROVED = "approved", "Baholangan"

    round = models.ForeignKey(ReadingRound, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reviews",
                             verbose_name="xodim")
    text = models.TextField("izoh matni", blank=True)
    file = models.FileField("fayl", storage=_private_storage, upload_to="reviews/", blank=True,
                            validators=[FileExtensionValidator(REVIEW_FILE_TYPES)])
    status = models.CharField("holati", max_length=10, choices=Status.choices, default=Status.SUBMITTED)
    final_score = models.DecimalField("yakuniy ball", max_digits=6, decimal_places=2, null=True, blank=True)
    submitted_at = models.DateTimeField("yuborilgan")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "izoh"
        verbose_name_plural = "izohlar"
        constraints = [models.UniqueConstraint(fields=["round", "user"], name="one_review_per_round")]

    def __str__(self):
        return f"{self.user} — {self.round}"


class Grade(models.Model):
    """Bitta tekshiruvchining bitta izohga bergan bahosi."""

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="grades")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+",
                                 verbose_name="tekshiruvchi")
    comment = models.TextField("xodimga izoh", blank=True)
    total = models.PositiveSmallIntegerField("jami")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "baho"
        verbose_name_plural = "baholar"
        constraints = [models.UniqueConstraint(fields=["review", "reviewer"], name="one_grade_per_reviewer")]


class GradeScore(models.Model):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="scores")
    criterion = models.ForeignKey(Criterion, on_delete=models.CASCADE)
    points = models.PositiveSmallIntegerField("ball")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["grade", "criterion"], name="one_score_per_criterion")]


def default_reading_ends(start, days):
    return start + timedelta(days=days)
