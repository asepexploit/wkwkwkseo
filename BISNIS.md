# Bot Telegram SEO Domain Checker - Rancangan Bisnis

## Konsep

Bot Telegram yang bisa cek metrik domain SEO secara otomatis dan langsung di Telegram.
Target user: seller/buyer expired domain, guest post, PBN builder, agency SEO Indonesia.

---

## Metrik yang Dicek (1 cek = semua metrik = 1 kredit)

| Metrik | Sumber |
|--------|--------|
| DA (Domain Authority) | dapachecker.net |
| PA (Page Authority) | dapachecker.net |
| SS (Spam Score) | dapachecker.net |
| Age (Umur Domain) | Whois |
| DR (Domain Rating) | Ahrefs free |
| BC (Backlink Count) | Ahrefs free |
| RD (Referring Domains) | Ahrefs free |

---

## Model Bisnis: Kredit

1 kredit = 1 domain dicek (dapat semua 7 metrik sekaligus)

### Paket Harga

| Paket | Kredit | Harga | Per Cek |
|-------|--------|-------|---------|
| Starter | 50 kredit | Rp15.000 | Rp300/cek |
| Basic | 200 kredit | Rp40.000 | Rp200/cek |
| Pro | 500 kredit | Rp75.000 | Rp150/cek |
| Bulk | 1.000 kredit | Rp120.000 | Rp120/cek |

### Bonus
- User baru gratis **2 kredit** (trial = 2 domain)
- Promo: top up 200 kredit bonus 20 kredit

---

## Keunggulan vs Kompetitor

| Fitur | Bot Ini | Ahrefs | DAPAchecker | Gumroad DR Checker |
|-------|---------|--------|-------------|-------------------|
| All-in-one (DA+PA+SS+DR+BC+RD) | ✅ | ❌ (partial) | ❌ (DA/PA only) | ❌ (DR only) |
| Via Telegram | ✅ | ❌ | ❌ | ❌ |
| Harga terjangkau | ✅ | ❌ ($129+/bln) | gratis (terbatas) | $49 one-time |
| Cocok user Indonesia | ✅ | ❌ | ❌ | ❌ |

---

## Target User

- Buyer/seller **expired domain**
- Pencari **guest post**
- Builder **PBN (Private Blog Network)**
- **Agency SEO** Indonesia
- Freelancer SEO

---

## Alur User di Bot

```
1. User ketik /start
2. Bot sambut + kasih 10 kredit gratis
3. User ketik domain (contoh: example.com)
4. Bot proses → tampil hasil DA/PA/SS/Age/DR/BC/RD
5. Kredit -1
6. Kalau kredit habis → bot minta top up
7. User pilih paket → transfer → kirim bukti → admin konfirmasi → kredit masuk
```

---

## Stack Teknis

- **Bahasa:** Python
- **Library:** python-telegram-bot
- **Scraping:** Playwright + stealth patch
- **Database:** SQLite / MySQL
- **Queue:** Antrian request agar tidak overload
- **Cache:** Simpan hasil cek per domain (expire 24 jam)

---

## Payment

- Transfer bank manual (konfirmasi admin)
- QRIS (target jangka panjang)
- Bisa tambah reseller sistem nanti

---

## Roadmap

- [ ] v1.0 - Bot dasar: cek domain + kredit sistem
- [ ] v1.1 - Top up otomatis (QRIS/midtrans)
- [ ] v1.2 - Cek bulk domain (kirim list sekaligus)
- [ ] v1.3 - Sistem reseller
- [ ] v1.4 - History cek per user
