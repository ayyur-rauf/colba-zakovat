import hashlib
import hmac
import re
import time
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts import auth_services as svc
from accounts.models import AuthIdentity, Branch, Employee, User

BOT_TOKEN = "123456:TEST"


def telegram_payload(tg_id=111, username="vali", auth_date=None, token=BOT_TOKEN):
    data = {"id": str(tg_id), "first_name": "Vali", "username": username,
            "auth_date": str(auth_date or int(time.time()))}
    check = "\n".join(f"{k}={data[k]}" for k in sorted(data))
    data["hash"] = hmac.new(hashlib.sha256(token.encode()).digest(), check.encode(),
                            hashlib.sha256).hexdigest()
    return data


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN, GOOGLE_CLIENT_IDS=["web-client"],
                   EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        branch = Branch.objects.create(name="Chilonzor")
        self.vali = Employee.objects.create(full_name="Aliyev Vali", branch=branch,
                                            email="vali@colba.uz", telegram_username="vali")

    # ---------- Telegram imzosi
    def test_telegram_signature_valid(self):
        self.assertEqual(svc.verify_telegram(telegram_payload())["id"], "111")

    def test_telegram_signature_tampered(self):
        data = telegram_payload()
        data["id"] = "999"
        with self.assertRaises(svc.AuthError):
            svc.verify_telegram(data)

    def test_telegram_wrong_bot_token(self):
        with self.assertRaises(svc.AuthError):
            svc.verify_telegram(telegram_payload(token="other:TOKEN"))

    def test_telegram_expired(self):
        with self.assertRaises(svc.AuthError):
            svc.verify_telegram(telegram_payload(auth_date=int(time.time()) - 2 * 86400))

    # ---------- Telegram orqali kirish
    def test_telegram_login_known_employee_gets_tokens(self):
        r = self.client.post("/api/auth/telegram/", telegram_payload(), format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["status"], "active")
        self.assertEqual(r.data["user"]["employee"]["full_name"], "Aliyev Vali")
        me = self.client.get("/api/me/", HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        self.assertEqual(me.status_code, 200)

    def test_telegram_login_unknown_is_pending_without_tokens(self):
        r = self.client.post("/api/auth/telegram/", telegram_payload(tg_id=5, username="begona"),
                             format="json")
        self.assertEqual(r.status_code, 202)
        self.assertEqual(r.data["status"], "pending")
        self.assertNotIn("access", r.data)
        self.assertEqual(User.objects.get(identities__uid="5").status, User.Status.PENDING)

    # ---------- Email kodi
    def _code_from_mail(self):
        return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

    def test_email_code_flow(self):
        r = self.client.post("/api/auth/email/request-code/", {"email": "VALI@colba.uz"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        code = self._code_from_mail()
        r = self.client.post("/api/auth/email/verify/", {"email": "vali@colba.uz", "code": code},
                             format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["status"], "active")
        # kod ikkinchi marta ishlamaydi
        r = self.client.post("/api/auth/email/verify/", {"email": "vali@colba.uz", "code": code},
                             format="json")
        self.assertEqual(r.status_code, 400)

    def test_dev_code_never_returned_with_real_mail_backend(self):
        r = self.client.post("/api/auth/email/request-code/", {"email": "vali@colba.uz"}, format="json")
        self.assertNotIn("dev_code", r.data)  # locmem pochta — kod javobda yo'q

    @override_settings(DEBUG=True, EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_dev_code_returned_only_in_local_console_mode(self):
        r = self.client.post("/api/auth/email/request-code/", {"email": "vali@colba.uz"}, format="json")
        self.assertRegex(r.data["dev_code"], r"^\d{6}$")

    def test_email_unknown_gets_no_code_but_same_answer(self):
        r = self.client.post("/api/auth/email/request-code/", {"email": "x@y.uz"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_wrong_code_attempts_limited(self):
        self.client.post("/api/auth/email/request-code/", {"email": "vali@colba.uz"}, format="json")
        real = self._code_from_mail()
        wrong = "000000" if real != "000000" else "111111"
        for _ in range(5):
            self.client.post("/api/auth/email/verify/", {"email": "vali@colba.uz", "code": wrong},
                             format="json")
        r = self.client.post("/api/auth/email/verify/", {"email": "vali@colba.uz", "code": real},
                             format="json")
        self.assertEqual(r.status_code, 400)

    # ---------- Google
    def test_google_login_matches_employee_by_email(self):
        info = {"sub": "g-1", "email": "vali@colba.uz", "email_verified": True, "aud": "web-client",
                "name": "Vali"}
        with mock.patch("google.oauth2.id_token.verify_oauth2_token", return_value=info):
            r = self.client.post("/api/auth/google/", {"id_token": "x"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)

    def test_google_wrong_audience_rejected(self):
        info = {"sub": "g-1", "email": "vali@colba.uz", "email_verified": True, "aud": "boshqa"}
        with mock.patch("google.oauth2.id_token.verify_oauth2_token", return_value=info):
            r = self.client.post("/api/auth/google/", {"id_token": "x"}, format="json")
        self.assertEqual(r.status_code, 400)

    # ---------- Bir akkauntga bir nechta usul
    def test_telegram_and_google_land_on_same_account(self):
        self.client.post("/api/auth/telegram/", telegram_payload(), format="json")
        info = {"sub": "g-1", "email": "vali@colba.uz", "email_verified": True, "aud": "web-client"}
        with mock.patch("google.oauth2.id_token.verify_oauth2_token", return_value=info):
            self.client.post("/api/auth/google/", {"id_token": "x"}, format="json")
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(AuthIdentity.objects.count(), 2)

    def test_linking_identity_already_used_by_other_account(self):
        other = User.objects.create(username="o", status=User.Status.ACTIVE)
        AuthIdentity.objects.create(user=other, provider="telegram", uid="111")
        r = self.client.post("/api/auth/email/request-code/", {"email": "vali@colba.uz"}, format="json")
        r = self.client.post("/api/auth/email/verify/",
                             {"email": "vali@colba.uz", "code": self._code_from_mail()}, format="json")
        token = r.data["access"]
        r = self.client.post("/api/auth/telegram/", telegram_payload(), format="json",
                             HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(r.status_code, 400)

    # ---------- Ishdan ketgan / bloklangan
    def test_inactive_employee_token_rejected(self):
        r = self.client.post("/api/auth/telegram/", telegram_payload(), format="json")
        access, refresh = r.data["access"], r.data["refresh"]
        self.vali.is_active = False
        self.vali.save()
        self.assertEqual(self.client.get("/api/me/", HTTP_AUTHORIZATION=f"Bearer {access}").status_code, 401)
        self.assertEqual(self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json").status_code, 401)
        r = self.client.post("/api/auth/telegram/", telegram_payload(), format="json")
        self.assertEqual(r.status_code, 403)

    def test_blocked_user_cannot_login(self):
        self.client.post("/api/auth/telegram/", telegram_payload(), format="json")
        User.objects.update(status=User.Status.BLOCKED)
        r = self.client.post("/api/auth/telegram/", telegram_payload(), format="json")
        self.assertEqual(r.status_code, 403)
