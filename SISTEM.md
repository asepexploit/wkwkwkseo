# Rancangan Sistem Bot Telegram SEO Domain Checker

## Arsitektur Sistem

```
User Telegram
     │
     ▼
[Telegram Bot API]
     │
     ▼
[Bot Handler - Python]
     │
     ├──► [Auth & Kredit Manager]
     │           │
     │           ▼
     │       [Database]
     │       - users
     │       - credits
     │       - transactions
     │       - history_cek
     │
     ├──► [Queue System]
     │           │
     │           ▼
     │    [Scraper Worker]
     │    ├── Playwright → dapachecker.net (DA/PA/SS)
     │    ├── Playwright → ahrefs.com free (DR/BC/RD)
     │    └── Whois API (Age)
     │
     └──► [Cache Layer]
              - Simpan hasil per domain
              - Expire: 24 jam
```

---

## Struktur Database

### Tabel: users
```
id          INT (PK)
telegram_id BIGINT (unique)
username    VARCHAR
nama        VARCHAR
kredit      INT default 2
joined_at   DATETIME
is_banned   BOOLEAN default 0
```

### Tabel: transactions
```
id          INT (PK)
user_id     INT (FK → users)
paket       VARCHAR (starter/basic/pro/bulk)
jumlah_kredit INT
harga       INT
status      ENUM(pending, confirmed, rejected)
bukti_url   VARCHAR
created_at  DATETIME
confirmed_at DATETIME
```

### Tabel: history_cek
```
id          INT (PK)
user_id     INT (FK → users)
domain      VARCHAR
da          INT
pa          INT
ss          INT
age         VARCHAR
dr          INT
bc          INT
rd          INT
checked_at  DATETIME
```

### Tabel: cache_domain
```
domain      VARCHAR (PK)
da          INT
pa          INT
ss          INT
age         VARCHAR
dr          INT
bc          INT
rd          INT
cached_at   DATETIME
expired_at  DATETIME
```

---

## Alur Lengkap Bot

### 1. User Baru
```
/start
  └─► Cek apakah sudah terdaftar di DB
       ├── Belum → daftar otomatis + kasih 2 kredit gratis
       └── Sudah → sambut balik

Response:
```
╔══════════════════════╗
║  🔎 DOMAIN ANALYZER  ║
╚══════════════════════╝

  Selamat datang, @username

  Tool ini bisa cek semua metrik
  domain SEO dalam satu kali cek:

  · DA  · PA  · SS  · Age
  · DR  · BC  · RD          (Ahrefs)

  ──────────────────────
  💳 Kamu dapat 5 kredit gratis
  Coba sekarang → kirim domain
  Contoh: google.com
```
```

### 2. Cek Domain
```
User kirim: "google.com"
  └─► Validasi format domain
       ├── Invalid → minta kirim ulang
       └── Valid
            └─► Cek kredit user
                 ├── Kredit = 0 → arahkan ke /topup
                 └── Kredit > 0
                      └─► Cek cache (apakah domain pernah dicek < 24 jam)
                           ├── Ada cache → langsung ambil dari DB
                           └── Tidak ada → masuk Queue scraper
                                └─► Scrape DA/PA/SS + DR/BC/RD + Age
                                     └─► Simpan ke cache + history
                                          └─► Kurangi kredit -1
                                               └─► Kirim hasil ke user

Response:
```
╔══════════════════════╗
║  🔎 DOMAIN ANALYZER  ║
╚══════════════════════╝
  ▸ google.com

  MOZ ──────────────────
  DA  ·  96   PA  ·  77
  SS  ·  1%  ✓ clean

  AGE ──────────────────
  ·  26 years old

  AHREFS ───────────────
  DR  ·  98
  BC  ·  2,400,000
  RD  ·  982,000

  ──────────────────────
  💳 credit left · 9
```
```

### 3. Top Up Kredit
```
/topup
  └─► Bot tampilkan pilihan paket:
      [1] Starter  - 50 kredit  - Rp15.000
      [2] Basic    - 200 kredit - Rp40.000
      [3] Pro      - 500 kredit - Rp75.000
      [4] Bulk     - 1.000 kredit - Rp120.000

User pilih paket
  └─► Bot kirim info rekening/QRIS
       └─► User transfer → kirim bukti (foto/screenshot)
            └─► Bot simpan bukti + buat transaksi status "pending"
                 └─► Notif ke Admin
                      └─► Admin konfirmasi → status "confirmed"
                           └─► Kredit masuk ke user
                                └─► Bot notif user: "Kredit berhasil masuk!"
```

### 4. Cek Kredit
```
/kredit
  └─► "Kredit kamu: 45"
```

### 5. History Cek
```
/history
  └─► Tampil 10 domain terakhir yang pernah dicek
```

---

## Panel Admin

Admin punya akses command khusus:

```
/admin_konfirmasi [transaction_id]  → konfirmasi top up
/admin_reject [transaction_id]      → tolak top up
/admin_addkredit [user_id] [jumlah] → tambah kredit manual
/admin_ban [user_id]                → ban user
/admin_stats                        → statistik total user, cek hari ini, dll
/admin_pending                      → list transaksi yang pending
```

---

## Queue & Worker System

Karena Playwright berat, pakai queue agar tidak crash:

```
Request masuk → masuk antrian (Queue)
                     │
              Worker ambil 1 per 1
                     │
              Scrape → simpan hasil
                     │
              Kirim balik ke user
```

- Max concurrent worker: **3** (agar tidak overload)
- Timeout per request: **30 detik**
- Kalau timeout → retry 1x → kalau gagal lagi → notif user "coba lagi"

---

## Error Handling

| Kondisi | Response Bot |
|---------|-------------|
| Domain tidak valid | "Format domain salah. Contoh yang benar: example.com" |
| Kredit habis | "Kredit kamu habis. Ketik /topup untuk isi ulang." |
| Scraper timeout | "Gagal cek domain, silakan coba lagi." |
| Domain di-block scraper | "Tidak bisa cek domain ini saat ini." |
| Bot overload | "Sedang ramai, kamu masuk antrian ke-X. Tunggu sebentar." |

---

## Struktur Folder Project

> Struktur folder lengkap & detail ada di [STRUKTUR.md](STRUKTUR.md)

Ringkasan layer utama:

```
wkwkwkseo/
├── main.py                  ← entry point
├── .env                     ← config sensitif (token, DB, dll)
├── app/
│   ├── bot/
│   │   ├── handlers/        ← start, check, topup, credit, admin
│   │   ├── middlewares/     ← auth, rate_limit, banned
│   │   └── keyboards/       ← tombol inline & reply
│   ├── scraper/             ← dapachecker, ahrefs, whois
│   ├── services/            ← domain, credit, topup, user service
│   ├── models/              ← user, transaction, history, cache
│   ├── database/            ← connection + migrations/
│   ├── queue/               ← worker + manager
│   └── utils/               ← validator, formatter, logger, constants
├── logs/
├── storage/proofs/
├── tests/
├── docs/
└── scripts/
```

Lihat [STRUKTUR.md](STRUKTUR.md) untuk penjelasan tiap file secara lengkap.

---

## Tech Stack

| Komponen | Library/Tool |
|----------|-------------|
| Bot framework | python-telegram-bot v20 |
| Scraping | Playwright + playwright-stealth |
| Database | SQLite (dev) / MySQL (production) |
| Queue | asyncio Queue / Redis Queue |
| Cache | SQLite / Redis |
| Hosting | VPS Ubuntu |

---

## Keamanan

- Admin ID disimpan di `.env` (bukan hardcode di code)
- Bukti transfer disimpan lokal, tidak dikirim ke luar
- Rate limit: 1 user max 5 request per menit
- Anti spam: domain sama tidak bisa dicek 2x dalam 5 menit oleh user yang sama
