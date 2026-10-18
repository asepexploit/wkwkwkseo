# Dokumentasi Sistem Cek DA/PA dan Ahrefs DR/BC/RD

Folder ini berisi dokumentasi lengkap sistem pengecekan metrik domain yang berjalan otomatis selama proses otomasi hosting.

## File dalam folder ini

| File | Isi |
|---|---|
| [01-overview.md](01-overview.md) | Gambaran umum: dua checker, fallback chain, cache, threshold |
| [02-dapachecker-cookies.md](02-dapachecker-cookies.md) | Setup & cara kerja cookies dapachecker.org (sumber utama DA/PA) |
| [03-smallseotools-captcha.md](03-smallseotools-captcha.md) | Fallback DA/PA: smallseotools + guestpostlinks + CaptchaAI |
| [04-ahrefs-dr-bc-rd.md](04-ahrefs-dr-bc-rd.md) | Cara kerja cek Ahrefs DR/BC/RD + sample backlinks |
| [05-ahrefs-captcha-robot.md](05-ahrefs-captcha-robot.md) | Mekanisme klik robot Cloudflare Turnstile di Ahrefs (dua fase) |
| [06-captchaai-client.md](06-captchaai-client.md) | CaptchaAI: setup API key, tipe captcha, polling, timeout |
| [07-captcha-login-panel.md](07-captcha-login-panel.md) | Captcha saat login panel hosting: semua tipe yang didukung |

## Urutan baca yang disarankan

Baca `01-overview.md` dulu untuk gambaran besar, lalu file lain sesuai bagian yang relevan.
