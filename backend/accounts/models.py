import re

from django.contrib.auth.models import AbstractUser
from django.db import models


def normalize_phone(value) -> str:
    """Telefonni +998XXXXXXXXX ko'rinishiga keltiradi. Aniqlab bo'lmasa — bo'sh satr."""
    if value is None:
        return ""
    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) == 12 and digits.startswith("998"):
        return "+" + digits
    return ""


def normalize_email(value) -> str:
    return (str(value).strip().lower() if value else "")


def normalize_telegram_username(value) -> str:
    return (str(value).strip().lstrip("@").lower() if value else "")


def mask_phone(phone: str) -> str:
    return f"****{phone[-4:]}" if phone else ""


class Branch(models.Model):
    name = models.CharField("nomi", max_length=150, unique=True)

    class Meta:
        verbose_name = "filial"
        verbose_name_plural = "filiallar"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Employee(models.Model):
    """Xodimlar ro'yxati (Excel'dan yuklanadi). Faqat shu ro'yxatdagilar akkaunt ocha oladi."""

    full_name = models.CharField("F.I.Sh.", max_length=200)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, verbose_name="filial")
    position = models.CharField("lavozim", max_length=150, blank=True)
    phone = models.CharField("telefon", max_length=13, blank=True, db_index=True)
    email = models.EmailField("email", blank=True, db_index=True)
    telegram_username = models.CharField("Telegram username", max_length=64, blank=True, db_index=True)
    is_active = models.BooleanField("ishlayapti", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "xodim"
        verbose_name_plural = "xodimlar"
        ordering = ["full_name"]
        constraints = [
            models.UniqueConstraint(fields=["phone"], condition=~models.Q(phone=""),
                                    name="unique_employee_phone"),
            models.UniqueConstraint(fields=["email"], condition=~models.Q(email=""),
                                    name="unique_employee_email"),
            models.UniqueConstraint(fields=["telegram_username"],
                                    condition=~models.Q(telegram_username=""),
                                    name="unique_employee_telegram"),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.branch})"

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        self.email = normalize_email(self.email)
        self.telegram_username = normalize_telegram_username(self.telegram_username)
        super().save(*args, **kwargs)


class User(AbstractUser):
    """Platforma akkaunti. Xodimga bog'langan bo'ladi (admin va tasdiq kutayotganlar bundan mustasno)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Tasdiq kutilmoqda"
        ACTIVE = "active", "Faol"
        BLOCKED = "blocked", "Bloklangan"

    employee = models.OneToOneField(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="user",
        verbose_name="xodim",
    )
    status = models.CharField("holati", max_length=10, choices=Status.choices, default=Status.PENDING)
    display_name = models.CharField("ko'rinadigan ism", max_length=200, blank=True)
    avatar = models.ImageField("rasm", upload_to="avatars/", blank=True)

    class Meta:
        verbose_name = "foydalanuvchi"
        verbose_name_plural = "foydalanuvchilar"

    def __str__(self):
        if self.employee_id:
            return self.employee.full_name
        return self.display_name or self.username

    @property
    def can_login(self) -> bool:
        if self.status != self.Status.ACTIVE or not self.is_active:
            return False
        if self.employee_id and not self.employee.is_active:
            return False
        return True


class AuthIdentity(models.Model):
    """Kirish usuli: bitta akkauntga bir nechta (Telegram, Google, email) bog'lanadi."""

    class Provider(models.TextChoices):
        EMAIL = "email", "Email"
        GOOGLE = "google", "Google"
        TELEGRAM = "telegram", "Telegram"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="identities")
    provider = models.CharField(max_length=10, choices=Provider.choices)
    uid = models.CharField("tashqi ID", max_length=255)
    extra = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "kirish usuli"
        verbose_name_plural = "kirish usullari"
        constraints = [
            models.UniqueConstraint(fields=["provider", "uid"], name="unique_identity"),
        ]

    def __str__(self):
        return f"{self.get_provider_display()}: {self.uid}"


class EmailLoginCode(models.Model):
    """Email orqali kirish uchun bir martalik kod (kodning o'zi emas, xeshi saqlanadi)."""

    email = models.EmailField(db_index=True)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "email kodi"
        verbose_name_plural = "email kodlari"
