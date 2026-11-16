"""Serverga chiqarish bilan bog'liq qismlar: bosh admin buyrug'i, Brevo pochta, pochta xatosi."""
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Branch, Employee, User
from core.models import Role, RoleAssignment, Season


class BootstrapAdminTests(TestCase):
    @mock.patch.dict("os.environ", {"ADMIN_EMAIL": "Boss@Colba.uz", "ADMIN_NAME": "Ali Valiyev", "ADMIN_PASSWORD": "Kuchli-Parol-123"})
    def test_creates_admin_season_and_is_idempotent(self):
        call_command("bootstrap_admin", stdout=mock.MagicMock())
        call_command("bootstrap_admin", stdout=mock.MagicMock())  # takror — xatosiz
        emp = Employee.objects.get(email="boss@colba.uz")
        self.assertEqual(emp.full_name, "Ali Valiyev")
        self.assertEqual(User.objects.filter(employee=emp).count(), 1)
        self.assertTrue(RoleAssignment.objects.filter(user__employee=emp, role=Role.ADMIN).exists())
        self.assertEqual(Season.objects.filter(is_active=True).count(), 1)
        su = User.objects.get(username="admin")
        self.assertTrue(su.is_superuser and su.check_password("Kuchli-Parol-123"))

    @mock.patch.dict("os.environ", {"ADMIN_EMAIL": ""})
    def test_without_email_only_season(self):
        call_command("bootstrap_admin", stdout=mock.MagicMock())
        self.assertFalse(Employee.objects.exists())
        self.assertTrue(Season.objects.filter(is_active=True).exists())


@override_settings(BREVO_API_KEY="test-key", DEFAULT_FROM_EMAIL="Colba <bot@colba.uz>",
                   EMAIL_BACKEND="core.email_backends.BrevoEmailBackend")
class BrevoTests(TestCase):
    def test_sends_via_http_api(self):
        with mock.patch("core.email_backends.requests.post") as post:
            post.return_value.raise_for_status.return_value = None
            sent = mail.send_mail("Mavzu", "Matn", None, ["x@y.uz"])
        self.assertEqual(sent, 1)
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["sender"], {"email": "bot@colba.uz", "name": "Colba"})
        self.assertEqual(payload["to"], [{"email": "x@y.uz"}])
        self.assertEqual(post.call_args.kwargs["headers"]["api-key"], "test-key")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="127.0.0.1", EMAIL_PORT=1)
class MailFailureTests(TestCase):
    def test_login_code_mail_failure_returns_clear_error(self):
        Employee.objects.create(full_name="X", branch=Branch.objects.create(name="F"), email="x@colba.uz")
        r = APIClient().post("/api/auth/email/request-code/", {"email": "x@colba.uz"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("pochta", r.data["detail"])
