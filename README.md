# 🛒 Savdo Bot — To'liq Qo'llanma

## Fayl tuzilishi

```
savdo_bot/
├── main.py                  # Botni ishga tushirish
├── config.py                # Sozlamalar
├── requirements.txt         # Kutubxonalar
├── railway.toml             # Railway deploy config
├── .env.example             # Muhit o'zgaruvchilari namunasi
├── database/
│   ├── db.py                # Baza ulanish va jadvallar
│   └── queries.py           # So'rovlar
├── handlers/
│   ├── registration.py      # Ro'yxatdan o'tish
│   ├── order.py             # Buyurtmalar
│   ├── moderator.py         # Moderator panel
│   └── admin.py             # Admin panel
└── keyboards/
    └── keyboards.py         # Barcha tugmalar
```

---

## 1-QADAM: Bot token olish

1. Telegramda **@BotFather** ni oching
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting (masalan: `QishloqSavdoBot`)
4. Username kiriting (masalan: `qishloq_savdo_bot`)
5. Token oling: `7123456789:AAH...` ko'rinishida

---

## 2-QADAM: Railway.app sozlash

### 2.1 GitHub repo yarating

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/sizning-username/savdo-bot.git
git push -u origin main
```

### 2.2 Railway ga kirish

1. [railway.app](https://railway.app) ga kiring
2. **GitHub** bilan ro'yxatdan o'ting
3. **New Project** → **Deploy from GitHub repo** bosing
4. Repozitoriyangizni tanlang

### 2.3 PostgreSQL qo'shish

1. Proyektingizda **+ New** → **Database** → **PostgreSQL**
2. PostgreSQL qo'shilganidan so'ng `DATABASE_URL` avtomatik paydo bo'ladi

### 2.4 Muhit o'zgaruvchilarini kiriting

Railway proyektingizda **Variables** bo'limiga kiring:

```
BOT_TOKEN        = 7123456789:AAH...sizning_tokeningiz
DATABASE_URL     = (Railway avtomatik to'ldiradi)
ADMIN_IDS        = sizning_telegram_id_ingiz
```

> 💡 **Telegram ID ni qanday bilish?** @userinfobot ga /start yuboring

### 2.5 Deploy qilish

Variables saqlangandan so'ng Railway avtomatik deploy qiladi.

---

## 3-QADAM: Birinchi ishga tushirgandan keyin

### Bosh admin tayinlash (MUHIM!)

Botga `/start` yuboring → ro'yxatdan o'ting

Keyin Railway **PostgreSQL** ga ulanib:

```sql
UPDATE users SET role='superadmin' WHERE telegram_id=SIZNING_ID_INGIZ;
```

Yoki botda `/setmod` buyrug'ini ishlatish uchun avval o'zingizni superadmin qiling.

### Filiallar qo'shish

Admin panelda: **📊 Admin panel → ➕ Yangi filial qo'shish**

### Moderator tayinlash

```
/setmod [branch_id] [moderator_telegram_id]
```

---

## Rollar tizimi

| Rol | Imkoniyatlar |
|-----|--------------|
| `customer` | Buyurtma berish, profil ko'rish |
| `moderator` | Zaxira, mahsulot, transfer, statistika |
| `admin` | Moderator + filiallar boshqaruvi, global stats |
| `superadmin` | Hammasi |

---

## Mahsulotlar va narxlarni yangilash

Moderator paneli → **✏️ Mahsulot tahrirlash** → kerakli mahsulotni tanlang

---

## Transfer tizimi qanday ishlaydi?

1. Filial 1 da kartoshka tugaydi (`min_quantity` dan kam)
2. Bot avtomatik **eng yaqin** filiallarni qidiradi
3. Filial 1 moderatoriga: "Quyidagi filiallardan so'rashingiz mumkin" deb xabar keladi
4. Moderator tasdiqlasa → Filial 2 moderatoriga so'rov ketadi
5. Filial 2 moderatori tasdiqlasa → Zaxira yangilanadi

---

## Muammolar

**Bot javob bermaydi?**
- Railway loglarini tekshiring: `Deployments → View Logs`
- BOT_TOKEN to'g'ri ekanligini tekshiring

**Database xatosi?**
- DATABASE_URL to'g'ri ulanganligini tekshiring
- Railway PostgreSQL servisi ishlayotganini ko'ring

---

## Kelajakda qo'shish mumkin

- [ ] To'lov tizimi (Payme, Click)
- [ ] Yetkazib berish kuzatuvi (GPS)
- [ ] SMS bildirishnomalar
- [ ] Web admin panel (Django/FastAPI)
- [ ] Mijozlar reytingi tizimi
