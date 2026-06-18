# 🎓 BilimAI

**BilimAI** — sun'iy intellektga asoslangan professional o'quv yordamchisi.
Matematika, fizika, kimyo, biologiya, tarix, geografiya, ingliz tili va dasturlash
bo'yicha savollarga bosqichma-bosqich, o'rgatuvchi javoblar beradi. Rasmdagi
masalalarni ham yechib beradi.

## ✨ Imkoniyatlar

| Funksiya | Buyruq | Holat |
|----------|--------|-------|
| 💬 Savol-javob (8+ fan) | matn yozish | 🆓 Bepul |
| 📷 Rasmdagi masalani yechish | rasm yuborish | 🆓 Bepul |
| 🎨 Rasm yaratish (AI rasm chizadi) | `/rasm tavsif` | 💎 Pullik obuna |
| 📊 Prezentatsiya (.pptx) tayyorlash | `/prezentatsiya mavzu` | 💎 Pullik obuna |

> 💎 **Pullik obuna** uchun admin bilan bog'laning: **[@ravshanovichch](https://t.me/ravshanovichch)**
> Rasm yaratish butunlay **bepul** API (Pollinations.ai) orqali ishlaydi — qo'shimcha kalit shart emas.

### 🤖 Bot buyruqlari

- `/start` — boshlash
- `/help` — yordam va buyruqlar ro'yxati
- `/id` — Telegram ID raqamingiz (obuna uchun kerak)
- `/obuna` — pullik obuna haqida ma'lumot
- `/rasm <tavsif>` — rasm yaratish *(premium)*
- `/prezentatsiya <mavzu>` — taqdimot tayyorlash *(premium)*

### 👑 Admin buyruqlari (faqat egasi uchun)

- `/addpremium <user_id> [kun] [username]` — foydalanuvchiga premium berish (kun=0 → muddatsiz)
- `/delpremium <user_id>` — premiumdan o'chirish
- `/users` — barcha premium foydalanuvchilar ro'yxati

> Admin `.env` dagi `ADMIN_USERNAME` (sukut bo'yicha `ravshanovichch`) yoki
> `ADMIN_ID` orqali aniqlanadi va barcha funksiyalardan **bepul** foydalanadi.


Loyiha **ikki ko'rinishda** ishlaydi:
- 🤖 **Telegram bot** (`bot.py`)
- 🌐 **Web ilova** (`web.py`) — brauzerda sinab ko'rish uchun

---

## 📁 Loyiha tuzilishi

```
BilimAI/
├── bilim_ai/            # Asosiy "miya"
│   ├── prompt.py        # BilimAI system prompt + prezentatsiya prompti
│   ├── config.py        # Muhit o'zgaruvchilarini o'qiydi (admin sozlamalari ham)
│   ├── ai.py            # AI provayder (Gemini / Groq)
│   ├── subscription.py  # Pullik obuna (premium) tizimi
│   ├── image_gen.py     # 🎨 Rasm yaratish (Pollinations.ai - bepul)
│   └── presentation.py  # 📊 Prezentatsiya (.pptx) yaratish
├── static/              # Web interfeys (HTML + CSS + JS)
│   ├── index.html
│   ├── style.css
│   └── script.js
├── bot.py               # Telegram bot
├── web.py               # FastAPI web server
├── requirements.txt     # Python kutubxonalar
├── .env.example         # Kalitlar namunasi
├── Procfile             # Railway / Heroku uchun
└── railway.json         # Railway sozlamasi
```

---

## 🔑 1-qadam: Bepul AI API kaliti olish

BilimAI ikkita **bepul** provayderni qo'llab-quvvatlaydi:

### 🟢 Google Gemini (TAVSIYA — rasm bilan ham ishlaydi)
1. <https://aistudio.google.com/app/apikey> ga kiring (Google akkaunt kerak).
2. **Create API key** tugmasini bosing.
3. Kalitdan nusxa oling — bu sizning `GEMINI_API_KEY`ingiz.

### ⚡ Groq (juda tez, lekin faqat matn)
1. <https://console.groq.com/keys> ga kiring.
2. **Create API Key** bosing va nusxa oling — bu `GROQ_API_KEY`.

> 💡 Rasmlardan masala yechish uchun **Gemini** kerak. Groq faqat matn uchun.

---

## 🤖 2-qadam: Telegram bot tokeni olish

1. Telegram'da [@BotFather](https://t.me/BotFather) ni oching.
2. `/newbot` deb yozing, bot nomi va username bering.
3. BotFather sizga **token** beradi — bu `TELEGRAM_BOT_TOKEN`.

---

## ⚙️ 3-qadam: Lokal (kompyuterda) ishga tushirish

```bash
# 1) Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 2) Kalitlarni sozlash
cp .env.example .env
#  .env faylni ochib, kalitlaringizni qo'ying

# 3a) Web versiyani ishga tushirish (brauzerda sinash)
python web.py
#  Brauzerda oching: http://localhost:8000

# 3b) Telegram botni ishga tushirish
python bot.py
```

`.env` fayl namunasi:
```env
AI_PROVIDER=gemini
GEMINI_API_KEY=siz_olgan_kalit
TELEGRAM_BOT_TOKEN=botfather_bergan_token
```

---

## 🚀 4-qadam: Railway'ga deploy qilish (web versiya, doimiy ishlashi uchun)

1. Kodingizni GitHub'ga yuklang (pastdagi bo'limga qarang).
2. <https://railway.app> ga kiring → **New Project** → **Deploy from GitHub repo**.
3. `BilimAI` repozitoriyasini tanlang.
4. **Variables** bo'limiga o'ting va kalitlarni qo'shing:
   - `AI_PROVIDER` = `gemini`
   - `GEMINI_API_KEY` = sizning kalitingiz
   - (Telegram bot ham kerak bo'lsa) `TELEGRAM_BOT_TOKEN`
5. Railway avtomatik build qilib, web ilovani ishga tushiradi.
6. **Settings → Networking → Generate Domain** orqali havola oling.

> Telegram botni doimiy ishlatish uchun Railway'da alohida **service** yaratib,
> start buyrug'ini `python bot.py` qilib qo'ying.

---

## 📤 GitHub'ga yuklash

```bash
git init
git add .
git commit -m "BilimAI: dastlabki versiya"
git branch -M main
git remote add origin https://github.com/<username>/BilimAI.git
git push -u origin main
```

> ⚠️ **Muhim:** `.env` fayli `.gitignore`da — kalitlaringiz hech qachon GitHub'ga
> yuklanmaydi. Bu xavfsizlik uchun.

---

## 🛡️ Xavfsizlik

- API kalitlari **hech qachon** kod ichida saqlanmaydi — faqat `.env` yoki Railway Variables.
- `.env` fayli git'ga qo'shilmaydi.
- Tokeningizni hech kimga bermang.

---

## ❓ Tez-tez uchraydigan xatolar

| Xato | Sabab | Yechim |
|------|-------|--------|
| `TELEGRAM_BOT_TOKEN topilmadi` | Token qo'yilmagan | `.env`ga tokenni qo'shing |
| `GEMINI_API_KEY topilmadi` | AI kaliti yo'q | `.env`ga kalitni qo'shing |
| Web sahifada "AI kaliti yo'q" | Kalit sozlanmagan | `.env` yoki Railway Variables tekshiring |
| Rasm ishlamayapti | Groq tanlangan | `AI_PROVIDER=gemini` qiling |

---

Made with 📚 — **BilimAI**
