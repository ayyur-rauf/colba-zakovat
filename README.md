# Colba platformasi

"Colba maktabi" xodimlari o'rtasidagi intellektual tadbirlar (Zakovat, Kitobxonlik, keyin Munozara va Sport) platformasi.
Talablar: [docs/TZ_v1.md](docs/TZ_v1.md).

## Tuzilma
```
backend/        Django + DRF (API va admin panel)
  config/       sozlamalar, URL'lar
  core/         mavsum, rollar, harakatlar jurnali
  accounts/     filial, xodimlar ro'yxati, akkaunt, kirish (Telegram, Google, email kod)
docs/           texnik topshiriq
```
web/            Next.js sayt (hisob hay'ati jadvali, katta ekran, kirish) — web/README.md
Keyingi qism: `mobile/` (Expo).

## Ishga tushirish (Windows, mahalliy)
```powershell
cd backend
python -m virtualenv .venv            # yoki: python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env                # SECRET_KEY ni to'ldiring, DEBUG=1
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py createsuperuser
.\.venv\Scripts\python manage.py runserver
```
Admin panel: http://127.0.0.1:8000/admin/

Testlar: `.\.venv\Scripts\python manage.py test`

## Xodimlar ro'yxatini yuklash
Excel (.xlsx), birinchi qator — sarlavhalar: **F.I.Sh.**, **Filial** (majburiy), Lavozim, Telefon, Email, Telegram.
- Admin panel: Xodimlar → "Excel'dan yuklash" (avval "Faqat tekshirish" bilan sinab ko'ring).
- Yoki buyruq: `python manage.py import_employees xodimlar.xlsx --dry-run`

Bitta qatorda xato bo'lsa ham, hech narsa saqlanmaydi. Hisobotda xato qatorlar raqami ko'rsatiladi.
Mavjud xodim telefon → email → Telegram bo'yicha topiladi va yangilanadi.

## Kirish qoidalari
| Holat | Natija |
|---|---|
| Kirish usuli avval bog'langan | O'sha akkaunt |
| Email (Google yoki kod) yoki Telegram username xodimlar ro'yxatida bor | Akkaunt faol, token beriladi |
| Ro'yxatda yo'q (Google yoki Telegram) | Akkaunt "tasdiq kutilmoqda", token berilmaydi. Admin xodimga bog'lab tasdiqlaydi |
| Ro'yxatda yo'q email | Kod yuborilmaydi (javob bir xil, email borligi oshkor qilinmaydi) |
| Bloklangan yoki xodim "ishlamaydi" | Kirish ham, eski token ham ishlamaydi |

Token bilan (`Authorization: Bearer ...`) shu endpointlarga murojaat qilinsa, kirish o'rniga yangi usul akkauntga bog'lanadi.

## API
| Metod | Yo'l | Body |
|---|---|---|
| POST | `/api/auth/email/request-code/` | `{email}` |
| POST | `/api/auth/email/verify/` | `{email, code}` |
| POST | `/api/auth/google/` | `{id_token}` |
| POST | `/api/auth/telegram/` | Telegram Login Widget maydonlari |
| POST | `/api/auth/refresh/` | `{refresh}` |
| GET | `/api/me/` | — |
| GET | `/api/health/` | — |

Kirish javobi: `{status: "active", access, refresh, user}`, `202 {status: "pending"}` yoki `403 {status: "blocked"}`.

## Zakovat API (`/api/zakovat/...`)
Barcha so'rovlar tokenni talab qiladi. Qoida buzilsa: `400 {"detail": "... [N-x.y]"}`, ruxsat bo'lmasa: `403`.
Mavsum: joriy faol mavsum yoki `?season=<id>`. Mahalliy (DEBUG=1) rejimda admin panelga kirgan holda brauzerda ham ochiladi.

**Ishtirokchi**
| Metod | Yo'l | Izoh |
|---|---|---|
| GET | `me/` | jamoam, takliflar, rollarim |
| GET | `players/?q=&free=1` | xodim qidirish (faqat ism va filial) |
| GET/POST | `teams/` | jamoalar ro'yxati / jamoa ochish `{name}` |
| GET | `teams/{id}/` | jamoa tarkibi |
| POST | `teams/{id}/invite/` | `{user_id}` — sardor |
| POST | `teams/{id}/members/{member_id}/remove/` | |
| POST | `teams/{id}/submit/`, `rename/`, `withdraw/` | `{name}`, `{reason}` |
| POST | `invitations/{id}/respond/` | `{accept}` |
| GET | `games/`, `games/{id}/` | o'yinlar va mening arizam |
| POST | `games/{id}/register/` | sardor |
| GET | `games/{id}/results/` | dastlabki/yakuniy natija, har savol bo'yicha javoblar, R |
| GET | `games/{id}/live/` | katta ekran: joriy savol, jonli reyting |
| GET/POST | `games/{id}/appeals/` | `{number, content, evidence}` — sardor |
| GET | `standings/` | mavsum reytingi |

**Tashkiliy guruh**
| Metod | Yo'l | Izoh |
|---|---|---|
| POST | `games/` | o'yin yaratish |
| PATCH | `games/{id}/` | o'zgartirish; 1 kundan kam qolganda `reason` majburiy |
| POST | `games/generate-schedule/` | `{start_time, venue, months}` — 3-shanbalar |
| POST | `teams/{id}/approve/` | |
| GET | `games/{id}/registrations/` | |
| POST | `registrations/{id}/approve/` | stol raqami beriladi |
| POST | `games/{id}/open-registration/`, `start/`, `publish/`, `finalize/` | holatlar |
| POST | `appeals/{id}/decide/` | `{accept, reason}` |
| POST | `games/{id}/tiebreak/`, `season-tiebreak/` | `{team_ids, starts_at, questions}` |
| POST | `games/{id}/reopen/` | `{reason}` — faqat bosh admin |

**Hisob hay'ati**
| Metod | Yo'l | Izoh |
|---|---|---|
| GET | `games/{id}/sheet/` | javoblar jadvali: jamoalar × savollar, tarkib, jonli ball |
| POST | `games/{id}/marks/` | `{marks: [{team_id, number, correct}]}` |
| POST | `games/{id}/current/` | `{number}` — joriy savol |
| POST | `games/{id}/lineup/` | `{team_id, round_no, user_id, from_question?}` |
| POST | `games/{id}/lineup/{entry_id}/remove/`, `lineup/copy/` | |

## Kitobxonlik API (`/api/kitob/...`)
Tur bosqichlari: qoralama → ovoz berish → o'qish (hammaga bir xil muddat, standart 10 kun) → baholash → yakunlangan.
PDF kitoblar va izoh fayllari `backend/private_media/` da saqlanadi va faqat API orqali, kirgan xodimga beriladi.

| Metod | Yo'l | Kim | Izoh |
|---|---|---|---|
| GET | `rounds/`, `rounds/{id}/` | hamma | mening ovozim, muddatim, izohim |
| POST | `rounds/{id}/vote/` | xodim | `{book_id}` — muddat tugaguncha o'zgartirsa bo'ladi |
| GET | `rounds/{id}/book/` (`?download=1`) | xodim | tanlangan kitob PDF |
| GET/POST | `rounds/{id}/my-review/` | xodim | multipart: `text`, `file` |
| GET | `my-card/` | xodim | shaxsiy kartochka: ballar, mezonlar, izohlar |
| GET | `leaderboard/` | sozlamaga qarab | reyting jadvali |
| GET/POST | `books/` | tashkilotchi | multipart: `title, author, pdf, cover?, rights_confirmed` |
| POST | `rounds/` | tashkilotchi | `{title, book_ids, criteria:[{name,max_points}], reading_days, min_review_length, reviewers_per_review}` |
| POST | `rounds/{id}/start-voting/` | tashkilotchi | `{vote_ends}` |
| POST | `rounds/{id}/close-voting/` | tashkilotchi | teng bo'lsa `{book_id}` |
| POST | `rounds/{id}/extensions/` | tashkilotchi | `{user_id, until, reason}` |
| POST | `rounds/{id}/start-grading/`, `approve/` | tashkilotchi | |
| GET | `rounds/{id}/reviews/` | tekshiruvchi | muallifsiz (tashkilotchiga — muallif bilan) |
| POST | `reviews/{id}/grade/` | tekshiruvchi | `{scores:[{criterion_id, points}], comment}` |
| GET | `reviews/{id}/file/` | muallif, tekshiruvchi | izoh fayli |

## Demo ma'lumotlar
`python manage.py seed_demo` — demo mavsum, 18 xodim, 4 jamoa, o'tkazilgan o'yin. Admin paroli `backend/dev_login.txt` da.
Mahalliy server: http://127.0.0.1:8100/admin/

## Serverga chiqarish
Railway uchun qadamma-qadam qo'llanma: [docs/RAILWAY.md](docs/RAILWAY.md).

## Serverga chiqarish uchun eslatma
- `DATABASE_URL=postgres://...` va `pip install "psycopg[binary]"`.
- `DEBUG=0`, kuchli `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, HTTPS.
- Server O'zbekiston hududida bo'lishi kerak (shaxsiy ma'lumotlar).
