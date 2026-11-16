# Colba platformasi — Texnik topshiriq (TZ), 1-versiya

**Holati:** qoralama, 2026-11-16
**Qamrovi:** Yadro + Zakovat ("Colba ligasi") + Kitobxonlik (MVP). Munozara va Sport — keyingi versiyada.
**Asos hujjat:** "Colba ligasi" Nizomi (`Colba_ligasi_Nizom.pdf`). Matnda `[N-x.y]` — Nizomning tegishli bandi.

---

## 1. Umumiy tavsif

### 1.1. Maqsad
"Colba maktabi" filiallari xodimlari o'rtasidagi intellektual tadbirlarni (Zakovat, Kitobxonlik, keyinroq Munozara va Sport) bitta platformada tashkil etish: e'lon, ro'yxatdan o'tish, jamoa tuzish, natijalarni hisoblash, reyting va yillik mukofot uchun ballarni yig'ish.

### 1.2. Foydalanuvchilar soni
- Boshida 300–400, keyinroq 500–600 xodim.
- Bir vaqtda faol: ko'pi bilan ~400 (masalan, natija e'lon qilingan payt).

### 1.3. Platformalar
| Platforma | Asosiy foydalanuvchi | Asosiy vazifa |
|---|---|---|
| Sayt (web) | Tashkilotchilar, hisob hay'ati | Katta jadvallar, natija kiritish, hisoblash, e'lon qilish, eksport, katta ekran rejimi |
| Mobil ilova (Android, iOS) | Xodimlar | Tadbirlar, ro'yxatdan o'tish, jamoa, kitob o'qish, izoh yuborish, ballar, apellyatsiya, bildirishnomalar |
| Telegram bot | Hamma | Faqat kirish (login) va xabarnomalar |

Xodim saytdan ham to'liq foydalana oladi. Admin ilovadan qisqartirilgan ko'rinishda ishlaydi.

### 1.4. Asosiy tushunchalar
- **Mavsum** = o'quv yili. Boshlanish va tugash sanasini admin belgilaydi (standart: 1-sentyabr — 31-avgust). Barcha ballar mavsum bo'yicha yig'iladi, mavsum yakunida "Yil sarhisobi"da taqdirlanadi [N-10.1].
- **Ball** — yillik reytingga tushadigan rasmiy natija. Zakovatda ball **jamoaga**, Kitobxonlikda **shaxsga** yoziladi.
- **Mashq (training)** — ball bermaydigan o'yinlar (quiz battle, qisqa zakovat).

---

## 2. Rollar va huquqlar

| Rol | Kim | Huquqlari |
|---|---|---|
| Bosh admin | Platforma egasi | Hamma narsa: foydalanuvchilar, rollar, modullar, mavsumlar, sozlamalar |
| Tashkiliy guruh (TG) a'zosi | Kasaba bo'limi tayinlaydi [N-2.1] | Zakovat: o'yin yaratish, jamoalarni tasdiqlash, natija kiritish, apellyatsiyani ko'rish, natijani tasdiqlash |
| Boshlovchi | TG belgilaydi [N-5.1] | O'yin ekranini boshqarish (savol raqami, raund) |
| Sekundant | TG belgilaydi | O'yin vaqtini boshqarish |
| Hisob hay'ati | TG belgilaydi | Javoblar jadvaliga "to'g'ri/noto'g'ri" kiritish |
| Kitobxonlik tashkilotchisi | Admin tayinlaydi | Kitob qo'shish, ovoz berish va turni boshqarish |
| Tekshiruvchi | Admin tayinlaydi | Izohlarni baholash |
| Jamoa sardori | Jamoani ochgan xodim | Jamoa tarkibi, ro'yxatdan o'tkazish, apellyatsiya berish |
| Xodim (ishtirokchi) | Har bir xodim | Profil, jamoaga qo'shilish, ovoz berish, o'qish, izoh yuborish, natijalarni ko'rish |

Bitta odamda bir nechta rol bo'lishi mumkin. Rollar modul va mavsum doirasida beriladi.
Cheklov: o'yin hisob hay'atidagi odam shu o'yinda o'yinchi bo'la olmaydi. Tekshiruvchi o'z izohini baholay olmaydi.

---

## 3. Yadro (umumiy qism)

### 3.1. Xodimlar ro'yxati va kirish
1. Admin xodimlar ro'yxatini Excel'dan yuklaydi: F.I.Sh., filial, lavozim, telefon, email (ixtiyoriy).
2. Faqat ro'yxatdagi xodim akkaunt ocha oladi. Ro'yxatda yo'q odam kirsa — "admin tasdig'ini kutmoqda" holati bo'ladi.
3. Kirish usullari: **Telegram** (Telegram Login), **Google**, **email** (parol yoki bir martalik kod).
4. Bitta akkauntga bir nechta kirish usulini bog'lash mumkin (profil sozlamalarida).
5. Xodim ishdan ketsa, admin uni "nofaol" qiladi. Akkaunt o'chirilmaydi, ballari tarixda qoladi.

### 3.2. Profil
- Rasm, F.I.Sh., filial, lavozim (ro'yxatdan keladi, xodim o'zgartira olmaydi).
- Zakovat jamoasi, kitobxonlik natijalari, joriy mavsum ballari, o'tgan mavsumlar arxivi.
- Telefon va email boshqa xodimlarga ko'rinmaydi.

### 3.3. Tadbirlar kalendari
- Barcha modullarning tadbirlari bitta kalendarda ko'rinadi.
- Har bir tadbirda: sana, vaqt, joy, holat, ro'yxatdan o'tish tugmasi.

### 3.4. Bildirishnomalar
- Kanallar: ilova ichida, push (mobil), Telegram bot, email. Xodim qaysilarini olishni o'zi tanlaydi.
- Turlari: yangi tadbir, eslatma, o'zgarish, natija e'lon qilindi, jamoaga taklif, izoh baholandi, muddat tugayapti.

### 3.5. Muloqot (kichik, shaxsiy emas)
- Tashkilotchilardan e'lonlar (modul bo'yicha).
- Tadbir ostida izoh va savollar.
- Jamoa ichki chati (2-versiyada).
- Shaxsiy yozishmalar **yo'q**. Admin istalgan izohni yashira oladi.

### 3.6. Ball reestri
Barcha ballar bitta jadvalda saqlanadi. Har bir yozuvda quyidagilar bo'ladi:
`mavsum | modul | kimga (jamoa yoki xodim) | ball | sabab (tadbir/izoh) | kim kiritdi | qachon | izoh`

Qoidalar:
- Ball hech qachon o'chirilmaydi. Tuzatish uchun yangi tuzatuvchi yozuv qo'shiladi, sababini yozish majburiy.
- Har bir xodim va jamoa o'z ballari tarixini ko'ra oladi.
- Mavsum reytingi shu reestr asosida hisoblanadi.

### 3.7. Harakatlar jurnali
Muhim amallar (natija kiritish va o'zgartirish, tasdiqlash, ball tuzatish, rol berish) jurnalga yoziladi: kim, qachon, nima edi, nima bo'ldi.

---

## 4. Zakovat moduli ("Colba ligasi")

### 4.1. Mavsum va o'yinlar jadvali
- Mavsum yaratilganda o'yinlar **har oyning 3-shanbasiga** avtomatik rejalashtiriladi [N-1.2]. Admin keraksiz sanalarni o'chirishi yoki qo'shishi mumkin.
- O'yin maydonlari: sana, vaqt, joy, maksimal jamoalar soni (joy sig'imi bo'yicha) [N-4.1], ro'yxatdan o'tish muddati.
- **O'zgartirish qoidasi** [N-1.4]: sana, vaqt yoki joy o'zgarsa, ro'yxatdagi hamma jamoaga darhol xabar ketadi. O'yinga 24 soatdan kam qolganda o'zgartirishga urinilsa, tizim ogohlantiradi va sababni so'raydi.
- Eslatmalar: 3 kun oldin, 1 kun oldin, o'yin kuni ertalab.

### 4.2. Jamoalar
**Tuzish:** xodim jamoa ochadi va sardor bo'ladi. U boshqa xodimlarni taklif qiladi, ular taklifni qabul qiladi. Jamoasiz xodim "jamoa qidiryapman" belgisini qo'yishi mumkin. Sardorlar shu ro'yxatni ko'radi.

**Tizim tekshiradigan qoidalar:**
| Qoida | Nizom |
|---|---|
| Jamoada 4 dan 8 tagacha o'yinchi | [N-3.2] |
| Bir o'yinchi mavsumda faqat bitta jamoada | [N-3.2] |
| Jamoa nomi takrorlanmaydi (katta-kichik harf va bo'sh joylar farqlanmaydi) | [N-3.3] |
| Nom faqat mavsumlar orasida o'zgaradi | [N-3.4] |
| Boshqa jamoaga o'tish faqat mavsum boshlanishidan oldin; mavsum davomida tarkib qulflanadi (TG ruxsati bilan istisno) | [N-3.5] |
| Jamoa tarkibini TG tasdiqlaydi; tasdiqlanmagan jamoa o'yinga yozila olmaydi | [N-3.1] |

**Jamoa holatlari:** `qoralama → tasdiq kutilmoqda → faol → chiqib ketgan / chetlatilgan`
- Sardor "ishtirokni to'xtatish" tugmasini bosadi, TG xabardor bo'ladi [N-3.7].
- Jamoa chiqib ketsa yoki chetlatilsa [N-3.8], **uning mavsumdagi barcha ballari nolga tushadi**. Boshqa jamoalarning ballari qayta hisoblanmaydi [N-3.9]. Ball reestriga tuzatuvchi yozuv qo'shiladi.
- Mavsum o'rtasida qo'shilgan jamoa 0 balldan boshlaydi [N-4.2].

### 4.3. O'yinga ro'yxatdan o'tish
- Sardor o'yinga ariza beradi va ishtirok etadigan o'yinchilarni belgilaydi.
- Ariza **o'yindan 1 kun oldin** yopiladi [N-3.2].
- Joy to'lsa, keyingi arizalar "navbat"ga tushadi. TG ularni qo'lda o'tkazadi.
- TG arizalarni tasdiqlaydi.

### 4.4. Qog'oz blankalar
Javoblar zalda **qog'ozda** yig'iladi. Tizim har o'yin uchun bosib chiqariladigan blankalar yaratadi (PDF): jamoa nomi va raqami, raund, savol raqami va javob uchun joy. Har jamoa uchun 36 ta blanka bo'ladi.

### 4.5. O'yin kuni — saytdagi ekranlar

**a) Tarkib ekrani (har raund oldidan)**
- Har jamoa uchun shu raundda o'ynayotgan o'yinchilar belgilanadi: ko'pi bilan 6 kishi [N-5.2].
- Almashtirish faqat raundlar orasida mumkin [N-5.2].
- O'yinchi raund o'rtasida kelsa, "qaysi savoldan qo'shildi" maydoni to'ldiriladi [N-4.3].

**b) Javoblar jadvali (hisob hay'ati)**
- Qatorlarda jamoalar, ustunlarda 36 savol (3 raund × 12) [N-5.3].
- Katakni bir bosish "to'g'ri" (1), ikki bosish "noto'g'ri" (0) qiladi. Klaviatura bilan tez kiritish ham mumkin.
- Bir nechta hisob hay'ati a'zosi bir vaqtda kiritishi mumkin (masalan, raundlar yoki jamoalar bo'yicha bo'lib).
- Hisobga olinmaydigan kataklar kulrang ko'rinadi. Bu jamoada 3 nafardan kam o'yinchi bo'lgan savollar [N-3.6, N-4.3].
- O'ng tomonda har jamoaning jami bali va o'rni jonli hisoblanib turadi.
- Har bir o'zgarish jurnalga yoziladi.

**c) Katta ekran (proyektor)**
- Joriy raund va savol raqami, taymer (sekundant boshqaradi).
- Raund oxirida reyting jadvali. TG uni yashirishi yoki ko'rsatishi mumkin (shiddatni saqlash uchun, masalan oxirgi raundda yashirib, oxirida ochish).

### 4.6. Natijalar holati va apellyatsiya
Natija quyidagi holatlardan o'tadi:
1. **Kiritilmoqda** — hisob hay'ati ishlayapti.
2. **Dastlabki natija** — TG e'lon qiladi. Ilovada natija va har bir savol bo'yicha jamoaning javoblari ko'rinadi.
3. **Apellyatsiya oynasi** — faqat **sardor** ilovadan apellyatsiya beradi [N-7.4]. Majburiy maydonlar: jamoa (avtomatik), savol raqami, e'tiroz mazmuni, dalillar (matn, rasm yoki havola). Maydonlardan biri bo'sh bo'lsa, ariza yuborilmaydi.
4. **Ko'rib chiqish** — TG har apellyatsiya bo'yicha "qabul qilindi" yoki "rad etildi" qarorini sababi bilan qo'yadi. Qabul qilinsa, jadvaldagi katak o'zgaradi va ballar avtomatik qayta hisoblanadi [N-6.4].
5. **Yakuniy natija** — TG tasdiqlaydi. Natija qulflanadi, ballar reestrga yoziladi, yangi apellyatsiya qabul qilinmaydi [N-7.3].

Yakuniy natijani faqat bosh admin qayta ocha oladi, sababini yozib. Bu jurnalga tushadi.

### 4.7. Hisoblash algoritmi

**Tur bali:** jamoa to'g'ri javob bergan va hisobga olinadigan savollar soni (har biri 1 ball) [N-6.1].
Agar jamoada butun tur davomida 3 nafardan kam o'yinchi bo'lsa, tur natijasi 0 bo'ladi va reyting uchun hisobga olinmaydi [N-4.3].

**Teng ballarni ajratish** [N-8.1–8.3]:
1. Har savol uchun reyting: `R = N + 1`, bunda N — shu savolga to'g'ri javob bera olmagan jamoalar soni.
2. Jamoa reytingi: `J = Σ R`, faqat jamoa to'g'ri javob bergan savollar bo'yicha.
3. Ball teng bo'lsa, J kattasi yuqori turadi.
4. Ball ham, J ham teng bo'lsa, teng jamoalar o'rtasida **qo'shimcha o'yin** o'tkaziladi (4.8-bo'lim).

Ochiq masala: N hisoblanayotganda shu turi hisobga olinmagan jamoalar (3 nafardan kam o'yinchi) ham sanaladimi? Hozircha **sanalmaydi** deb qabul qilindi, TG tasdiqlashi kerak.

**Misol:** 10 jamoa. 5-savolga 2 jamoa to'g'ri javob berdi, demak N = 8, R = 9. A va B jamoalarida 20 balldan. A javob bergan savollar reytinglari yig'indisi 140, B niki 132 → A yuqorida.

**Mavsum reytingi:** jamoaning yakuniy tasdiqlangan tur ballari yig'indisi. Mavsum oxirida ballar teng bo'lsa, qo'shimcha o'yin o'tkaziladi.

### 4.8. Qo'shimcha o'yin
- TG teng jamoalarni tanlaydi (tizim ularni avtomatik taklif qiladi) va qo'shimcha o'yin yaratadi: sana, savollar soni.
- Natija xuddi shu javoblar jadvalida kiritiladi.
- Qo'shimcha o'yin **faqat o'rinni** belgilaydi, mavsum ballariga qo'shilmaydi.

### 4.9. Savollar banki
- Savol maydonlari: matn, rasm yoki audio (ixtiyoriy), javob, qabul qilinadigan javoblar, izoh, manba, muallif, mavzu, qiyinlik, holat (`qoralama / tahrirda / tasdiqlangan / ishlatilgan`).
- Liga o'yinigacha savollar faqat TG'ga ko'rinadi.
- O'yindan keyin savollar "ishlatilgan" holatiga o'tadi va mashq bo'limiga ochiladi.

### 4.10. Mashq bo'limi (ball bermaydi)
- **Quiz battle (onlayn):** individual yoki jamoaviy; telefondan javob, taymer; natija faqat shu o'yin ichida ko'rinadi.
- **Qisqa zakovat:** masalan 12 savol; zalda (oflayn, javoblar jadvali bilan) yoki onlayn.
- Savollar ishlatilgan savollar bankidan yoki tashkilotchi alohida qo'shgan savollardan olinadi.
- Ball reestriga **hech narsa yozilmaydi**.

---

## 5. Kitobxonlik moduli

### 5.1. Tur holatlari
`qoralama → ovoz berish → o'qish (10 kun) → izohlar yopildi → baholash → yakunlangan`

### 5.2. Bosqichlar
**1. Tur yaratish (tashkilotchi)**
- Bir nechta nomzod kitob qo'shiladi: nom, muallif, muqova, qisqa tavsif, PDF fayl.
- Ovoz berish muddati, o'qish muddati (standart 10 kun), baholash mezonlari belgilanadi.

**2. Ovoz berish**
- Har xodim bitta kitobga ovoz beradi. Muddat tugaguncha ovozini o'zgartira oladi.
- Ovoz berish davomida natijalar yashirin bo'ladi (sozlama).
- **Eng ko'p ovoz olgan kitob tanlanadi.** Ovozlar teng bo'lsa, tashkilotchi tanlaydi.

**3. O'qish (10 kun)**
- Tanlangan kitob ilova va sayt ichidagi PDF o'qigichda ochiladi yoki yuklab olinadi.
- PDF faqat tizimga kirgan xodimlarga beriladi (vaqtinchalik havola orqali).
- Ekranda qolgan kunlar ko'rinadi. Eslatmalar muddat tugashiga 3 kun va 1 kun qolganda ketadi.
- Ochiq masala: 10 kun tur boshlanganidan hisoblanadimi (hammaga bir xil muddat) yoki xodim "o'qishni boshladim" deganidan? Hozircha **hammaga bir xil** deb qabul qilindi.

**4. Izoh yuborish**
- Matn (minimal uzunlik sozlanadi) va/yoki fayl (PDF, DOCX, rasm).
- Muddat tugaguncha xodim izohini tahrirlay oladi. Muddatdan keyin yuborish yopiladi. Tashkilotchi alohida xodimga muddatni uzaytirishi mumkin.

**5. Baholash**
- Tekshiruvchi mezonlar bo'yicha ball qo'yadi. Mezonlar har tur uchun sozlanadi, masalan: mazmunni tushunish 0–10, shaxsiy fikr va tahlil 0–10, savodxonlik va uslub 0–5.
- Tekshiruvchi xodimga qisqa izoh yozadi.
- Bir izohni bir nechta tekshiruvchi baholashi mumkin. Unda o'rtacha ball olinadi (sozlama).
- Tashkilotchi barcha baholarni tasdiqlaydi, keyin ballar reestrga yoziladi va xodimga xabar ketadi.

### 5.3. Shaxsiy kartochka
- O'qilgan kitoblar, har biri bo'yicha ball, mezonlar kesimida baho va tekshiruvchi izohi.
- Joriy mavsumdagi jami kitobxonlik bali.

### 5.4. Reyting jadvali
- Admin sozlamasi bilan yoqiladi yoki o'chiriladi (hozircha aniq emas).
- Yoqilsa: mavsum bo'yicha xodimlar reytingi, filial bo'yicha filtr bilan.

### 5.5. Huquqiy eslatma
PDF kitoblarni tarqatishda mualliflik huquqiga e'tibor berish kerak. Mualliflik muddati o'tgan kitoblar, ruxsat olingan nashrlar yoki sotib olingan nusxalardan foydalanish tavsiya etiladi. Kitob qo'shishda tashkilotchi "tarqatish huquqi bor" belgisini qo'yadi.

---

## 6. Ma'lumotlar tuzilmasi (asosiy jadvallar)

**Yadro**
- `branch` — filial: id, nom.
- `employee` — xodim: id, fish, filial, lavozim, telefon, email, faol.
- `user` — akkaunt: id, employee_id, rasm, holat.
- `auth_identity` — kirish usuli: user_id, turi (telegram / google / email), tashqi_id.
- `role_assignment` — rol: user_id, rol, modul, mavsum.
- `season` — mavsum: id, nom (masalan "2026–2027"), boshlanish, tugash, faol.
- `points_ledger` — ball reestri: mavsum, modul, subyekt_turi (team / user), subyekt_id, ball, sabab_turi, sabab_id, kiritdi, vaqt, izoh.
- `notification`, `announcement`, `comment`.
- `audit_log` — jurnal: user, amal, obyekt, eski, yangi, vaqt.

**Zakovat**
- `team` — jamoa: id, mavsum, nom, sardor, holat.
- `team_member` — a'zo: team_id, user_id, qo'shildi, chiqdi.
- `game` — o'yin: id, mavsum, turi (liga / qo'shimcha / mashq), sana, joy, maks_jamoa, ariza_muddati, savollar_soni, raundlar_soni, holat.
- `game_registration` — ariza: game_id, team_id, holat.
- `game_lineup` — tarkib: game_id, team_id, raund, user_id, qaysi_savoldan.
- `question` — savol: matn, javob, mavzu, qiyinlik, muallif, holat.
- `game_question` — o'yindagi savol: game_id, tartib_raqami, question_id.
- `answer_mark` — javob belgisi: game_id, team_id, savol_raqami, to'g'ri (1 / 0), hisobga_olinadi, kiritdi, vaqt.
- `appeal` — apellyatsiya: game_id, team_id, savol_raqami, mazmun, dalil, holat, qaror, qaror_sababi.
- `game_result` — natija: game_id, team_id, ball, J, o'rin, holat.

**Kitobxonlik**
- `book` — kitob: nom, muallif, muqova, pdf, tavsif, huquq_belgisi.
- `reading_round` — tur: mavsum, holat, ovoz_muddati, o'qish_boshlanishi, o'qish_tugashi, tanlangan_kitob.
- `round_candidate` — nomzod kitob: round_id, book_id.
- `book_vote` — ovoz: round_id, user_id, book_id.
- `review` — izoh: round_id, user_id, matn, fayl, yuborilgan, holat.
- `rubric_criterion` — mezon: round_id, nom, maks_ball.
- `review_score` — baho: review_id, tekshiruvchi, criterion_id, ball, izoh.

---

## 7. Texnologiyalar

| Qism | Tanlov | Sabab |
|---|---|---|
| Backend | Python, Django + Django REST Framework | Tayyor admin panel, autentifikatsiya, tez ishlab chiqish |
| Kirish | django-allauth (Google, email) + Telegram Login | Tayyor yechimlar |
| Ma'lumotlar bazasi | PostgreSQL | Ishonchli, hisoblash so'rovlari uchun qulay |
| Fon vazifalari | Celery + Redis | Eslatmalar, bildirishnomalar, PDF blankalar |
| Sayt | Next.js (React, TypeScript) | Katta jadvallar va katta ekran rejimi uchun |
| Ilova | React Native (Expo) | Bitta kod Android va iOS uchun; sayt bilan bir API |
| Jonli yangilanish | Boshida har 3–5 soniyada so'rov (polling); quiz battle uchun WebSocket (Django Channels) | 400 foydalanuvchi uchun yetarli |
| Fayllar | S3'ga mos saqlash yoki server diski | PDF va rasmlar |
| Server | O'zbekiston hududidagi VPS: 4 vCPU, 8 GB RAM, 100 GB+ disk | Shaxsiy ma'lumotlar qonunchilikka ko'ra O'zbekistonda saqlanishi kerak |

---

## 8. Nofunksional talablar
- **Tezlik:** sahifalar 2 soniyadan tez ochiladi, javoblar jadvalidagi kiritish 0,5 soniyadan tez saqlanadi.
- **Xavfsizlik:** HTTPS; huquqlar har bir API so'rovida tekshiriladi; telefon va email boshqa xodimlarga ko'rinmaydi.
- **Zaxira nusxa:** baza har kuni avtomatik nusxalanadi, 30 kun saqlanadi. Fayllar haftada bir marta nusxalanadi.
- **Ishonchlilik:** o'yin kuni internet uzilsa, javoblar jadvali brauzerda vaqtincha saqlanadi va internet qaytganda serverga yuboriladi.
- **Til:** o'zbek tili (lotin). Keyinchalik boshqa tillarni qo'shish uchun matnlar alohida faylda saqlanadi.
- **Eksport:** barcha jadvallar Excel'ga eksport qilinadi.

---

## 9. Ishlab chiqish rejasi

| Sprint (2 hafta) | Natija |
|---|---|
| 1 | Loyiha asosi, baza, xodimlar ro'yxatini yuklash, kirish (Google, email, Telegram), rollar |
| 2 | Profil, mavsum, ball reestri, kalendar, bildirishnomalar (Telegram, email) |
| 3 | Zakovat: jamoalar, qoidalar, o'yin jadvali, ro'yxatdan o'tish |
| 4 | Zakovat: tarkib, javoblar jadvali, hisoblash (J), katta ekran, PDF blankalar |
| 5 | Zakovat: apellyatsiya, natija holatlari, mavsum reytingi, qo'shimcha o'yin |
| 6 | Kitobxonlik: turlar, ovoz berish, PDF o'qish, izoh yuborish |
| 7 | Kitobxonlik: baholash, shaxsiy kartochka; sayt bo'yicha umumiy sinov |
| 8–9 | Mobil ilova (asosiy ekranlar), push bildirishnomalar |
| 10 | Haqiqiy o'yinda sinov (pilot), tuzatishlar, ishga tushirish |
| Keyin | Mashq bo'limi (quiz battle), jamoa chati, Munozara, Sport |

Tavsiya: sinov uchun 4-sprintdan keyin bitta liga o'yinini qog'oz bilan parallel ravishda tizimda ham hisoblab ko'rish kerak. Natijalar mos kelsa, tizimga ishonsa bo'ladi.

---

## 10. Ochiq savollar
1. O'quv yili mavsumi aniq qaysi sanalarda boshlanib tugaydi? Liga o'yinlari qaysi oylarda bo'ladi (masalan, sentyabr–may)?
2. Savol reytingidagi N hisoblanganda turi hisobga olinmagan jamoalar sanaladimi?
3. Kitobxonlikda 10 kun hammaga bir xil sanadan boshlanadimi?
4. Kitobxonlik ovozlari teng bo'lsa kim hal qiladi? (Hozircha tashkilotchi.)
5. Bir izohni nechta tekshiruvchi baholaydi? Ballar o'rtachami?
6. Kitobxonlik reyting jadvali ochiq bo'ladimi?
7. Yillik mukofot qanday taqsimlanadi (masalan, top-3 jamoa, top-10 kitobxon)? Bu reyting sahifasining ko'rinishiga ta'sir qiladi.
