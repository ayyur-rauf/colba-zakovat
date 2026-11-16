"""Mahalliy ko'rib chiqish uchun demo ma'lumotlar. Faqat DEBUG=1 da ishlaydi.

    python manage.py seed_demo

Yaratadi: faol mavsum, 3 filial, 18 xodim, 4 jamoa, yakunlangan 1-tur (natija va ballar bilan),
ro'yxatdan o'tish ochiq 2-tur, admin akkaunti. Admin login va paroli `dev_login.txt` ga yoziladi.
Qayta ishga tushirilsa, demo ma'lumotlar o'chirilib yangidan yaratiladi.
"""
import secrets
from datetime import date, datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from django.core.files.base import ContentFile

from accounts.models import Branch, Employee, User
from kitobxonlik import services as ksvc
from kitobxonlik.models import Book, ReadingRound, SeasonConfig
from core.models import Module, PointsEntry, Role, RoleAssignment, Season
from zakovat import services as svc
from zakovat.models import Game, Team

DEMO_SEASON = "Demo 2026–2027"
NAMES = [
    "Aliyev Vali", "Karimova Laylo", "Toshmatov Jasur", "Rahimova Nilufar", "Qodirov Bekzod",
    "Yusupova Madina", "Ergashev Sardor", "Nazarova Dilnoza", "Xolmatov Aziz", "Saidova Gulnora",
    "Mirzayev Otabek", "Abdullayeva Zarina", "Sobirov Sherzod", "Hamidova Kamola", "Usmonov Akmal",
    "Tursunova Shahlo", "Ismoilov Doniyor", "Raximov Ulug'bek",
]
TEAMS = ["Bilimdonlar", "Aql charxi", "Colba yulduzlari", "Mantiq"]


def demo_pdf(title: str) -> bytes:
    """Bir sahifali oddiy PDF (demo kitob o'rniga)."""
    text = title.encode("latin-1", "replace").replace(b"(", b"[").replace(b")", b"]")
    stream = b"BT /F1 24 Tf 72 720 Td (" + text + b") Tj 0 -40 Td /F1 12 Tf (Demo kitob - haqiqiy matn emas) Tj ET"
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{off:010d} 00000 n \n".encode() for off in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


REVIEW_TEXT = ("Kitob menga juda katta taassurot qoldirdi. Asosiy qahramonning tanlovlari va ularning "
               "oqibatlari orqali muallif mas'uliyat haqida gapiradi. Ayniqsa ikkinchi qismdagi voqealar "
               "o'z ishimga ham qarashimni o'zgartirdi: o'quvchilar bilan muloqotda sabr va izchillik "
               "qanchalik muhimligini yana bir bor angladim. Kitobning tili sodda, lekin fikrlari chuqur. "
               "Hamkasblarimga ham o'qishni tavsiya qilaman, ayniqsa yosh o'qituvchilarga.")


class Command(BaseCommand):
    def _seed_kitobxonlik(self, season, admin, users, at):
        SeasonConfig.objects.update_or_create(season=season, defaults={"leaderboard_public": True})
        books = []
        for title, author in [("[Demo] O'tkan kunlar", "Abdulla Qodiriy"),
                              ("[Demo] Kecha va kunduz", "Cho'lpon"),
                              ("[Demo] Sariq devni minib", "Xudoyberdi To'xtaboyev"),
                              ("[Demo] Ufq", "Said Ahmad")]:
            pdf = ContentFile(demo_pdf(title), name="demo.pdf")
            books.append(ksvc.add_book(admin, title=title, author=author, pdf=pdf, rights_confirmed=True,
                                       description="Demo uchun yaratilgan kitob kartochkasi."))
        criteria = [{"name": "Mazmunni tushunish", "max_points": 10},
                    {"name": "Shaxsiy fikr va tahlil", "max_points": 10},
                    {"name": "Savodxonlik va uslub", "max_points": 5}]

        # Oktabr turi: to'liq o'tkazilgan
        r1 = ksvc.create_round(season, admin, title="Oktabr kitobi", book_ids=[b.pk for b in books[:3]],
                               criteria=criteria, min_review_length=300)
        t = at(2026, 10, 1, 9)
        ksvc.start_voting(r1, admin, vote_ends=t + timedelta(days=3), now=t)
        for i, u in enumerate(users[:12]):
            ksvc.cast_vote(r1, u, books[0] if i % 3 else books[1], now=t + timedelta(hours=i))
        ksvc.close_voting(r1, admin, now=t + timedelta(days=3))
        for i, u in enumerate(users[:9]):
            ksvc.submit_review(r1, u, text=REVIEW_TEXT, now=r1.reading_starts + timedelta(days=1 + i % 8))
        ksvc.start_grading(r1, admin, now=r1.reading_ends + timedelta(hours=1))
        crit = list(r1.criteria.all())
        for i, review in enumerate(r1.reviews.all()):
            pts = [(7 + i) % 11, (5 + 2 * i) % 11, (3 + i) % 6]
            ksvc.grade_review(review, admin, scores={c.pk: p for c, p in zip(crit, pts)},
                              comment="Fikrlar aniq, misollar ko'proq bo'lsa yanada yaxshi.",
                              now=r1.reading_ends + timedelta(hours=2))
        ksvc.approve_results(r1, admin)

        # Noyabr turi: ovoz berish ketmoqda
        r2 = ksvc.create_round(season, admin, title="Noyabr kitobi", book_ids=[b.pk for b in books[1:]],
                               criteria=criteria, min_review_length=300)
        now = timezone.now()
        ksvc.start_voting(r2, admin, vote_ends=now + timedelta(days=4), now=now)
        for i, u in enumerate(users[:7]):
            ksvc.cast_vote(r2, u, books[1 + i % 3], now=now)
    help = "Demo ma'lumotlar (faqat mahalliy ishlab chiqish uchun)."

    @transaction.atomic
    def handle(self, *args, **opts):
        if not settings.DEBUG:
            raise CommandError("Faqat DEBUG=1 bo'lganda ishlaydi.")
        tz = timezone.get_current_timezone()

        def at(*a):
            return datetime(*a, tzinfo=tz)

        # eski demo ma'lumotlarni tozalash (ball yozuvlari o'zgarmas, shuning uchun queryset bilan)
        old = Season.objects.filter(name=DEMO_SEASON).first()
        if old:
            PointsEntry.objects.filter(season=old)._raw_delete(PointsEntry.objects.db)
            ReadingRound.objects.filter(season=old).delete()
            Book.objects.filter(title__startswith="[Demo]").delete()
            for g in Game.objects.filter(season=old):
                g.results.all().delete(); g.marks.all().delete(); g.lineup.all().delete()
                g.appeals.all().delete(); g.registrations.all().delete()
            Game.objects.filter(season=old, tiebreak_for__isnull=False).delete()
            Game.objects.filter(season=old).delete()
            for t in Team.objects.filter(season=old):
                t.members.all().delete()
            Team.objects.filter(season=old).delete()
            old.delete()
        User.objects.filter(username__startswith="demo_").delete()
        Employee.objects.filter(email__endswith="@demo.colba.uz").delete()

        Season.objects.filter(is_active=True).update(is_active=False)
        season = Season.objects.create(name=DEMO_SEASON, start_date=date(2026, 9, 1),
                                       end_date=date(2027, 8, 31), is_active=True)

        admin, _ = User.objects.get_or_create(username="admin")
        password = secrets.token_urlsafe(12)
        admin.set_password(password)
        admin.is_staff = admin.is_superuser = True
        admin.status = User.Status.ACTIVE
        admin.display_name = "Bosh admin"
        admin.save()
        (settings.BASE_DIR / "dev_login.txt").write_text(
            f"Mahalliy admin panel: http://127.0.0.1:8100/admin/\nlogin: admin\nparol: {password}\n",
            encoding="utf-8")

        branches = [Branch.objects.get_or_create(name=n)[0] for n in ("Chilonzor", "Yunusobod", "Sergeli")]
        users = []
        for i, name in enumerate(NAMES):
            emp = Employee.objects.create(full_name=name, branch=branches[i % 3], position="O'qituvchi",
                                          email=f"xodim{i + 1}@demo.colba.uz")
            u = User(username=f"demo_{i + 1}", employee=emp, display_name=name, status=User.Status.ACTIVE)
            u.set_unusable_password()
            u.save()
            users.append(u)

        before = at(2026, 8, 25, 10)
        teams = []
        pos = 0
        for tname, size in zip(TEAMS, (5, 5, 4, 4)):
            members = users[pos:pos + size]
            pos += size
            team = svc.create_team(season, members[0], tname, now=before)
            for u in members[1:]:
                m = svc.invite_member(team, members[0], u, now=before)
                svc.respond_invite(m, u, True, now=before)
            svc.submit_team(team, members[0])
            svc.approve_team(team, admin)
            teams.append(team)

        games = svc.generate_league_schedule(season, admin, venue="Colba, Chilonzor filiali, majlislar zali",
                                             months={9, 10, 11, 12, 1, 2, 3, 4, 5})
        oct_game = next(g for g in games if g.starts_at.month == 10)
        nov_game = next(g for g in games if g.starts_at.month == 11)

        sep_game = next(g for g in games if g.starts_at.month == 9)

        def play(game, correct, appeal=None):
            svc.open_registration(game, admin)
            for t in correct:
                reg = svc.register_team(game, t, t.captain, now=game.starts_at - timedelta(days=3))
                svc.approve_registration(reg, admin)
            svc.start_game(game, admin)
            for t in correct:
                players = [m.user for m in t.members.filter(status="active")]
                for r in range(1, game.rounds + 1):
                    svc.set_current_question(game, admin, game.first_question_of(r))
                    for u in players[:4]:
                        svc.add_to_lineup(game, t, r, u, admin)
            for q in range(1, game.total_questions + 1):
                svc.set_current_question(game, admin, q)
                for t in correct:
                    svc.set_mark(game, t, q, q in correct[t], admin)
            svc.publish_preliminary(game, admin)
            if appeal:
                team, number = appeal
                a = svc.submit_appeal(game, team, team.captain, number=number,
                                      content="Javobimiz 'Amir Temur' edi, to'g'ri javob bilan bir xil ma'noda",
                                      evidence="Savol izohida ikkala nom ham keltirilgan")
                svc.decide_appeal(a, admin, accept=True, reason="Javob ma'nosi to'g'ri javobga mos")
            svc.finalize_game(game, admin)

        # 1-tur (sentyabr) va 2-tur (oktabr): to'liq o'tkazilgan
        play(sep_game, {
            teams[0]: {1, 2, 4, 6, 7, 10, 13, 14, 17, 19, 21, 24, 26, 29, 31, 34},
            teams[1]: {1, 3, 4, 7, 9, 13, 16, 19, 22, 25, 28, 33},
            teams[2]: {1, 2, 4, 5, 7, 8, 10, 13, 15, 19, 21, 24, 27, 30, 35},
            teams[3]: {1, 4, 7, 13, 19, 22, 25, 31, 34, 36},
        })
        play(oct_game, {
            teams[0]: {1, 2, 3, 5, 7, 8, 11, 13, 14, 15, 18, 20, 22, 25, 27, 30, 33, 35},
            teams[1]: {1, 2, 4, 5, 7, 9, 12, 13, 15, 16, 19, 20, 23, 25, 28, 31, 34, 36},
            teams[2]: {1, 3, 5, 6, 8, 13, 15, 17, 20, 21, 25, 26, 29},
            teams[3]: {1, 2, 5, 13, 15, 20, 25, 32},
        }, appeal=(teams[2], 30))

        # 2-tur (noyabr): 3 jamoa tasdiqlangan, o'yin hisob hay'ati sahifasidan boshlanadi
        svc.open_registration(nov_game, admin)
        for t in teams[:3]:
            reg = svc.register_team(nov_game, t, t.captain, now=nov_game.starts_at - timedelta(days=5))
            svc.approve_registration(reg, admin)

        # Sayt orqali kirish uchun demo tashkilotchi (email kod bilan)
        staff_emp = Employee.objects.create(full_name="Demo Tashkilotchi", branch=branches[0],
                                            position="Tashkiliy guruh", email="tg@demo.colba.uz")
        staff = User(username="demo_tg", employee=staff_emp, display_name=staff_emp.full_name,
                     status=User.Status.ACTIVE)
        staff.set_unusable_password()
        staff.save()
        for role, module in ((Role.TG_MEMBER, Module.ZAKOVAT), (Role.SCORER, Module.ZAKOVAT),
                             (Role.ORGANIZER, Module.KITOBXONLIK)):
            RoleAssignment.objects.create(user=staff, role=role, module=module, granted_by=admin)
        with open(settings.BASE_DIR / "dev_login.txt", "a", encoding="utf-8") as f:
            f.write("\nSayt (http://localhost:3100) — email kod bilan kirish:\n"
                    "  tashkilotchi / hisob hay'ati: tg@demo.colba.uz\n"
                    "  oddiy xodim (Bilimdonlar sardori): xodim1@demo.colba.uz\n"
                    "  Mahalliy rejimda kod sahifada avtomatik ko'rinadi.\n")

        self._seed_kitobxonlik(season, admin, users, at)

        self.stdout.write(self.style.SUCCESS(
            f"Demo tayyor: {len(users)} xodim, {len(teams)} jamoa, {len(games)} o'yin. "
            f"Admin login/parol: {settings.BASE_DIR / 'dev_login.txt'}"))
