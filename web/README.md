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

## Sahifalar
| Yo'l | Kim uchun | Nima |
|---|---|---|
| `/login` | hamma | email kod bilan kirish (mahalliy rejimda kod avtomatik ko'rinadi) |
| `/` | hamma | o'yinlar ro'yxati |
| `/zakovat/[id]/sheet` | hisob hay'ati, Tashkiliy guruh | javoblar jadvali, tarkib, joriy savol, natija e'loni, apellyatsiyalar |
| `/zakovat/[id]/screen` | proyektor | katta ekran: raund, savol, jonli reyting |

## Tekshiruv
```powershell
node node_modules/typescript/bin/tsc --noEmit -p .
node node_modules/eslint/bin/eslint.js src
```
