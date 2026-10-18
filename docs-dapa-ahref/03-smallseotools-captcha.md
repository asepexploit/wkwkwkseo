# 03 — smallseotools.com & guestpostlinks.net: Fallback DA/PA

Dipakai hanya kalau dapachecker.org gagal atau cookies tidak tersedia. Kedua sumber ini memerlukan penyelesaian **Cloudflare Turnstile** via layanan CaptchaAI sebelum bisa submit.

---

## Fallback 1: smallseotools.com

**URL:** `https://smallseotools.com/id/domain-authority-checker/`

### Alur kerja lengkap

```
1. Buka halaman
2. Isi textarea dengan domain yang ingin dicek
3. Deteksi widget Turnstile di halaman
4. Kirim ke CaptchaAI → tunggu token (sampai 3 menit)
5. Inject token ke field response tersembunyi di form
6. Panggil fungsi JavaScript submit milik situs
7. Tunggu hasil muncul di tabel
8. Kalau ada pesan error dari situs → berhenti lebih awal
```

### Langkah 3 — Deteksi widget Turnstile

Widget Turnstile memiliki atribut `data-sitekey` di DOM. Sistem mencari elemen dengan class `.cf-turnstile` yang punya atribut ini. Nilai sitekey-nya dikirim ke CaptchaAI bersama URL halaman saat ini.

Kalau tidak ada widget Turnstile terdeteksi → skip, anggap sumber ini tidak bisa dipakai saat ini.

### Langkah 4 — Solve via CaptchaAI

Token Turnstile diminta ke CaptchaAI dengan mengirimkan sitekey dan URL halaman. CaptchaAI menyelesaikan di server mereka lalu mengirim token kembali. Proses ini bisa memakan waktu 15 detik sampai 3 menit (lihat detail di `06-captchaai-client.md`).

Log selama menunggu:
```
example.com: cek DA/PA (smallseotools) — captcha terdeteksi, minta solve ke CaptchaAI…
  … menunggu CaptchaAI (15s)
  … menunggu CaptchaAI (20s)
example.com: token captcha diterima (1234 char) — isi ke form…
```

### Langkah 5 — Inject token

Token diisi ke field input tersembunyi (`input[name='cf-turnstile-response']`) via JavaScript langsung di halaman browser. Ini field yang dibaca situs saat validasi form.

### Langkah 6 — Submit

Sistem memanggil fungsi JavaScript `check_validation()` milik situs — bukan klik tombol secara fisik. Lebih reliable karena tidak perlu mencari posisi tombol di DOM.

### Langkah 7 — Tunggu hasil

Poll tabel `#excel_report_section` tiap 1 detik, maksimal 40 detik. Tiap baris dicocokkan dengan domain yang dicari berdasarkan teks di kolom pertama, lalu ambil kolom DA dan PA.

### Langkah 8 — Deteksi error lebih awal

Kalau situs menampilkan pesan error (mis. "Please add valid URLs" atau "Captcha is not loaded") → berhenti langsung tanpa tunggu timeout 40 detik habis.

---

## Fallback 2: guestpostlinks.net

**URL:** `https://tools.guestpostlinks.net/id/bulk-cek-da-pa/`

Dipakai hanya kalau smallseotools juga gagal. Kredit berbayar dan terbatas — dihemat.

### Perbedaan dari smallseotools

| Aspek | smallseotools | guestpostlinks |
|---|---|---|
| Sitekey Turnstile | Diambil dari DOM | **Hardcoded** di sistem |
| Cara submit | Panggil JS `check_validation()` | Klik tombol `#DAPAformsend` |
| Tabel hasil | `#excel_report_section` | `#dapa_tbl` |
| Timeout hasil | 40 detik | 20 detik |
| Baris placeholder | Tidak ada | Ada — perlu diabaikan |

### Kenapa sitekey hardcoded?

Widget Turnstile di guestpostlinks.net tidak menampilkan `data-sitekey` di DOM halaman. Sitekey didapat secara manual dari URL request ke `challenges.cloudflare.com` yang terekam di network tab — kemudian dikodekan langsung ke sistem. Jika suatu saat situs ganti sitekey, nilai ini perlu diperbarui manual.

### Baris placeholder di guestpostlinks

Tabel `#dapa_tbl` merender baris kosong sebelum data AJAX tiba — DA dan PA berisi string kosong `""`. Sistem harus menolak baris ini per baris (bukan asumsi semua domain siap bersamaan) dan terus polling sampai angka muncul.

---

## Mode Batch

Kedua sumber mendukung banyak domain sekaligus per textarea (satu domain per baris). Sistem memanfaatkan ini untuk submit sampai 10 domain dalam satu kali submit, hemat kuota captcha.

Khusus untuk guestpostlinks (batch): domain diurutkan dari yang paling panjang saat mencocokkan hasil. Ini mencegah domain pendek (mis. `shop.com`) salah menangkap baris milik domain lebih panjang (`example-shop.com`) yang ada di batch yang sama — karena pencocokannya berbasis substring.

---

## Data yang dihasilkan

Kedua sumber ini **tidak mendapat SS dan Age** — hanya DA dan PA:

```
{
  "da":  45,
  "pa":  32,
  "ss":  null,
  "age": null
}
```

SS dan Age hanya tersedia dari dapachecker.org (sumber utama).

---

## Diagnostik kalau hasil tidak muncul

Kalau polling habis tanpa hasil, sistem otomatis log snapshot halaman — URL saat ini dan 300 karakter pertama teks halaman. Ini membantu debugging apakah form benar-benar ter-submit (tampilan berubah) atau masih stuck di halaman yang sama.
