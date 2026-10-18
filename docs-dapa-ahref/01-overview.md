# 01 — Overview: Sistem Cek DA/PA & Ahrefs

## Apa yang dicek

Sistem ini mengecek dua paket metrik domain secara otomatis selama proses otomasi hosting.

### Paket 1: DA/PA/SS/Domain Age
- **DA** (Domain Authority) — skor 0–100 dari Moz
- **PA** (Page Authority) — skor 0–100 dari Moz
- **SS** (Spam Score) — persentase 0–100 dari Moz
- **Age** (Domain Age) — string bebas, contoh: "1 Years, 3 Months"

### Paket 2: Ahrefs DR/BC/RD + Backlinks Sample
- **DR** (Domain Rating) — skor 0–100 dari Ahrefs (bisa desimal, mis. "1.2" untuk domain kecil/baru)
- **BC** (Backlinks) — jumlah backlink, disimpan sebagai string: "3.7B", "175M", "451K", "0"
- **RD** (Referring Domains) — jumlah domain pengirim, string apa adanya
- **BC dofollow** — persentase dofollow dari total BC (angka bulat 0–100)
- **RD dofollow** — persentase dofollow dari total RD (angka bulat 0–100)
- **Backlinks Sample** — contoh 3 baris tabel backlink (DR pengirim / halaman rujukan / anchor + target URL)

---

## Dua checker yang bekerja secara independen

Kedua checker dipanggil berdampingan dalam satu proses. Satu gagal tidak mempengaruhi yang lain.

---

## Fallback chain DA/PA

```
┌─────────────────────────────────────────┐
│  1. dapachecker.org                     │  ← UTAMA
│     Premium, login via cookies          │
│     Tidak ada captcha sama sekali       │
│     Data: DA, PA, SS, Age               │
└────────────────┬────────────────────────┘
                 │ gagal / cookies expired / tidak ada
                 ▼
┌─────────────────────────────────────────┐
│  2. smallseotools.com                   │  ← Fallback 1
│     Perlu solve Turnstile via CaptchaAI │
│     Data: DA, PA saja (SS/Age = None)   │
└────────────────┬────────────────────────┘
                 │ gagal
                 ▼
┌─────────────────────────────────────────┐
│  3. guestpostlinks.net                  │  ← Fallback 2 / Last resort
│     Perlu solve Turnstile via CaptchaAI │
│     Kredit berbayar terbatas            │
│     Data: DA, PA saja (SS/Age = None)   │
└─────────────────────────────────────────┘
                 │ semua gagal
                 ▼
              None  ← fail-open, proses tetap lanjut
```

---

## Fallback chain Ahrefs DR

```
┌─────────────────────────────────────────┐
│  ahrefs.com/id/backlink-checker/        │  ← SATU-SATUNYA sumber
│  Tidak ada login, tidak ada cookies     │
│  Langsung buka URL dengan query domain  │
│  Captcha Turnstile: klik fisik CDP      │
│  (bukan solve via CaptchaAI)            │
└─────────────────────────────────────────┘
                 │ gagal / timeout
                 ▼
              None  ← fail-open, proses tetap lanjut
```

---

## Cache per run

Semua hasil di-cache selama satu run berjalan. Cache berlaku per domain, shared antar semua jalur.

```
DA/PA cache:
  "example.com" → {da: 45, pa: 32, ss: 12, age: "2 Years"}
  "badsite.com" → None   ← hasil gagal juga di-cache, tidak dicoba ulang

DR/BC/RD cache:
  "example.com" → {dr: 46.0, bc: "1.2M", rd: "45K", ...}
  "badsite.com" → {dr: None, bc: None, ...}
```

Domain yang sudah dicek lewat jalur manapun **tidak akan dicek ulang** di run yang sama — termasuk subdomain berbeda dengan root domain yang sama (mis. `shop.example.com` dan `blog.example.com` cukup cek satu kali untuk root `example.com`).

---

## Threshold DA/PA

| Threshold | Nilai | Efek |
|---|---|---|
| DA minimum skip upload SEO | 30 | DA ≥ 30 → upload SEO dilewati otomatis |
| DA minimum CpanelSel | 20 | DA ≥ 20 → akun ditandai sebagai CpanelSel |

---

## Filosofi: best-effort / fail-open

Semua checker **tidak pernah menghentikan run** kalau gagal. Kalau semua sumber gagal, hasilnya `None` dan proses tetap lanjut upload SEO / ganti NS seperti biasa.

Gangguan sesaat di situs pihak ketiga (dapachecker timeout, smallseotools down, Ahrefs rate limit) tidak pernah memblokir run utama.

---

## Mode operasi DA/PA

### Single domain
Cek satu domain, dengan cache. Kalau sudah pernah dicek di run ini, pakai hasil cache.

### Batch (sampai 10 domain per submit)
Submit banyak domain sekaligus ke satu form — jauh lebih efisien untuk banyak domain karena 1 captcha solve bisa mencakup sampai 10 domain sekaligus.

### Ahrefs selalu satu per satu
Tidak ada batch-submit sungguhan di Ahrefs — tiap domain buka URL terpisah satu per satu, tapi tetap cache-aware.
