"""Kirish mantig'i: tashqi ID → akkaunt, xodimlar ro'yxati bo'yicha tekshiruv.

Qoidalar:
1. Kirish usuli (provider + uid) avval bog'langan bo'lsa — o'sha akkaunt.
2. Aks holda xodimlar ro'yxatidan qidiriladi: Google/email — email bo'yicha,
   Telegram — username bo'yicha. Topilsa, akkaunt faol holda yaratiladi (yoki
   xodimning mavjud akkauntiga bog'lanadi).
3. Topilmasa — akkaunt "tasdiq kutilmoqda" holatida yaratiladi; admin uni xodimga
   bog'lab faollashtiradi. Bunday akkauntga token berilmaydi.
4. Bloklangan, nofaol yoki ishdan ketgan xodimning akkauntiga kirish yo'q.
"""
import hashlib
import logging
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from core.services import log_action

from .models import (
    AuthIdentity, EmailLoginCode, Employee, User, normalize_email, normalize_telegram_username,
)


class AuthError(Exception):
    """Foydalanuvchiga ko'rsatiladigan kirish xatosi."""


@dataclass
class LoginResult:
    user: User
    created: bool

    @property
    def status(self):
        return "active" if self.user.can_login else self.user.status


# ---------------------------------------------------------------- Telegram

def verify_telegram(data: dict, bot_token: str | None = None, max_age: int | None = None) -> dict:
    """Telegram Login Widget ma'lumotini tekshiradi (https://core.telegram.org/widgets/login)."""
    bot_token = bot_token if bot_token is not None else settings.TELEGRAM_BOT_TOKEN
    max_age = max_age if max_age is not None else settings.TELEGRAM_AUTH_MAX_AGE
    if not bot_token:
        raise AuthError("Telegram orqali kirish sozlanmagan.")
    data = {k: str(v) for k, v in data.items() if v is not None}
    received_hash = data.pop("hash", "")
    if not received_hash or "id" not in data or "auth_date" not in data:
        raise AuthError("Telegram ma'lumoti to'liq emas.")
    check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data))
    secret = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise AuthError("Telegram imzosi noto'g'ri.")
    try:
        auth_date = int(data["auth_date"])
    except ValueError:
        raise AuthError("Telegram ma'lumoti noto'g'ri.")
    if time.time() - auth_date > max_age:
        raise AuthError("Telegram ma'lumoti eskirgan. Qaytadan kiring.")
    return data


# ---------------------------------------------------------------- Google

def verify_google(id_token_str: str) -> dict:
    """Google ID token'ni tekshiradi va {sub, email, name} qaytaradi."""
    if not settings.GOOGLE_CLIENT_IDS:
        raise AuthError("Google orqali kirish sozlanmagan.")
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    try:
        info = id_token.verify_oauth2_token(id_token_str, google_requests.Request())
    except ValueError:
        raise AuthError("Google tokeni yaroqsiz.")
    if info.get("aud") not in settings.GOOGLE_CLIENT_IDS:
        raise AuthError("Google tokeni boshqa ilova uchun berilgan.")
    if not info.get("email") or not info.get("email_verified"):
        raise AuthError("Google akkauntida tasdiqlangan email yo'q.")
    return {"sub": info["sub"], "email": normalize_email(info["email"]), "name": info.get("name", "")}


# ---------------------------------------------------------------- Email kodi

def _hash_code(email: str, code: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"{email}:{code}".encode(), hashlib.sha256).hexdigest()


def email_is_known(email: str) -> bool:
    return (Employee.objects.filter(email=email, is_active=True).exists()
            or AuthIdentity.objects.filter(provider=AuthIdentity.Provider.EMAIL, uid=email).exists())


def request_email_code(email: str, *, allow_unknown=False) -> str | None:
    """Kod yuboradi. Noma'lum email uchun hech narsa yubormaydi (lekin xatoni ham oshkor qilmaydi).

    Qaytaradi: yuborilgan kod (faqat mahalliy ishlab chiqishda ko'rsatish uchun) yoki None.
    """
    email = normalize_email(email)
    if not email:
        raise AuthError("Email kiritilmagan.")
    if not allow_unknown and not email_is_known(email):
        return None
    hour_ago = timezone.now() - timedelta(hours=1)
    if EmailLoginCode.objects.filter(email=email, created_at__gte=hour_ago).count() >= settings.EMAIL_CODE_MAX_PER_HOUR:
        raise AuthError("Juda ko'p urinish. Birozdan keyin qayta urinib ko'ring.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    EmailLoginCode.objects.filter(email=email, used_at__isnull=True).update(used_at=timezone.now())
    EmailLoginCode.objects.create(
        email=email, code_hash=_hash_code(email, code),
        expires_at=timezone.now() + timedelta(minutes=settings.EMAIL_CODE_TTL_MINUTES),
    )
    try:
        send_mail(
            "Colba platformasiga kirish kodi",
            f"Kirish kodingiz: {code}\nKod {settings.EMAIL_CODE_TTL_MINUTES} daqiqa amal qiladi.\n"
            "Agar siz so'ramagan bo'lsangiz, bu xatni e'tiborsiz qoldiring.",
            settings.DEFAULT_FROM_EMAIL, [email],
        )
    except Exception:  # noqa: BLE001 — pochta sozlanmagan yoki xizmat ishlamayapti
        logging.getLogger(__name__).exception("Kirish kodi yuborilmadi: %s", email)
        raise AuthError("Kodni yuborib bo'lmadi: pochta xizmati sozlanmagan yoki ishlamayapti. Admin bilan bog'laning.")
    return code


def dev_codes_visible() -> bool:
    """Pochta sozlanmagan mahalliy yoki sinov rejimida kod javobda qaytariladi.
    Haqiqiy serverda (DEBUG=0, TEST_MODE=0) hech qachon."""
    return (settings.DEBUG or getattr(settings, "TEST_MODE", False)) and \
        settings.EMAIL_BACKEND.endswith("console.EmailBackend")


def check_email_code(email: str, code: str) -> str:
    email = normalize_email(email)
    code = (code or "").strip()
    entry = (EmailLoginCode.objects
             .filter(email=email, used_at__isnull=True, expires_at__gt=timezone.now())
             .order_by("-created_at").first())
    if entry is None:
        raise AuthError("Kod topilmadi yoki muddati o'tgan. Yangi kod so'rang.")
    if entry.attempts >= settings.EMAIL_CODE_MAX_ATTEMPTS:
        raise AuthError("Urinishlar soni tugadi. Yangi kod so'rang.")
    if not hmac.compare_digest(entry.code_hash, _hash_code(email, code)):
        entry.attempts += 1
        entry.save(update_fields=["attempts"])
        raise AuthError("Kod noto'g'ri.")
    entry.used_at = timezone.now()
    entry.save(update_fields=["used_at"])
    return email


# ---------------------------------------------------------------- Akkauntni aniqlash

def _find_employee(provider, email, telegram_username):
    if provider in (AuthIdentity.Provider.GOOGLE, AuthIdentity.Provider.EMAIL) and email:
        return Employee.objects.filter(email=email).first()
    if provider == AuthIdentity.Provider.TELEGRAM and telegram_username:
        return Employee.objects.filter(telegram_username=telegram_username).first()
    return None


@transaction.atomic
def resolve_login(provider, uid, *, email="", telegram_username="", display_name="", extra=None) -> LoginResult:
    email = normalize_email(email)
    telegram_username = normalize_telegram_username(telegram_username)
    identity = AuthIdentity.objects.select_related("user").filter(provider=provider, uid=uid).first()
    created = False

    if identity:
        user = identity.user
    else:
        employee = _find_employee(provider, email, telegram_username)
        if employee is not None and hasattr(employee, "user"):
            user = employee.user
        else:
            user = User(
                username=f"u_{uuid.uuid4().hex[:12]}",
                employee=employee,
                display_name=(employee.full_name if employee else display_name)[:200],
                email=email,
                status=User.Status.ACTIVE if employee else User.Status.PENDING,
            )
            user.set_unusable_password()
            user.save()
            created = True
        identity = AuthIdentity.objects.create(user=user, provider=provider, uid=uid, extra=extra or {})
        log_action(user, "auth.identity_linked", identity,
                   after={"provider": provider, "new_user": created, "status": user.status})

    identity.last_used_at = timezone.now()
    identity.save(update_fields=["last_used_at"])
    return LoginResult(user=user, created=created)


@transaction.atomic
def link_identity(user, provider, uid, *, extra=None) -> AuthIdentity:
    """Kirgan foydalanuvchiga yangi kirish usulini bog'laydi."""
    existing = AuthIdentity.objects.filter(provider=provider, uid=uid).first()
    if existing:
        if existing.user_id == user.pk:
            return existing
        raise AuthError("Bu kirish usuli boshqa akkauntga bog'langan. Admin bilan bog'laning.")
    identity = AuthIdentity.objects.create(user=user, provider=provider, uid=uid, extra=extra or {})
    log_action(user, "auth.identity_linked", identity, after={"provider": provider})
    return identity


def issue_tokens(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}
