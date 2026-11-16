# Colba platformasini Railway'ga joylash

Loyiha Railway'da **3 qismdan** iborat bo'ladi:

| Qism | Nima | Papka |
|---|---|---|
| **Postgres** | Ma'lumotlar bazasi | — |
| **backend** | Django API va admin panel | `backend/` |
| **web** | Sayt (Next.js) | `web/` |

Kod tayyor. Quyidagi qadamlarni Railway sahifasida bir marta bajarasiz.
Shundan keyin GitHub'ga har push qilinganda Railway saytni o'zi yangilaydi.

> **Muhim (qonunchilik):** Railway serverlari O'zbekistondan tashqarida joylashgan. O'zbekiston qonunchiligi
> fuqarolarning shaxsiy ma'lumotlarini mamlakat hududidagi serverlarda saqlashni talab qiladi.
> Railway'ni **sinov va namoyish** uchun ishlating. Haqiqiy xodimlar ro'yxati bilan ishga tushirishdan oldin
> yurist bilan maslahatlashing yoki O'zbekistondagi serverga ko'chiring (kod buning uchun ham tayyor).

---

## 0. Kerakli narsalar
1. **Railway akkaunti** — https://railway.com → "Login" → GitHub bilan kiring.
   Doimiy ishlashi uchun **Hobby** tarifi kerak bo'ladi (narxi va shartlarini Railway sahifasida tekshiring).
2. **Brevo akkaunti** (kirish kodlarini email orqali yuborish uchun, bepul) — 5-qadamga qarang.
3. **SECRET_KEY** — o'z kompyuteringizda yarating:
   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```
   Chiqqan uzun qatorni saqlab qo'ying, uni hech kimga ko'rsatmang.

---

## 1. Loyiha yaratish
1. Railway → **New Project** → **Deploy from GitHub repo** → `ayyur-rauf/colba-zakovat` ni tanlang.
   (Birinchi marta Railway'ga GitHub omboringizga ruxsat berishni so'raydi.)
2. Railway bitta xizmat yaratadi. Uni **backend** qilamiz (2-qadam).

## 2. Ma'lumotlar bazasi
1. Loyiha ichida **+ Create** (yoki **New**) → **Database** → **PostgreSQL**.
2. Hech narsa sozlash shart emas.

## 3. Backend xizmati
Yaratilgan xizmatni oching:

**Settings:**
- **Service name:** `backend`
- **Root Directory:** `/backend`
- **Config file path** (agar so'rasa yoki o'zi topmasa): `/backend/railway.json`
- **Networking → Generate Domain** → manzil hosil bo'ladi, masalan `backend-production-xxxx.up.railway.app`.
  Port so'rasa: `8000`.

**Volume** (yuklangan kitoblar va rasmlar o'chib ketmasligi uchun):
- Xizmat ustida o'ng tugma (yoki **+ Create → Volume**) → backend xizmatiga ulang → **Mount path:** `/data`

**Variables** (Raw Editor orqali birdaniga qo'yish mumkin):
```
DEBUG=0
SECRET_KEY=<0-qadamda yaratgan uzun qator>
DATABASE_URL=${{Postgres.DATABASE_URL}}
MEDIA_ROOT=/data/media
PRIVATE_MEDIA_ROOT=/data/private_media
ADMIN_EMAIL=<sizning emailingiz — saytga shu bilan kirasiz>
ADMIN_NAME=<Ism Familiya>
ADMIN_PASSWORD=<Django admin panel uchun kuchli parol (ixtiyoriy)>
BREVO_API_KEY=<5-qadamdan>
DEFAULT_FROM_EMAIL=Colba platformasi <brevoda-tasdiqlangan@email>
```
`${{Postgres.DATABASE_URL}}` — aynan shunday yozing, Railway uni o'zi bazaning manziliga almashtiradi.

Saqlagach Railway deploy qiladi. Har deploy oldidan avtomatik:
- bazaga jadvallar yaratiladi/yangilanadi (`migrate`);
- `ADMIN_EMAIL` bo'yicha bosh admin va joriy o'quv yili mavsumi yaratiladi (bir marta).

Tekshirish: brauzerda `https://<backend-domeni>/api/health/` → `{"status":"ok"}` chiqishi kerak.

## 4. Sayt (web) xizmati
1. Loyiha ichida **+ Create** → **GitHub Repo** → yana o'sha `colba-zakovat` omborini tanlang.
2. **Settings:**
   - **Service name:** `web`
   - **Root Directory:** `/web`
   - **Config file path** (kerak bo'lsa): `/web/railway.json`
   - **Networking → Generate Domain** (port so'rasa: `3000`)
3. **Variables:**
   ```
   BACKEND_URL=https://<backend-domeni>
   ```
   Oxirida `/` qo'ymang. Bu qiymat **build vaqtida** o'qiladi — keyin o'zgartirsangiz, web xizmatini
   **Redeploy** qiling.

## Sinov rejimi (pochtasiz tekshirish)
Pochta hali sozlanmagan bo'lsa, backend Variables'ga qo'shing:
```
TEST_MODE=1
DEMO_DATA=1
```
- `TEST_MODE=1` — kirish kodi xatga yuborilmaydi, kirish sahifasida ko'rinadi.
- `DEMO_DATA=1` — birinchi deploy'da demo ma'lumotlar yuklanadi (bir marta): demo jamoalar, o'yinlar, kitoblar.
  Kirish: `admin@demo.colba.uz` (bosh admin), `tg@demo.colba.uz` (tashkilotchi), `xodim1@demo.colba.uz` (xodim).

> **Diqqat:** sinov rejimida ro'yxatdagi emailni bilgan har kim kira oladi. Haqiqiy xodimlar ro'yxatini
> yuklashdan oldin `TEST_MODE` va `DEMO_DATA` ni o'chiring va pochtani (5-qadam) sozlang.

## 5. Pochta (Brevo) — kirish kodlari uchun
Saytga kirish email kodi orqali. Railway'ning arzon tariflarida oddiy SMTP portlari yopiq bo'lishi mumkin,
shuning uchun xat Brevo'ning HTTP API'si orqali yuboriladi (kod tayyor).

1. https://www.brevo.com → bepul ro'yxatdan o'ting.
2. **Senders, Domains & Dedicated IPs → Senders → Add a sender** → yuboruvchi emailni kiriting
   (masalan Gmail'ingiz) → pochtangizga kelgan xat orqali tasdiqlang.
3. **SMTP & API → API Keys → Generate a new API key** → nusxa oling.
4. Backend xizmatining Variables bo'limiga:
   ```
   BREVO_API_KEY=xkeysib-...
   DEFAULT_FROM_EMAIL=Colba platformasi <2-bandda tasdiqlangan email>
   ```
Bepul tarifda kuniga 300 ta xat — 400–600 xodimga yetadi (kod faqat kirishda yuboriladi).

## 6. Birinchi kirish
1. `https://<web-domeni>` ni oching → `ADMIN_EMAIL` dagi emailni kiriting → pochtaga kelgan kodni yozing.
2. Menyuda **⚙ Boshqaruv** paydo bo'ladi:
   - **Xodimlar → Excel'dan yuklash** — xodimlar ro'yxati (avval "Tekshirish", keyin "Saqlash");
   - **Rollar** — Tashkiliy guruh, hisob hay'ati, tashkilotchi, tekshiruvchilarni tayinlang;
   - **Mavsumlar** — joriy o'quv yili avtomatik yaratilgan, kerak bo'lsa sanalarini tekshiring.
3. Zakovat → O'yinlar → **Mavsum jadvali** — 3-shanbalarga o'yinlar.

Django admin panel (zaxira, texnik): `https://<backend-domeni>/admin/` → login `admin`, parol `ADMIN_PASSWORD`.

## 7. Yangilash
Kompyuterda o'zgarish → `git push` → Railway backend va web'ni o'zi qayta yig'ib, ishga tushiradi.
Bazadagi ma'lumotlar va Volume'dagi fayllar saqlanib qoladi.

## Muammolar bo'lsa
| Belgi | Sabab / yechim |
|---|---|
| Backend deploy "Healthcheck failed" | Variables'ni tekshiring (`SECRET_KEY`, `DATABASE_URL`); **Deployments → View logs** |
| Saytda "Server bilan aloqa yo'q" | web'dagi `BACKEND_URL` noto'g'ri yoki keyin o'zgartirilgan — to'g'rilab **Redeploy** |
| Kod kelmayapti / "pochta xizmati sozlanmagan" | `BREVO_API_KEY`, `DEFAULT_FROM_EMAIL` (Brevo'da tasdiqlangan bo'lishi shart); spam papkasini ham ko'ring |
| Kitob PDF yoki muqovalar deploy'dan keyin yo'qoldi | Volume ulanmagan yoki `MEDIA_ROOT`/`PRIVATE_MEDIA_ROOT` yozilmagan |
| "Faol mavsum yo'q" | Boshqaruv → Mavsumlar → mavsumni "Joriy qilish" |

## Texnik ma'lumot (dasturchi uchun)
- `backend/railway.json` — Railpack, pre-deploy: `migrate` + `bootstrap_admin`; start: `collectstatic` + `gunicorn` (`[::]:$PORT`), healthcheck `/api/health/`.
- `web/railway.json` — `npm run build` / `npm run start` (Next `PORT` ni o'zi o'qiydi), healthcheck `/login`.
- Brauzer faqat web domeniga murojaat qiladi; `/api/*` Next tomonidan `BACKEND_URL` ga uzatiladi (CORS kerak emas).
- `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` ga `RAILWAY_PUBLIC_DOMAIN` va `healthcheck.railway.app` avtomatik qo'shiladi.
- Statik fayllar — WhiteNoise; ochiq media (muqovalar) — Django; PDF va izoh fayllari — faqat API orqali.
