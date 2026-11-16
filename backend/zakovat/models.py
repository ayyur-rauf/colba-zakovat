"""Zakovat ("Colba ligasi") modellari. Nizom bandlari: [N-x.y]."""
import re
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q

from core.models import Season


def team_name_key(name: str) -> str:
    """Nomlarni solishtirish uchun kalit: harf kattaligi, qo'shtirnoq va bo'sh joylar farqlanmaydi."""
    s = (name or "").lower()
    s = re.sub(r"[\"'«»“”„`ʻʼ‘’]", "", s)
    return " ".join(s.split())


# ------------------------------------------------------------------ jamoalar

class Team(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        PENDING = "pending", "Tasdiq kutilmoqda"
        ACTIVE = "active", "Faol"
        WITHDRAWN = "withdrawn", "Chiqib ketgan"
        DISQUALIFIED = "disqualified", "Chetlatilgan"

    season = models.ForeignKey(Season, on_delete=models.PROTECT, related_name="zakovat_teams",
                               verbose_name="mavsum")
    name = models.CharField("nomi", max_length=100)
    name_key = models.CharField(max_length=100, editable=False)
    captain = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                related_name="captained_teams", verbose_name="sardor")
    status = models.CharField("holati", max_length=15, choices=Status.choices, default=Status.DRAFT)
    previous = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="+", verbose_name="o'tgan mavsumdagi jamoa")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                    blank=True, related_name="+", verbose_name="kim tasdiqladi")
    approved_at = models.DateTimeField("tasdiqlangan vaqti", null=True, blank=True)
    status_reason = models.CharField("holat sababi", max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "jamoa"
        verbose_name_plural = "jamoalar"
        ordering = ["name"]
        constraints = [
            # [N-3.3] bir mavsumda bir xil nomli ikki jamoa bo'lmaydi
            models.UniqueConstraint(fields=["season", "name_key"], name="unique_team_name_in_season"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = " ".join(self.name.split())
        self.name_key = team_name_key(self.name)
        super().save(*args, **kwargs)

    @property
    def is_out(self):
        return self.status in (self.Status.WITHDRAWN, self.Status.DISQUALIFIED)


class TeamMember(models.Model):
    class Status(models.TextChoices):
        INVITED = "invited", "Taklif qilingan"
        ACTIVE = "active", "A'zo"
        DECLINED = "declined", "Rad etgan"
        LEFT = "left", "Chiqqan"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="members")
    season = models.ForeignKey(Season, on_delete=models.PROTECT, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                             related_name="zakovat_memberships", verbose_name="o'yinchi")
    status = models.CharField("holati", max_length=10, choices=Status.choices, default=Status.INVITED)
    joined_at = models.DateTimeField("qo'shilgan", null=True, blank=True)
    left_at = models.DateTimeField("chiqqan", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "jamoa a'zosi"
        verbose_name_plural = "jamoa a'zolari"
        constraints = [
            # [N-3.2] bir o'yinchi mavsumda faqat bitta jamoada
            models.UniqueConstraint(fields=["season", "user"], condition=Q(status="active"),
                                    name="one_active_team_per_season"),
        ]

    def __str__(self):
        return f"{self.user} → {self.team}"

    def save(self, *args, **kwargs):
        self.season_id = self.team.season_id
        super().save(*args, **kwargs)


# ------------------------------------------------------------------ o'yinlar

class Game(models.Model):
    class Kind(models.TextChoices):
        LEAGUE = "league", "Liga o'yini"
        TIEBREAK = "tiebreak", "Qo'shimcha o'yin"
        PRACTICE = "practice", "Mashq"

    class Status(models.TextChoices):
        PLANNED = "planned", "Rejalashtirilgan"
        REGISTRATION = "registration", "Ro'yxatdan o'tish ochiq"
        IN_PROGRESS = "in_progress", "O'yin ketmoqda"
        PRELIMINARY = "preliminary", "Dastlabki natija"
        FINAL = "final", "Yakuniy natija"
        CANCELLED = "cancelled", "Bekor qilingan"

    season = models.ForeignKey(Season, on_delete=models.PROTECT, related_name="zakovat_games",
                               verbose_name="mavsum")
    kind = models.CharField("turi", max_length=10, choices=Kind.choices, default=Kind.LEAGUE)
    title = models.CharField("nomi", max_length=150)
    starts_at = models.DateTimeField("boshlanish vaqti")
    venue = models.CharField("joyi", max_length=200, blank=True)
    max_teams = models.PositiveSmallIntegerField("maksimal jamoalar soni", null=True, blank=True,
                                                 help_text="[N-4.1] joy sig'imi bo'yicha; bo'sh — cheklovsiz")
    registration_deadline = models.DateTimeField("ro'yxatdan o'tish muddati", null=True, blank=True,
                                                 help_text="Bo'sh bo'lsa — o'yindan 1 kun oldin [N-3.2]")
    rounds = models.PositiveSmallIntegerField("raundlar soni", default=3)
    questions_per_round = models.PositiveSmallIntegerField("raunddagi savollar", default=12)
    status = models.CharField("holati", max_length=15, choices=Status.choices, default=Status.PLANNED)
    current_round = models.PositiveSmallIntegerField("joriy raund", default=0)
    current_question = models.PositiveSmallIntegerField("joriy savol", default=0)
    hide_standings = models.BooleanField("katta ekranda reytingni yashirish", default=False)
    tiebreak_for = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True,
                                     related_name="tiebreaks", verbose_name="qaysi o'yin uchun qo'shimcha")
    tiebreak_for_season = models.BooleanField("mavsum reytingi uchun qo'shimcha o'yin", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "o'yin"
        verbose_name_plural = "o'yinlar"
        ordering = ["starts_at"]

    def __str__(self):
        return f"{self.title} ({self.starts_at:%Y-%m-%d})"

    @property
    def total_questions(self) -> int:
        return self.rounds * self.questions_per_round

    @property
    def effective_deadline(self):
        return self.registration_deadline or (self.starts_at - timedelta(days=1))

    def round_of(self, number: int) -> int:
        return (number - 1) // self.questions_per_round + 1

    def first_question_of(self, round_no: int) -> int:
        return (round_no - 1) * self.questions_per_round + 1

    @property
    def gives_points(self) -> bool:
        return self.kind == self.Kind.LEAGUE


class GameRegistration(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ko'rib chiqilmoqda"
        APPROVED = "approved", "Tasdiqlangan"
        WAITLIST = "waitlist", "Navbatda"
        REJECTED = "rejected", "Rad etilgan"
        WITHDRAWN = "withdrawn", "Bekor qilingan"

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="registrations")
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="registrations")
    table_number = models.PositiveSmallIntegerField("stol raqami", null=True, blank=True)
    status = models.CharField("holati", max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "o'yinga ariza"
        verbose_name_plural = "o'yinga arizalar"
        ordering = ["created_at"]
        constraints = [models.UniqueConstraint(fields=["game", "team"], name="unique_game_team")]

    def __str__(self):
        return f"{self.team} → {self.game}"


class LineupEntry(models.Model):
    """Raunddagi tarkib [N-5.2]. from_question — o'yinchi qaysi savoldan ishtirok etdi [N-4.3]."""

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="lineup")
    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    round_no = models.PositiveSmallIntegerField("raund")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="o'yinchi")
    from_question = models.PositiveSmallIntegerField("qaysi savoldan")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "tarkib yozuvi"
        verbose_name_plural = "tarkib"
        constraints = [
            models.UniqueConstraint(fields=["game", "round_no", "user"], name="unique_lineup_player"),
        ]


# ------------------------------------------------------------------ savollar

class Question(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        EDITING = "editing", "Tahrirda"
        APPROVED = "approved", "Tasdiqlangan"
        USED = "used", "Ishlatilgan"

    text = models.TextField("savol")
    answer = models.CharField("javob", max_length=300)
    accepted_answers = models.TextField("qabul qilinadigan javoblar", blank=True,
                                        help_text="Har birini yangi qatorga yozing")
    comment = models.TextField("izoh", blank=True)
    source = models.TextField("manba", blank=True)
    topic = models.CharField("mavzu", max_length=100, blank=True)
    difficulty = models.PositiveSmallIntegerField("qiyinlik (1–5)", null=True, blank=True)
    media = models.FileField("rasm/audio", upload_to="zakovat/questions/", blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                               blank=True, related_name="+", verbose_name="muallif")
    status = models.CharField("holati", max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "savol"
        verbose_name_plural = "savollar banki"

    def __str__(self):
        return self.text[:80]


class GameQuestion(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="questions")
    number = models.PositiveSmallIntegerField("raqami")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        verbose_name = "o'yin savoli"
        verbose_name_plural = "o'yin savollari"
        ordering = ["number"]
        constraints = [models.UniqueConstraint(fields=["game", "number"], name="unique_game_question")]


# ------------------------------------------------------------------ javoblar va natijalar

class AnswerMark(models.Model):
    """Hisob hay'ati belgisi: jamoa N-savolga to'g'ri javob berdimi."""

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="marks")
    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    number = models.PositiveSmallIntegerField("savol raqami")
    correct = models.BooleanField("to'g'ri")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "javob belgisi"
        verbose_name_plural = "javob belgilari"
        constraints = [models.UniqueConstraint(fields=["game", "team", "number"], name="unique_mark")]


class Appeal(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ko'rib chiqilmoqda"
        ACCEPTED = "accepted", "Qabul qilindi"
        REJECTED = "rejected", "Rad etildi"

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="appeals")
    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    number = models.PositiveSmallIntegerField("savol raqami")
    content = models.TextField("e'tiroz mazmuni")
    evidence = models.TextField("dalillar")
    evidence_file = models.FileField("dalil fayli", upload_to="zakovat/appeals/", blank=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    status = models.CharField("holati", max_length=10, choices=Status.choices, default=Status.PENDING)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   blank=True, related_name="+")
    decision_reason = models.TextField("qaror sababi", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "apellyatsiya"
        verbose_name_plural = "apellyatsiyalar"
        ordering = ["created_at"]


class GameResult(models.Model):
    """Hisoblangan natija (dastlabki yoki yakuniy). Har qayta hisoblashda yangilanadi."""

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="results")
    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    points = models.PositiveSmallIntegerField("ball")
    rating_j = models.PositiveIntegerField("J (savollar reytingi)")
    eligible = models.BooleanField("hisobga olinadi", default=True)
    place = models.PositiveSmallIntegerField("o'rin", null=True, blank=True)
    tie_group = models.PositiveSmallIntegerField("teng guruh", null=True, blank=True,
                                                 help_text="Ball va J teng — qo'shimcha o'yin kerak")

    class Meta:
        verbose_name = "o'yin natijasi"
        verbose_name_plural = "o'yin natijalari"
        ordering = ["game", "place"]
        constraints = [models.UniqueConstraint(fields=["game", "team"], name="unique_game_result")]
