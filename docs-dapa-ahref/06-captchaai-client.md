# 06 — CaptchaAI: Setup, Tipe Captcha, Polling

## Apa itu CaptchaAI?

Layanan solve captcha pihak ketiga berbayar. Cara kerja umum:

1. Sistem mendeteksi captcha di halaman browser
2. Data captcha (sitekey + URL halaman, atau bytes gambar) dikirim ke CaptchaAI
3. CaptchaAI menyelesaikan captcha di server mereka
4. Token hasil dikirim balik ke sistem
5. Token diinjeksikan ke form sebelum submit

- **Base URL:** `https://ocr.captchaai.com`
- **Dokumentasi:** https://docs.captchaai.com/

---

## Setup API Key

Masukkan ke file `.env` di root project:

```
CAPTCHAAI_API_KEY=your_api_key_here
```

Dibaca otomatis saat aplikasi start. Jangan hardcode di kode, jangan masuk ke commit git.

**Kalau key kosong:**

- Untuk cek DA/PA (fallback): hasil null, domain dianggap gagal, run tetap lanjut
- Untuk login panel: proses dihentikan dengan pesan error jelas ("CAPTCHAAI_API_KEY kosong — isi di .env")

**Cek saldo / validasi key** bisa dilakukan dari tombol di GUI tanpa memakai kuota solve.

---

## Tipe captcha yang didukung

### 1. Cloudflare Turnstile

Dipakai untuk: smallseotools.com, guestpostlinks.net, dan panel hosting yang menggunakan Turnstile di form login.

Data yang dikirim ke CaptchaAI:
- Sitekey (dari `data-sitekey` di DOM, atau hardcoded kalau tidak ada di DOM)
- URL halaman saat ini

Hasil: token string panjang yang diinjeksikan ke field tersembunyi `input[name='cf-turnstile-response']`.

### 2. reCAPTCHA v2

Dipakai untuk: panel hosting yang menggunakan checkbox Google "I'm not a robot" di form login.

Data yang dikirim ke CaptchaAI:
- Sitekey (dari `data-sitekey` di widget reCAPTCHA)
- URL halaman saat ini

Hasil: token yang diinjeksikan ke `#g-recaptcha-response` + callback widget dipanggil kalau ada.

### 3. Image captcha (teks dalam gambar)

Dipakai untuk: panel hosting yang menampilkan gambar teks acak di form login.

Data yang dikirim ke CaptchaAI:
- Bytes gambar captcha (PNG)

Hasil: teks jawaban yang diisi ke input field captcha.

**Cara ambil gambar:** Gambar diambil via `fetch()` **di dalam browser** (bukan request HTTP terpisah dari Python) agar ikut menyertakan cookie sesi. Request Python tanpa cookie browser bisa mendapat gambar berbeda dari yang ditampilkan ke user — karena gambar captcha terikat cookie sesi.

---

## Alur polling CaptchaAI

```
1. Kirim task ke endpoint submit → dapat task_id

2. Tunggu 15 detik (initial wait sebelum mulai polling)

3. Loop poll tiap 5 detik:
   ├── status=1, ada token  → SUKSES, return token
   ├── status=0, "CAPCHA_NOT_READY"  → belum siap, poll lagi
   └── status=0, kode error lain  → GAGAL, return null

4. Kalau total waktu > 180 detik → timeout, return null
```

### Kenapa timeout 3 menit?

Dokumentasi CaptchaAI tidak menyebutkan batas waktu resmi — hanya "cek tiap 5 detik sampai dapat token". Captcha nyata (bukan sitekey uji yang selalu instan) bisa butuh lebih dari 2 menit. Jangan persempit timeout ini tanpa pengujian nyata.

---

## Sleep yang bisa diinterupsi (penting untuk tombol Stop)

Polling bisa berlangsung sampai 3 menit. Kalau menggunakan `time.sleep()` biasa, tombol Stop di GUI tidak responsif selama itu — pengguna harus menunggu polling selesai dulu baru Stop bisa bereaksi.

Solusinya: proses sleep selama polling menggunakan mekanisme sleep yang **bisa diinterupsi** oleh tombol Stop. Kalau Stop ditekan saat polling CaptchaAI berjalan, proses langsung berhenti.

Selain itu, tiap jeda polling di-log agar terlihat bahwa sistem masih bekerja (bukan macet):

```
  … menunggu CaptchaAI (15s)
  … menunggu CaptchaAI (20s)
  … menunggu CaptchaAI (25s)
```

---

## Ringkasan konstanta waktu

| Tahap | Durasi |
|---|---|
| Tunggu sebelum poll pertama | 15 detik |
| Interval antar poll | 5 detik |
| Timeout maksimum | 180 detik (3 menit) |
