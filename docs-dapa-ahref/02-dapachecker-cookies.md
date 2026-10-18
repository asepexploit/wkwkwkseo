# 02 — dapachecker.org: Sumber Utama DA/PA dengan Cookies Premium

## Kenapa pakai cookies?

dapachecker.org menawarkan akun premium yang **tidak pernah menampilkan captcha** selama cookies login valid. Ini jauh lebih cepat dan hemat dibanding sumber fallback yang harus solve captcha tiap kali.

Kalau file cookies tidak ada atau sudah expired → langsung lompat ke smallseotools.com, tidak buang waktu membuka dapachecker sama sekali.

---

## Setup cookies (dilakukan satu kali oleh operator)

### Langkah-langkah

1. Login ke `https://www.dapachecker.org/` di Chrome biasa (bukan incognito)
2. Install ekstensi **EditThisCookie** (atau "Cookie-Editor") dari Chrome Web Store
3. Pastikan sudah login ke dapachecker.org
4. Klik ikon ekstensi → **Export cookies** (pilih format JSON)
5. Simpan file JSON ke folder `cokies/` di root project dengan nama `dapachecker.json`

### Lokasi file

```
root project/
└── cokies/
    └── dapachecker.json
```

Lokasi bisa diubah via environment variable `DAPACHECKER_COOKIES_PATH`.

### Format file cookie (hasil export EditThisCookie)

```json
{
  "url": "https://www.dapachecker.org",
  "cookies": [
    {
      "domain": ".dapachecker.org",
      "name": "_ga",
      "value": "GA1.1.xxxxxxx",
      "path": "/",
      "expirationDate": 1824211499,
      "hostOnly": false,
      "httpOnly": false,
      "sameSite": "unspecified",
      "secure": false,
      "session": false
    },
    { "..." }
  ]
}
```

Field wajib per cookie: `name` dan `domain`. Field lain yang hilang atau salah tipe diabaikan per cookie (tidak gagal baca seluruh file).

---

## Kapan cookies perlu diperbarui?

Cookies punya masa berlaku (`expirationDate`). Tanda cookies sudah expired di log run:

```
dapachecker.org: halaman tak siap setelah 35s (Cloudflare challenge belum selesai / cookie expired) — coba sumber cadangan…
```

atau:

```
dapachecker.org: N domain tak dapat hasil dalam 40s (cookie mungkin expired) — coba sumber cadangan…
```

Solusi: login ulang ke dapachecker.org, export cookies lagi, timpa file lama.

---

## Alur kerja saat run berjalan

### 1. Cek awal — apakah file cookies tersedia?

Sebelum membuka browser sama sekali, sistem cek apakah file cookies ada dan valid. Kalau tidak ada atau semua cookie invalid → langsung fallback ke smallseotools, tidak buka dapachecker.

### 2. Inject cookies ke Chrome (satu kali per sesi run)

Cookie diinjeksikan ke Chrome incognito yang sedang berjalan. Dilakukan **satu kali saja** per sesi run — tidak diulang per domain. Setelah diinjeksikan, cookie berlaku untuk semua request berikutnya ke dapachecker.org dalam sesi yang sama.

Log saat berhasil:
```
dapachecker.org: 12/15 cookie berhasil dipasang (login premium)
```

### 3. Buka halaman dapachecker.org

Cloudflare "Just a moment..." bisa muncul sebelum halaman asli load. Ini **bukan captcha yang perlu diklik** — Cloudflare akan auto-resolve sendiri dalam beberapa detik untuk browser sungguhan dengan cookies valid.

Sistem menunggu sampai textarea input domain muncul di halaman, maksimal **35 detik**. Kalau belum muncul juga → cookies mungkin expired → fallback ke smallseotools.

### 4. Isi domain dan submit

Domain dimasukkan ke textarea — bisa banyak domain sekaligus (satu per baris). Setelah diisi, sistem **menunggu 500ms** sebelum klik tombol. Kenapa? Situs punya validasi JavaScript yang jalan otomatis setelah textarea diisi — klik terlalu cepat sebelum validasi selesai menyebabkan tombol tidak merespons.

### 5. Tunggu hasil

Sistem polling tiap 1 detik, maksimal 40 detik. Hasil dibaca dari tabel hasil di halaman — tiap baris punya atribut domain yang dicocokkan dengan domain yang dicari.

### 6. Bug yang pernah terjadi: angka kosong di putaran pertama

Baris hasil di tabel muncul di DOM **seketika** setelah request AJAX dikirim — tapi isi angkanya masih string kosong `""` sampai data benar-benar tiba. Cek yang benar harus menolak string kosong (bukan hanya `null`) — kalau tidak, domain akan dianggap gagal di putaran pertama padahal data belum datang.

### 7. Grace period untuk kolom Age

Kolom Domain Age render **lebih lambat** dari DA/PA/SS — kadang muncul beberapa detik setelahnya. Kalau DA/PA sudah ada tapi Age masih kosong, sistem menunggu sekitar 20 detik ekstra sebelum menerima `age = null`. Kalau tetap tidak muncul, Age disimpan sebagai null dan proses lanjut.

---

## Data yang dihasilkan

```
{
  "da":  45,                    ← angka bulat
  "pa":  32,                    ← angka bulat
  "ss":  12,                    ← angka bulat (persentase spam score)
  "age": "1 Years, 3 Months"   ← string mentah, tidak di-parse
}
```

`age` disimpan sebagai string apa adanya karena formatnya beda-beda tergantung locale situs ("30 Years", "Menos de 1 año", dll) — tidak ada cara parse ke angka yang aman dan universal.

---

## Batch: banyak domain sekaligus

dapachecker.org mendukung banyak URL per baris di textarea. Ini dimanfaatkan untuk submit sampai **10 domain sekaligus** per satu submit. Hasil semua domain dibaca sekaligus dari tabel dalam satu evaluasi JavaScript — efisien, tidak perlu klik submit berkali-kali.
