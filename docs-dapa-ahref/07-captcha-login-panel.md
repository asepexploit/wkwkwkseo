# 07 — Captcha Saat Login Panel Hosting

Sistem ini mendeteksi dan menyelesaikan captcha yang muncul di form login panel hosting (cPanel, DirectAdmin, WHMCS, dll). Berbeda dari cek DA/PA dan Ahrefs — ini berjalan saat proses login akun hosting, bukan saat mengecek metrik domain.

---

## Filosofi

**Kalau tidak ada captcha di halaman** → langsung lewat, tidak melakukan apa-apa. Mayoritas panel hosting tidak punya captcha sama sekali.

**Kalau ada captcha tapi gagal diselesaikan** (key CaptchaAI kosong, atau solver timeout) → proses dihentikan dengan pesan error jelas. Melanjutkan submit form tanpa token captcha pasti gagal login — lebih baik berhenti dengan jelas daripada menghasilkan "login gagal" yang membingungkan.

---

## Urutan deteksi captcha

Sistem mencoba tiap tipe berurutan, berhenti di yang pertama terdeteksi:

```
1. Cloudflare Managed Challenge
   Cek: apakah judul halaman mengandung "just a moment"?

2. reCAPTCHA v2
   Cek: apakah ada elemen .g-recaptcha[data-sitekey] di halaman?

3. Cloudflare Turnstile
   Cek: apakah ada elemen .cf-turnstile[data-sitekey] di halaman?

4. Image captcha (gambar teks)
   Cek: apakah ada img[src*=captcha] dan input captcha di halaman?

   ↓ tidak ada satupun terdeteksi

Tidak ada captcha — lanjut submit biasa
```

---

## Tipe 1: Cloudflare Managed Challenge

**Tampilan:** Halaman interstitial penuh dengan teks "Just a moment... Performing security verification", ada spinner berputar, sebelum redirect ke halaman tujuan.

**Cara deteksi:** Bukan cari elemen di DOM, tapi cek **judul halaman** (`document.title`). Kenapa? Karena iframe captcha-nya tidak pernah bisa ditemukan lewat `querySelectorAll` dari halaman utama (same-origin policy + timing render iframe sebagai target CDP).

### Dua kemungkinan resolusi

**A. Auto-resolve (lebih umum)**

Sistem polling judul halaman tiap 1 detik. Kalau judul sudah bukan "just a moment" artinya Cloudflare sudah selesai sendiri (verifikasi otomatis berhasil) → lanjut tanpa klik apapun.

Log: `Cloudflare Managed Challenge: auto-resolve (8s) — title berubah, lanjut tanpa klik.`

**B. Perlu klik manual**

Kalau setelah **35 detik** judul halaman masih "just a moment" → iframe checkbox perlu diklik secara fisik via CDP. Tunggu selama 35 detik dulu karena:

- Dikonfirmasi via websocket CDP langsung ke my.racknerd.com: di detik ke-20 target iframe belum terdaftar di sistem Chrome sama sekali
- Di detik 30–35 baru muncul dan checkbox tergambar di layar
- Klik sebelum iframe ter-render sebagai target CDP → pasti gagal

Setelah diklik, sistem menunggu 4 detik lagi untuk proses verifikasi selesai.

---

## Tipe 2: reCAPTCHA v2 (checkbox "I'm not a robot")

**Cara deteksi:** Cari elemen `.g-recaptcha[data-sitekey]` di halaman.

**Cara selesaikan:**

1. Ambil `data-sitekey` dari widget
2. Kirim ke CaptchaAI: kirimkan sitekey + URL halaman → tunggu token
3. Inject token ke field `#g-recaptcha-response`
4. Kalau widget punya atribut `data-callback` → panggil fungsi callback tersebut dengan token (beberapa situs punya fungsi custom yang dipicu setelah captcha selesai)

---

## Tipe 3: Cloudflare Turnstile (di form login)

**Berbeda dari Ahrefs:** Di form login panel hosting, widget Turnstile biasanya punya `data-sitekey` yang bisa dibaca dari DOM → bisa pakai CaptchaAI.

**Cara deteksi:** Cari elemen `.cf-turnstile[data-sitekey]` di halaman.

**Cara selesaikan:**

1. Ambil `data-sitekey` dari widget
2. Kirim ke CaptchaAI → tunggu token
3. Inject token ke field `input[name='cf-turnstile-response']`
4. Panggil callback kalau ada

---

## Tipe 4: Image captcha (gambar teks)

**Cara deteksi:** Cari elemen gambar dan input yang cocok dengan pola:

- Gambar: `img#captcha_image`, `img.captcha`, `img[src*=captcha]`, `img[alt*=captcha]`, `img[id*=captcha]`
- Input: `input[name=captcha]`, `input[name=security_code]`, `input#captcha`, `input[name=captcha_code]`

**Cara selesaikan:**

1. Ambil bytes gambar via `fetch()` **di dalam browser** (wajib, agar ikut cookie sesi — request Python terpisah bisa dapat gambar berbeda)
2. Kirim bytes gambar ke CaptchaAI → tunggu teks jawaban
3. Isi teks jawaban ke input field captcha

---

## Posisi dalam flow login

Langkah solve captcha selalu dilakukan **setelah** isi username/password dan **sebelum** klik tombol submit:

```
Isi username
Isi password
→ Solve captcha (kalau ada)
Klik submit
```

---

## Selektor yang digunakan (dari konfigurasi terpusat)

Semua selektor captcha disimpan di satu file konfigurasi JSON, urutan dalam array = urutan prioritas:

```
reCAPTCHA v2 widget:      .g-recaptcha[data-sitekey]
                          div[data-sitekey][class*=recaptcha]

reCAPTCHA v2 response:    #g-recaptcha-response
                          textarea[name=g-recaptcha-response]

Turnstile widget:         .cf-turnstile[data-sitekey]
                          div[data-sitekey][class*=turnstile]

Turnstile response:       input[name='cf-turnstile-response']
                          input[name*=turnstile-response]

Image captcha img:        img#captcha_image
                          img.captcha
                          img[src*=captcha]
                          img[alt*=captcha]
                          img[id*=captcha]

Image captcha input:      input[name=captcha]
                          input[name=security_code]
                          input#captcha
                          input[name=captcha_code]
```

Kandidat pertama yang ditemukan di DOM yang dipakai.
