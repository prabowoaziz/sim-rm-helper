# SIM-RM Helper

Web app untuk membantu pengolahan data rekam medis rumah sakit.
Upload file mentah SIMRS -> dibersihkan -> dihitung -> jadi laporan siap lapor.

## Yang sudah jalan (per 19 Nov 2026, diverifikasi Codex)
- Upload & cleaning data mentah (pilih sheet)
- Track perpindahan kamar pasien (per episode, bukan per baris — masih ada bug double-count hari pindah, lihat Tahap 2/3)
- Hitung BOR, ALOS, TOI, BTO (masih ada bug ALOS +1, lihat Tahap 2)
- Laporan RL 3.1 (Kegiatan Pelayanan Rawat Inap)
- Laporan RL 4a (Morbiditas Rawat Inap + mapping ICD-10)

## Yang BELUM jalan — jangan diklaim sudah ada
- RL 1, RL 2, RL 5
- Laporan Akreditasi lengkap
- Sensus harian (ini yang mau direkonstruksi setelah checkpoint 0 — commit 4002728)
- Retensi / pemusnahan berkas (ada file RETENSI_2026.xlsx terpisah, belum masuk web)

## Checkpoint
- `checkpoint_stable/` = kondisi web SEBELUM rekonstruksi sensus harian.
  Commit: 4002728 "CHECKPOINT 0: kondisi web sebelum rekonstruksi sensus harian"
  Tag: v0.0-pre-rekonstruksi
  Isi: app.py 6 tab + modules/ + .streamlit/ + JANGAN_DIUBAH.md
  ATURAN: JANGAN DIUBAH, JANGAN DITIMPA. Kalau mau kembangin, pakai branch baru.
- `PANDUAN.md` lama BUKAN checkpoint. Itu prompt Codex lama. Sudah di-rename jadi `PROMPT_CODEX_LAMA.md`.

## Cara pakai (untuk istri / staf RM)
1. Buka web, Tab Upload, upload file Excel hasil tarikan SIMRS.
2. Pilih sheet yang benar (contoh: `px masuk` + `px sisa` untuk 1 bulan, bukan semua sheet).
3. Isi Periode (tanggal awal - akhir bulan yang mau dilaporkan). Saat ini web belum ada input periode — periode masih ditebak dari data + batas bulan berjalan. Ini akan diperbaiki di Tahap 2.
4. Cek Tab Mutasi: pastikan 1 pasien yang pindah kamar tidak terhitung 2x.
5. Cek Tab BOR: pastikan Total TT = 100 (cek Master Data). Transit IGD tidak dihitung BOR.
6. Download RL 3.1 / RL 4a dari Tab Laporan.

## Rumus yang dipakai (SIRS Revisi 6.3) — TARGET, belum 100% di kode lama
- **Hari Perawatan (HP)** = jumlah hari kamar terisi, hitung half-open `[masuk, keluar)`. Hari pindah hanya milik kamar baru. Episode same-day = 1 hari.
- **Lama Dirawat (LOS)** = `tgl_keluar_episode - tgl_masuk_episode` (selisih tanggal, same-day = 1). BUKAN `+1` untuk semua.
- **BOR** = HP / (TT x jumlah hari periode) x 100%
- **ALOS** = Total LOS episode yang keluar di periode / Pasien Keluar di periode. BUKAN HP / Keluar.
- **TOI** = (TT x periode - HP) / Pasien Keluar
- **BTO** = Pasien Keluar / TT
- **GDR** = Meninggal / Keluar x 1000
- **NDR** = Meninggal >48 jam / Keluar x 1000. Kalau hanya ada tanggal (tanpa jam), NDR yang tampil adalah nilai minimum + peringatan. Jangan pakai GDR sebagai NDR.

## Tech Stack
- Streamlit (frontend + backend Python)
- Supabase (database + storage) — master TT bisa dari Supabase atau default lokal
- Pandas (olah data)

## Struktur
```
app.py
modules/
  loader.py
  cleaner.py
  tracker.py
  bor_calculator.py
  reporter.py
  master_data.py
  icd_loader.py
checkpoint_stable/   # backup web sebelum rekonstruksi sensus harian, JANGAN DIUBAH
pondasi/             # dokumen/rencana pribadi, TIDAK diimpor web, JANGAN DIUTAK-ATIK
```

## Git — aturan
- Jangan push langsung ke `main`. Pakai branch `fix/...` + Pull Request.
- Jangan simpan data pasien asli ke repo. `.gitignore` sudah mengabaikan *.xlsx/*.xls/*.csv.
- Tag checkpoint yang sudah ada: v0.0-pre-rekonstruksi. Jangan buat tag baru dengan nama sama.
