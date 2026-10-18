# Struktur Folder Project - SEO Domain Checker Bot

```
wkwkwkseo/
│
├── .env                          ← semua config sensitif (token, DB, admin ID)
├── .env.example                  ← template .env untuk referensi
├── .gitignore                    ← exclude .env, __pycache__, logs, dll
│
├── main.py                       ← entry point, jalankan bot dari sini
├── requirements.txt              ← semua dependency Python
│
├── app/
│   ├── __init__.py
│   │
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── handlers/             ← semua command & message handler
│   │   │   ├── __init__.py
│   │   │   ├── start.py          ← /start
│   │   │   ├── check.py          ← cek domain
│   │   │   ├── topup.py          ← /topup flow + terima bukti
│   │   │   ├── credit.py         ← /kredit, /history
│   │   │   └── admin.py          ← semua command admin
│   │   │
│   │   ├── middlewares/          ← layer sebelum handler dijalankan
│   │   │   ├── __init__.py
│   │   │   ├── auth.py           ← cek apakah user terdaftar
│   │   │   ├── rate_limit.py     ← batasi request per user per menit
│   │   │   └── banned.py         ← cek apakah user di-ban
│   │   │
│   │   └── keyboards/            ← semua tombol inline & reply keyboard
│   │       ├── __init__.py
│   │       ├── main_menu.py
│   │       ├── topup_menu.py
│   │       └── admin_menu.py
│   │
│   ├── scraper/                  ← semua logika scraping
│   │   ├── __init__.py
│   │   ├── base.py               ← base class scraper (setup Playwright)
│   │   ├── dapachecker.py        ← scrape DA, PA, SS
│   │   ├── ahrefs.py             ← scrape DR, BC, RD
│   │   └── whois.py              ← cek Age domain
│   │
│   ├── services/                 ← business logic utama
│   │   ├── __init__.py
│   │   ├── domain_service.py     ← orkestrasi: panggil scraper, simpan cache, potong kredit
│   │   ├── credit_service.py     ← logika kredit: tambah, kurangi, cek saldo
│   │   ├── topup_service.py      ← logika top up: buat transaksi, konfirmasi, reject
│   │   └── user_service.py       ← registrasi, get user, ban/unban
│   │
│   ├── models/                   ← definisi tabel database (ORM)
│   │   ├── __init__.py
│   │   ├── user.py               ← model User
│   │   ├── transaction.py        ← model Transaction
│   │   ├── history.py            ← model CheckHistory
│   │   └── cache.py              ← model DomainCache
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py         ← koneksi DB, session management
│   │   └── migrations/           ← script buat/update tabel
│   │       ├── 001_create_users.sql
│   │       ├── 002_create_transactions.sql
│   │       ├── 003_create_history.sql
│   │       └── 004_create_cache.sql
│   │
│   ├── queue/
│   │   ├── __init__.py
│   │   ├── worker.py             ← async worker, proses antrian scraping
│   │   └── manager.py            ← kelola queue, status antrian
│   │
│   └── utils/
│       ├── __init__.py
│       ├── validator.py          ← validasi format domain
│       ├── formatter.py          ← format pesan hasil cek ke teks Telegram
│       ├── logger.py             ← setup logging ke file & console
│       └── constants.py          ← paket harga, teks pesan, konstanta lain
│
├── logs/                         ← file log otomatis (di-gitignore)
│   ├── bot.log
│   ├── scraper.log
│   └── error.log
│
├── storage/                      ← file yang diupload user (bukti transfer)
│   └── proofs/
│
├── tests/                        ← unit test
│   ├── __init__.py
│   ├── test_scraper.py
│   ├── test_services.py
│   └── test_validator.py
│
├── docs/
│   ├── BISNIS.md
│   └── SISTEM.md
│
└── scripts/
    ├── setup.sh                  ← install dependency, setup DB
    └── migrate.py                ← jalankan semua migration
```

---

## Prinsip yang Dipakai

| Prinsip | Penjelasan |
|---------|-----------|
| **Separation of Concerns** | Handler hanya terima input, logic ada di services |
| **Single Responsibility** | Tiap file punya 1 tanggung jawab jelas |
| **Layered Architecture** | bot → services → models → database |
| **Config via .env** | Tidak ada hardcode token/password di code |
| **Migration-based DB** | Perubahan struktur DB terdokumentasi & bisa di-rollback |

---

## Aliran Data

```
User kirim domain
      │
      ▼
Handler (bot/handlers/check.py)
      │
      ▼
Middleware (auth → rate_limit → banned)
      │
      ▼
Service (services/domain_service.py)
      │
      ├─► Cache hit? → ambil dari models/cache.py → format → kirim
      │
      └─► Cache miss → Queue → Worker → Scraper
                                             │
                                        Simpan ke cache & history
                                             │
                                        Potong kredit
                                             │
                                        Format hasil (utils/formatter.py)
                                             │
                                        Kirim ke user
```

---

## File .env (contoh isi)

```env
# Bot
BOT_TOKEN=xxxxxx:xxxxxxxxxxxxxxxx
ADMIN_ID=123456789

# Database
DB_TYPE=sqlite
DB_PATH=./storage/bot.db
# DB_HOST=localhost        ← aktifkan kalau pakai MySQL
# DB_NAME=seobot
# DB_USER=root
# DB_PASS=secret

# Scraper
HEADLESS=true
MAX_WORKERS=3
SCRAPE_TIMEOUT=30

# Cache
CACHE_TTL_HOURS=24

# Rate Limit
RATE_LIMIT_PER_MINUTE=5
```
