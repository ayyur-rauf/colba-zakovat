from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Module(models.TextChoices):
    CORE = "core", "Umumiy"
    ZAKOVAT = "zakovat", "Zakovat"
    KITOBXONLIK = "kitobxonlik", "Kitobxonlik"
    MUNOZARA = "munozara", "Munozara"
    SPORT = "sport", "Sport"


class Season(models.Model):
    """Mavsum = o'quv yili. Bir vaqtda faqat bitta faol mavsum bo'ladi."""

    name = models.CharField("nomi", max_length=50, unique=True, help_text="Masalan: 2026–2027")
    start_date = models.DateField("boshlanishi")
    end_date = models.DateField("tugashi")
    is_active = models.BooleanField("faol", default=False)

    class Meta:
        verbose_name = "mavsum"
        verbose_name_plural = "mavsumlar"
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"], condition=Q(is_active=True), name="only_one_active_season"
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if not (self.start_date and self.end_date):
            return
        if self.start_date >= self.end_date:
            raise ValidationError("Mavsum boshlanishi tugashidan oldin bo'lishi kerak.")
        overlap = Season.objects.exclude(pk=self.pk).filter(
            start_date__lte=self.end_date, end_date__gte=self.start_date
        )
        if overlap.exists():
            raise ValidationError(f"Mavsum boshqa mavsum bilan ustma-ust tushadi: {overlap.first()}")
        if self.is_active and Season.objects.exclude(pk=self.pk).filter(is_active=True).exists():
            raise ValidationError("Faol mavsum allaqachon bor. Avval uni nofaol qiling.")

    @classmethod
    def current(cls):
        return cls.objects.filter(is_active=True).first()


class Role(models.TextChoices):
    ADMIN = "admin", "Bosh admin"
    TG_MEMBER = "tg_member", "Tashkiliy guruh a'zosi"
    HOST = "host", "Boshlovchi"
    SECOND = "second", "Sekundant"
    SCORER = "scorer", "Hisob hay'ati"
    ORGANIZER = "organizer", "Tashkilotchi"
    REVIEWER = "reviewer", "Tekshiruvchi"


class RoleAssignment(models.Model):
    """Rol modul va (ixtiyoriy) mavsum doirasida beriladi.

    season bo'sh bo'lsa — rol barcha mavsumlarga amal qiladi.
    Jamoa sardori bu yerda emas: u jamoa modelidan kelib chiqadi.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="role_assignments",
        verbose_name="foydalanuvchi",
    )
    role = models.CharField("rol", max_length=20, choices=Role.choices)
    module = models.CharField("modul", max_length=20, choices=Module.choices, default=Module.CORE)
    season = models.ForeignKey(
        Season, on_delete=models.CASCADE, null=True, blank=True, verbose_name="mavsum"
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name="kim berdi",
    )
    created_at = models.DateTimeField("berilgan vaqti", auto_now_add=True)

    class Meta:
        verbose_name = "rol"
        verbose_name_plural = "rollar"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role", "module", "season"], name="unique_role_assignment"
            ),
        ]

    def __str__(self):
        scope = f" / {self.season}" if self.season_id else ""
        return f"{self.user} — {self.get_role_display()} ({self.get_module_display()}{scope})"


class PointsEntry(models.Model):
    """Ball reestri. Yozuvlar o'chirilmaydi va o'zgartirilmaydi — tuzatish yangi yozuv bilan.

    subject: kimga — jamoa (zakovat) yoki xodim (kitobxonlik). Modul ilovalari core'ga
    bog'lanmasligi uchun havola (turi + ID) ko'rinishida saqlanadi.
    """

    class Subject(models.TextChoices):
        TEAM = "team", "Jamoa"
        USER = "user", "Xodim"

    season = models.ForeignKey(Season, on_delete=models.PROTECT, verbose_name="mavsum")
    module = models.CharField("modul", max_length=20, choices=Module.choices)
    subject_type = models.CharField("kimga (turi)", max_length=10, choices=Subject.choices)
    subject_id = models.PositiveBigIntegerField("kimga (ID)")
    amount = models.IntegerField("ball")
    reason_type = models.CharField("sabab turi", max_length=50, help_text="masalan: zakovat.game")
    reason_id = models.CharField("sabab ID", max_length=64, blank=True)
    note = models.CharField("izoh", max_length=300, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name="kim kiritdi",
    )
    created_at = models.DateTimeField("vaqti", default=timezone.now)

    class Meta:
        verbose_name = "ball yozuvi"
        verbose_name_plural = "ball reestri"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["season", "module", "subject_type", "subject_id"])]

    def __str__(self):
        return f"{self.get_subject_type_display()} #{self.subject_id}: {self.amount:+d} ({self.reason_type})"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Ball yozuvini o'zgartirib bo'lmaydi — tuzatuvchi yozuv qo'shing.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Ball yozuvini o'chirib bo'lmaydi — tuzatuvchi yozuv qo'shing.")


class AuditLog(models.Model):
    """Muhim amallar jurnali: kim, qachon, nima edi, nima bo'ldi. Faqat qo'shiladi."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name="kim",
    )
    action = models.CharField("amal", max_length=100)
    object_type = models.CharField("obyekt turi", max_length=100, blank=True)
    object_id = models.CharField("obyekt ID", max_length=64, blank=True)
    before = models.JSONField("oldin", null=True, blank=True)
    after = models.JSONField("keyin", null=True, blank=True)
    note = models.TextField("izoh", blank=True)
    created_at = models.DateTimeField("vaqti", default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "jurnal yozuvi"
        verbose_name_plural = "harakatlar jurnali"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.actor} {self.action}"


class Announcement(models.Model):
    """Tashkilotchilardan e'lon. module bo'sh bo'lsa — umumiy e'lon."""

    title = models.CharField("sarlavha", max_length=200)
    body = models.TextField("matn", blank=True)
    module = models.CharField("modul", max_length=20, choices=Module.choices, default=Module.CORE)
    pinned = models.BooleanField("yuqorida mahkamlangan", default=False)
    is_active = models.BooleanField("ko'rinadi", default=True)
    expires_at = models.DateTimeField("ko'rinish muddati", null=True, blank=True,
                                      help_text="Bo'sh bo'lsa — qo'lda o'chirilguncha ko'rinadi")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                               related_name="+", verbose_name="muallif")
    created_at = models.DateTimeField("yaratilgan", default=timezone.now)

    class Meta:
        verbose_name = "e'lon"
        verbose_name_plural = "e'lonlar"
        ordering = ["-pinned", "-created_at"]

    def __str__(self):
        return self.title
