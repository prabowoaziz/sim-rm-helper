Halo Codex. Sekarang kita masuk ke fitur Pemetaan Kolom dan Data Cleaning. Tolong kerjakan instruksi ini.

Tugas 1: Buat file baru bernama `modules/cleaner.py`.
Isi dengan fungsi-fungsi pembersih ini (gunakan regex `re`):

import pandas as pd
import re
from datetime import datetime

def clean_nama(val):
    if pd.isna(val): return None
    s = str(val).strip()
    s = re.sub(r'\s*\([^)]*\)\s*$', '', s)
    return s.upper().strip()

def split_jk_umur(val):
    if pd.isna(val): return None, None
    s = str(val).strip()
    m = re.match(r'([A-Za-z]+)\s*\((\d+)\s*(Th|Bl|Hr)?\)', s, re.IGNORECASE)
    if not m:
        jk_only = re.match(r'([A-Za-z]+)', s)
        return (jk_only.group(1).upper() if jk_only else None), None
    jk = m.group(1).upper()
    angka = int(m.group(2))
    satuan = (m.group(3) or 'Th').lower()
    if satuan == 'bl': umur = round(angka / 12, 2)
    elif satuan == 'hr': umur = round(angka / 365, 2)
    else: umur = float(angka)
    return jk, umur

def kategori_umur(umur):
    if umur is None or pd.isna(umur): return None
    if umur < 0.08: return 'Neonatus'
    if umur < 1: return 'Bayi'
    if umur < 5: return 'Balita'
    if umur < 18: return 'Anak'
    if umur < 60: return 'Dewasa'
    return 'Lansia'

def parse_kamar(val):
    if pd.isna(val): return None, None, None
    s = str(val).strip()
    parts = s.split(' ', 1)
    kode = parts[0]
    ruang = parts[1] if len(parts) > 1 else None
    tokens = kode.split('-')
    kelas = tokens[1] if len(tokens) > 1 else None
    return kode, ruang, kelas

Tugas 2: Update file `app.py`.
Di bawah preview tabel (jika df berhasil diload), tambahkan UI untuk Mapping Kolom menggunakan `st.selectbox`:
- Buat list nama kolom dari df (misal: `kolom_options = list(df.columns)`).
- Tampilkan 6 selectbox (bisa pakai `st.columns(2)` biar rapi) untuk memilih:
  1. Kolom Nama Pasien
  2. Kolom JK/Umur
  3. Kolom No. RM
  4. Kolom Kamar
  5. Kolom Tanggal Masuk
  6. Kolom Tanggal Keluar

Tugas 3: Tambahkan tombol `st.button("🚀 Proses Data")`.
Jika tombol diklik:
- Ambil DataFrame asli.
- Petakan kolom yang dipilih user.
- Panggil fungsi dari `modules/cleaner.py` untuk membersihkan Nama, memisah JK/Umur, dan memisah Kamar.
- Buat DataFrame baru bernama `df_clean` dengan kolom standar: `no_rm, nama, jenis_kelamin, umur_tahun, kategori_umur, kode_kamar, ruang, kelas, tgl_masuk, tgl_keluar`.
- Simpan `df_clean` ke `st.session_state.df_clean`.
- Tampilkan `st.dataframe(df_clean.head())` dan tombol `st.download_button` untuk mendownload file Excel bersih ini (gunakan `to_csv` atau `to_excel` di dalam buffer `io.BytesIO`).

Aturan:
- Jangan ubah CSS/tema.
- Gunakan `pd.to_datetime(..., errors='coerce')` untuk format tanggal.
- Setelah selesai, update ke GitHub.