from django.test import TestCase

from accounts.models import User


class ZakovatAdminTests(TestCase):
    def test_pages_render(self):
        admin = User.objects.create(username="a", is_staff=True, is_superuser=True, status="active")
        self.client.force_login(admin)
        for url in ("/admin/zakovat/team/", "/admin/zakovat/game/", "/admin/zakovat/game/add/",
                    "/admin/zakovat/appeal/", "/admin/zakovat/question/add/", "/admin/core/season/",
                    "/admin/core/pointsentry/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
