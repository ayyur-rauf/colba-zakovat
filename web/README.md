# Colba platformasi — sayt (Next.js)

Next.js 16 (App Router, TypeScript, Tailwind). Backend (Django) bilan `/api/...` orqali ishlaydi:
Next so'rovni `BACKEND_URL` ga (standart `http://127.0.0.1:8100`) uzatadi — `next.config.ts`.

## Ishga tushirish
```powershell
cd web
npm.cmd install
npm.cmd run dev -- -p 3100 -H 127.0.0.1
```
Backend 8100-portda ishlab turishi kerak. Sayt: http://localhost:3100

**Tez rejim (production):** ishlab chiqish rejimida har sahifa birinchi ochilganda kompilyatsiya qilinadi va sekinroq.
Haqiqiy tezlikni ko'rish uchun:
```powershell
node node_modules/next/dist/bin/next build
node node_modules/next/dist/bin/next start -p 3101 -H 127.0.0.1
```

## Sahifalar
| Yo'l | Nima |
|---|---|
| `/login` | email kod bilan kirish (mahalliy rejimda kod avtomatik ko'rinadi) |
| `/` | modullar markazi |
| `/zakovat` | umumiy: keyingi o'yin, statistika, qisqa reyting |
| `/zakovat/games` | o'yinlar, arizalar, yangi o'yin, mavsum jadvali |
| `/zakovat/teams` | jamoalar, tarkib, tasdiqlash |
| `/zakovat/standings` | mavsum reytingi |
| `/zakovat/questions` | savollar banki (faqat Tashkiliy guruh) |
| `/zakovat/[id]/questions` | o'yinga savollarni biriktirish, avtomatik to'ldirish |
| `/zakovat/[id]/host` | boshlovchi pulti: savol, javob, taymer (← → Probel R) |
| `/zakovat/[id]/sheet` | hisob hay'ati jadvali (klaviatura: strelkalar, 1/Enter, 0), tarkib, apellyatsiyalar |
| `/chop/[id]` | qog'oz blankalar — chop etish yoki PDF |
| `/ekran/[id]` | proyektor uchun katta ekran |
| `/kitobxonlik` | turlar: yaratish, ovoz, o'qish, baholash, tasdiqlash |
| `/kitobxonlik/books` | kitoblar va PDF yuklash |
| `/kitobxonlik/grading` | izohlarni baholash |
| `/kitobxonlik/leaderboard` | reyting |
| `/munozara`, `/sport` | rejalashtirilgan bo'limlar |
| `/boshqaruv` | (bosh admin) xodimlar va Excel yuklash |
| `/boshqaruv/accounts` | tasdiq kutayotgan akkauntlar, bloklash |
| `/boshqaruv/roles` | rollarni berish va olish |
| `/boshqaruv/seasons` | mavsumlar, joriy mavsum |
| `/boshqaruv/announcements` | e'lonlar (bosh sahifa va modullarda ko'rinadi) |
| `/boshqaruv/points` | ball reestri, qo'lda tuzatish (sabab bilan) |
| `/boshqaruv/summary` | Yil sarhisobi: g'oliblar, filiallar kesimi, Excel |
| `/boshqaruv/audit` | harakatlar jurnali |

## Tashqi ko'rinishni o'zgartirish
- **Ranglar, burchaklar, fon:** `src/app/globals.css` — kunduzgi (`:root`) va tungi (`[data-theme="dark"]`) o'zgaruvchilar (`--bg`, `--accent`, ...).
- **Kunduzgi/tungi ko'rinish:** sarlavhadagi ☾/☀ tugmasi; tanlov brauzerda saqlanadi, birinchi marta tizim sozlamasiga qaraladi (`src/lib/theme.ts`).
- **Modullar, ikonkalar, bo'limlar menyusi:** `src/lib/modules.ts`.
- **Tugma, kartochka, belgi, sarlavha:** `src/components/ui.tsx`.
- Har modul sahifalari: `src/components/zakovat/*`, `src/components/kitob/*`.

## Tekshiruv
```powershell
node node_modules/typescript/bin/tsc --noEmit -p .
node node_modules/eslint/bin/eslint.js src
```
