Halo Codex. Hasil audit data menemukan 5 bug fatal di `app.py` dan `modules/cleaner.py`. Tolong perbaiki kodenya PERSIS SEPERTI INSTRUKSI DI BAWAH INI.

Tugas 1: Update `modules/cleaner.py`
Tambahkan fungsi baru untuk menebak JK dari nama (karena kolom JK banyak kosong):
```python
def guess_jk_from_nama(nama):
    if not nama: return None
    s = str(nama).upper()
    # Deteksi kata kunci umum
    if any(w in s for w in ["NYONYA", "NY.", " NY ", "NN", "NONA", "HAJAH", "HJ.", "IBU", "PUAN", "SITI"]): return 'P'
    if any(w in s for w in ["TUAN", "TN.", " TN ", "BAPAK", "BPK", "HAJI", "HJ", "OM"]): return 'L'
    return None
Tugas 2: Update app.py (Proses Data - perbaikan menyeluruh)
Di dalam loop for idx, row in df_temp.iterrows(): saat klik "Proses Data", perbaiki logikanya menjadi:

No RM: Wajib dikonversi jadi String tanpa desimal.
rm_raw = row[map_rm]
rm_clean = str(int(float(rm_raw))) if pd.notna(rm_raw) and str(rm_raw).replace('.','',1).isdigit() else str(rm_raw)

Status Pulang: Pastikan masuk ke dataframe. Tambahkan status_pulang dari mapping kolom.
status_raw = row[map_status] if map_status != "— Pilih kolom —" else None
Masukkan ke dict: "status_pulang": status_raw

Jenis Kelamin (Fix Kosong):
Setelah dapat jk dari split_jk_umur, jika jk is None, panggil guess_jk_from_nama(nama_bersih). Jika hasilnya tetap None, baru biarkan kosong.
if jk is None: jk = guess_jk_from_nama(nama_bersih)

is_titipan (Fix True semua):
Cek perbandingan antara kelas_jam (dari Excel) dan kelas_kamar (dari parse_kamar/master_kelas).
kelas_excel = str(raw_kelas).strip().upper() if raw_kelas else ""
kelas_fisik = str(kelas_kamar).strip().upper() if kelas_kamar else ""
is_titipan = False
if kelas_excel in ['1','2','3','VIP'] and kelas_fisik in ['1','2','3','VIP'] and kelas_excel != kelas_fisik:
is_titipan = True
Simpan is_titipan ke dalam dict hasil.

Fix File Terpotong saat Download:
Pastikan saat memanggil to_excel atau to_csv, tidak ada parameter yang memotong data. Dan pastikan dataframe df_clean sudah di-reset index-nya (df_clean = df_clean.reset_index(drop=True)).

Tugas 3: Tambahkan Selectbox Mapping Status Pulang di app.py
Di UI Pemetaan Kolom, tambahkan satu dropdown lagi untuk "Kolom Status Pulang (Sembuh/Meninggal)". Ini supaya data status nggak hilang.

Jangan sentuh desain/CSS. Jika sudah selesai, jalankan git push ke GitHub.

