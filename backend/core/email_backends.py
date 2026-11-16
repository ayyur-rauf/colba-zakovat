"""Brevo (sendinblue) HTTP API orqali xat yuborish.

Nega HTTP: Railway kabi platformalarda chiquvchi SMTP portlari tarif bo'yicha yopiq bo'lishi mumkin.
Brevo bepul tarifida kuniga 300 ta xat, domen shart emas — bitta yuboruvchi emailni tasdiqlash kifoya.

Sozlash (.env yoki Railway Variables):
    BREVO_API_KEY=xkeysib-...
    DEFAULT_FROM_EMAIL=Colba platformasi <siz-tasdiqlagan@email.uz>
"""
import logging
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

log = logging.getLogger(__name__)
API_URL = "https://api.brevo.com/v3/smtp/email"


class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        sent = 0
        name, sender = parseaddr(settings.DEFAULT_FROM_EMAIL)
        for msg in email_messages:
            payload = {
                "sender": {"email": sender, "name": name or "Colba"},
                "to": [{"email": addr} for addr in msg.to],
                "subject": msg.subject,
                "textContent": msg.body,
            }
            try:
                r = requests.post(API_URL, json=payload, timeout=15,
                                  headers={"api-key": settings.BREVO_API_KEY, "accept": "application/json"})
                r.raise_for_status()
                sent += 1
            except requests.RequestException as exc:
                log.error("Brevo orqali xat yuborilmadi: %s %s", exc, getattr(exc.response, "text", "")[:300])
                if not self.fail_silently:
                    raise
        return sent
