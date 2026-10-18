# 05 — Klik Robot Cloudflare Turnstile di Ahrefs (Dua Fase)

## Kenapa tidak bisa pakai CaptchaAI?

Captcha yang muncul di Ahrefs berbeda dari captcha di smallseotools. Di smallseotools, widget Turnstile punya atribut `data-sitekey` yang bisa dibaca dari DOM halaman — sitekey itu dikirim ke CaptchaAI untuk disolve.

Di Ahrefs, **tidak ada `data-sitekey` yang bisa ditemukan di DOM halaman utama**. Sitekey hanya ada di dalam URL iframe cross-origin (`challenges.cloudflare.com/...`), dan JavaScript di halaman utama tidak bisa mengakses iframe lintas domain karena same-origin policy.

Dibuktikan manual: CaptchaAI membalas `ERROR_CAPTCHA_UNSOLVABLE` untuk sitekey jenis ini.

**Satu-satunya cara**: klik checkbox captcha secara **fisik** menggunakan event mouse CDP (Chrome DevTools Protocol) langsung ke sesi iframe tersebut.

---

## Kapan captcha ini muncul?

Tidak muncul setiap saat — muncul tidak menentu, tapi lebih sering saat:

- Menggunakan VPN (dikonfirmasi dari penggunaan nyata)
- IP sudah di-rate limit oleh Ahrefs

Tanpa VPN: 0 dari 15 percobaan nyata kena captcha. Dengan VPN: cukup sering muncul.

---

## Tampilan fisik captcha ini

Bukan halaman interstitial penuh "Just a moment..." (itu adalah Cloudflare Managed Challenge — tipe berbeda, dibahas di `07-captcha-login-panel.md`).

Yang ini adalah **widget kecil** di sudut halaman — kotak kecil dengan teks "Verifikasi bahwa Anda adalah manusia" / "Verify you are human" dan logo Cloudflare.

---

## Dua fase widget Turnstile

Widget ini tidak langsung menampilkan checkbox. Ada dua fase berurutan:

```
FASE 1: "Melakukan verifikasi..." / "Verifying..."
─────────────────────────────────────────────────
Cloudflare mencoba lolos otomatis via fingerprint browser.
Spinner berputar. TIDAK ADA checkbox yang bisa diklik.
Klik di fase ini → tidak berhasil.

        ↓ kalau verifikasi otomatis gagal

FASE 2: Checkbox muncul
─────────────────────────────────────────────────
"Verifikasi bahwa Anda adalah manusia"
Checkbox BISA diklik dan efektif.
```

Dikonfirmasi manual: klik di detik ke-4 gagal. Klik setelah tunggu ~18–20 detik berhasil (diuji pada tiga domain berbeda).

---

## Solusi: klik dua fase

```
KLIK PERTAMA (segera, tanpa tunggu apapun)
  │
  ├── Return FALSE → tidak ada iframe captcha di halaman
  │                  Lanjut langsung poll hasil (kasus mayoritas)
  │
  └── Return TRUE → captcha terdeteksi, iframe ditemukan
                    Klik ini mungkin belum efektif (masih fase spinner)
                    │
                    Tunggu 10 detik
                    (biarkan fase spinner selesai, checkbox muncul)
                    │
                    KLIK KEDUA (konfirmasi — checkbox sudah siap)
```

### Kenapa klik pertama tidak cukup?

Method klik via CDP return `True` kalau iframe ditemukan dan klik berhasil dikirim — bukan kalau captcha benar-benar terselesaikan. Klik di fase spinner tetap return `True` meskipun tidak efektif secara visual. Makanya butuh klik kedua setelah menunggu.

### Jeda tunggu: 10 detik

Asalnya 19 detik berdasarkan pengujian manual (fase spinner stabil jadi checkbox di detik 18–20). Diturunkan ke 10 detik untuk mempercepat proses.

**Tradeoff:** Semakin pendek jeda, semakin besar risiko klik kedua masih meleset karena widget belum keluar dari fase spinner. Kalau captcha Ahrefs mulai sering gagal diselesaikan, pertimbangkan naikkan kembali ke 15–19 detik.

---

## Cara klik via CDP (bukan JavaScript biasa)

Klik dilakukan dengan mengirim event mouse fisik menggunakan Chrome DevTools Protocol langsung ke **sesi** iframe tersebut — bukan `element.click()` dari JavaScript halaman utama.

Alurnya:
1. Panggil CDP `Target.getTargets()` — dapatkan semua target aktif di browser
2. Cari target yang URL-nya mengandung `"challenges.cloudflare.com"`
3. Kirim CDP `Input.dispatchMouseEvent` ke sesi target tersebut

Ini penting karena iframe cross-origin tidak bisa dijangkau dari JavaScript halaman utama.

---

## Setelah klik berhasil

Setelah klik kedua, Ahrefs memproses verifikasi dan baru kemudian menampilkan hasil DR/BC/RD. Ini **tidak instan** — perlu sekitar 5–10 detik setelah klik. Sistem polling yang mengurus menunggu hasil ini (bukan bagian dari proses klik captcha).

---

## Fail-open

Proses klik captcha ini **tidak pernah menghentikan run** kalau gagal. Kalau klik gagal karena alasan apapun, sistem tetap lanjut polling hasil seperti biasa — kemungkinan besar timeout tanpa hasil, tapi tidak ada error yang menghentikan proses yang lebih besar.

---

## Log yang dihasilkan

```
# Kasus tidak ada captcha (kasus mayoritas):
(tidak ada log, langsung poll)

# Kasus captcha terdeteksi:
example.com: cek DR/BC/RD (Ahrefs) — captcha Turnstile terdeteksi, menunggu (10s) sebelum konfirmasi klik…
example.com: cek DR/BC/RD (Ahrefs) — captcha Turnstile dikonfirmasi diklik
```

---

## Perbandingan dengan tipe captcha lain

| Aspek | Ahrefs Turnstile | smallseotools Turnstile | Managed Challenge |
|---|---|---|---|
| `data-sitekey` di DOM? | Tidak | Ya | Tidak |
| Bisa pakai CaptchaAI? | Tidak | Ya | Tidak |
| Cara selesaikan | Klik fisik CDP | Inject token via JS | Klik fisik CDP |
| Timing klik | Dua fase, tunggu 10 detik | Langsung setelah token siap | Tunggu 35 detik render iframe |
| Cara deteksi | Coba klik → True/False | Cek `data-sitekey` di DOM | Cek judul halaman |
