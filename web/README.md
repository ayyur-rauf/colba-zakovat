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
| `/zakovat/[id]/sheet` | hisob hay'ati jadvali, tarkib, apellyatsiyalar |
| `/ekran/[id]` | proyektor uchun katta ekran |
| `/kitobxonlik` | turlar: yaratish, ovoz, o'qish, baholash, tasdiqlash |
| `/kitobxonlik/books` | kitoblar va PDF yuklash |
| `/kitobxonlik/grading` | izohlarni baholash |
| `/kitobxonlik/leaderboard` | reyting |
| `/munozara`, `/sport` | rejalashtirilgan bo'limlar |

## Tashqi ko'rinishni o'zgartirish
- **Ranglar, burchaklar, fon:** `src/app/globals.css` — boshidagi o'zgaruvchilar (`--bg`, `--accent`, ...).
- **Modullar, ikonkalar, bo'limlar menyusi:** `src/lib/modules.ts`.
- **Tugma, kartochka, belgi, sarlavha:** `src/components/ui.tsx`.
- Har modul sahifalari: `src/components/zakovat/*`, `src/components/kitob/*`.

## Tekshiruv
```powershell
node node_modules/typescript/bin/tsc --noEmit -p .
node node_modules/eslint/bin/eslint.js src
```
