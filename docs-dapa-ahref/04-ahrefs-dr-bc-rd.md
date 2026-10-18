# 04 — Ahrefs DR/BC/RD + Backlinks Sample

## Cara kerja dasar

Tidak ada form fill, tidak ada login, tidak ada cookies. Sistem langsung membuka URL dengan domain target di query string:

```
https://ahrefs.com/id/backlink-checker/?input=<domain>&mode=subdomains
```

Hasil muncul langsung di halaman tersebut tanpa interaksi form apapun.

---

## Alur kerja lengkap

```
1. Buka URL dengan domain di query string
2. Cek apakah ada captcha Turnstile (bisa muncul, terutama saat VPN aktif)
   └─ Ada  → klik dua fase (detail di 05-ahrefs-captcha-robot.md)
   └─ Tidak ada → lanjut langsung
3. Poll halaman tiap 500ms, max 45 detik
   └─ Tunggu label "Peringkat Domain" muncul di DOM + nilai angkanya
4. Begitu DR terisi → ambil semua field (BC, RD, dofollow%) dari halaman yang sama
5. Setelah DR siap → poll tabel sample backlinks terpisah (max 4 detik)
6. Kembalikan hasil
```

---

## Kenapa pakai URL langsung, bukan form?

Percobaan isi-form-manual sempat dicoba tapi lebih rapuh: ada race condition dengan modal cookie-consent atau banner promosi yang kadang menggeser DOM saat form sedang diisi, menyebabkan "URL tidak valid" padahal domain valid. Navigasi langsung via query string tidak punya masalah ini.

---

## URL yang digunakan

Pakai path `/id/` (Indonesia). Deteksi hasil bergantung pada **label teks Indonesia** yang muncul di halaman:

- `"Peringkat Domain"` = Domain Rating (DR)
- `"Backlinks"` = Backlinks (BC)
- `"Situs web penghubung"` = Referring Domains (RD)

**Catatan penting:** Kalau Ahrefs suatu saat mendeteksi bahasa dari header browser alih-alih path URL, label yang dicari akan berbeda → hasil selalu null tapi tidak ada error eksplisit. Kalau hasil tiba-tiba selalu kosong padahal situs bisa diakses, cek apakah label Indonesia masih sama.

---

## Cara membaca hasil dari halaman

Ahrefs adalah aplikasi React — DOM-nya tidak punya ID atau class yang stabil untuk dipakai selector langsung. Sistem menggunakan pendekatan berbeda: **cari berdasarkan teks label, lalu naik ke container induk**.

### Algoritma pencarian

Untuk setiap metrik (DR / BC / RD):

1. Cari elemen terkecil (tidak punya anak) yang teks-nya **persis sama** dengan label Indonesia
2. Naik **7 level parent** ke atas → sampai ke container kartu metrik
3. Di dalam container itu, cari elemen terkecil dengan **font-size >= 30px** — itu nilai metriknya
4. Untuk DR: validasi format angka (boleh desimal, mis. "1.2")
5. Untuk BC/RD: tidak divalidasi format (disimpan apa adanya)
6. Untuk BC/RD: cari juga teks yang cocok pola "NN% dofollow" → ambil angkanya

**Kenapa naik 7 level parent?**
Dicek manual per level langsung ke halaman asli Ahrefs: baris "NN% dofollow" baru muncul di kedalaman 7 — kedalaman 6 tidak mencakupnya.

---

## Tipe data setiap field

| Field | Tipe | Contoh nilai | Catatan |
|---|---|---|---|
| `dr` | angka desimal atau null | `46.0`, `1.2`, `0.0` | Biasanya bulat, tapi bisa desimal untuk domain kecil |
| `bc` | string atau null | `"3.7B"`, `"175M"`, `"451K"`, `"0"` | String apa adanya, TIDAK dikonversi ke angka |
| `rd` | string atau null | `"45K"`, `"1.2M"` | Sama seperti bc |
| `bc_dofollow` | angka bulat atau null | `74`, `100`, `0` | Persentase 0–100 |
| `rd_dofollow` | angka bulat atau null | `68` | Persentase 0–100 |
| `backlinks_sample` | list | `[{...}, {...}]` | List, bisa kosong `[]`, tidak pernah null |

### Kenapa DR bisa desimal?

Dikonfirmasi langsung dari situs: domain kecil/baru menampilkan "Peringkat Domain 1.2" di popup. Sistem sebelumnya hanya menerima angka bulat sehingga DR seperti "1.2" tidak pernah terbaca untuk domain ini.

### Kenapa BC/RD disimpan sebagai string?

Situs menampilkan angka terbulatkan 2 digit signifikan + suffix (B/M/K). Mengonversi ke integer memberikan presisi palsu — "3.7B" bisa berarti 3.700.000.000 atau 3.749.999.999, tidak ada yang tahu pasti.

### Kenapa DR tidak punya dofollow%?

Ahrefs hanya menampilkan baris "NN% dofollow" di bawah BC dan RD — bukan di bawah DR.

---

## Timeout dan polling

- Poll tiap **500ms**, maksimal **45 detik**
- Log progress tiap **5 detik** kalau masih menunggu

45 detik dipilih karena kasus dengan captcha bisa butuh ~10 detik solve captcha + ~10 detik lagi sampai hasil muncul. Kasus tanpa captcha biasanya selesai dalam 2–5 detik.

---

## Tabel sample backlinks

Diambil **terpisah** setelah DR sudah siap — render-nya lebih lambat dari kartu metrik utama. Poll tiap 500ms, maksimal 4 detik.

### Format data

```
backlinks_sample = [
  {
    "dr":          45,              ← angka bulat, DR domain pengirim
    "ref_title":   "Example Blog",  ← judul halaman pengirim
    "ref_url":     "https://...",   ← URL halaman pengirim
    "anchor_text": "klik di sini",  ← teks anchor, bisa null
    "target_url":  "https://..."    ← URL yang di-link ke domain target
  },
  ...  ← biasanya 3 baris kalau tabel muncul
]
```

`anchor_text` bisa `null` kalau backlink adalah gambar atau link tanpa teks.

### Kapan tabel tidak muncul?

Tabel `backlinks_sample` dikembalikan sebagai list kosong `[]` (bukan null) kalau:

- Domain sangat besar (google.com, amazon.com) — Ahrefs tidak tampilkan tabel ini
- Domain sangat kecil/tidak dikenal (DR 0) — tidak ada data
- Tabel tidak muncul dalam 4 detik polling

Ini hasil **valid**, bukan kegagalan.

---

## Fail-open per field

Kalau situs Ahrefs berubah struktur sebagian (mis. DR masih ada tapi BC berubah), field yang berhasil tetap dikembalikan — field yang gagal jadi `null`. Tidak ada field yang "wajib ada". Proses tetap lanjut.

---

## Cache per run

Tiap domain yang sudah dicek disimpan di cache selama run berlangsung. Domain yang sama tidak akan dibuka ulang meski dipanggil berkali-kali. Cache hasil gagal juga disimpan — kalau sekali gagal, tidak dicoba ulang di run yang sama.
