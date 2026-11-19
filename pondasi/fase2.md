# 📘 FASE 2: Track Perpindahan Kamar (Mutasi)

**Tujuan:** Rekonstruksi perjalanan pasien per kamar berdasarkan data bersih (df_clean) dari Fase 1.

---

## 🤖 PERINTAH UNTUK CODEX (Backend/Logic)

Copy-paste teks di bawah ini ke Codex:

```text
Halo Codex. Sekarang kita masuk ke Fase 2: Track Perpindahan Kamar. Tolong kerjakan instruksi ini.

Tugas 1: Buat file baru bernama `modules/tracker.py`.
Isi dengan fungsi ini:

import pandas as pd

def track_perpindahan(df):
    """
    Menerima df_clean, mengembalikan df_long (detail per kamar) dan df_wide (ringkasan per pasien).
    """
    if df.empty: return df, df
    
    d = df.copy()
    # Buang baris yang tidak punya no_rm atau kamar
    d = d[d['no_rm'].notna() & d['kode_kamar'].notna()]
    
    # Urutkan berdasarkan no_rm, tgl_masuk, dan tgl_keluar
    d['_idx'] = d.index
    d = d.sort_values(['no_rm', 'tgl_masuk', 'tgl_keluar', '_idx'], na_position='last')
    
    # Tandai urutan
    d['urutan'] = d.groupby('no_rm').cumcount() + 1
    d['total'] = d.groupby('no_rm')['urutan'].transform('max')
    
    # Tentukan status Masuk / Pindah / Dipindahkan
    d['masuk'] = d['urutan'] == 1
    d['pindah'] = d['urutan'] > 1
    d['dipindahkan'] = d['urutan'] < d['total']
    
    # Format kamar gabungan
    d['kamar'] = d['kode_kamar'].astype(str) + ' ' + d['ruang'].fillna('').astype(str)
    
    kolom_long = ['no_rm', 'nama', 'urutan', 'kamar', 'ruang', 'kelas', 'tgl_masuk', 'tgl_keluar', 'masuk', 'pindah', 'dipindahkan']
    # Handle jika ada kolom status_pulang, masukkan juga
    if 'status_pulang' in d.columns:
        kolom_long.append('status_pulang')
        
    df_long = d[kolom_long].copy()
    return df_long

Tugas 2: Update `app.py` di bagian Tab 2 (`with tab2:`).
Ganti tulisan "Fitur dalam pengembangan" dengan:
- Cek apakah `st.session_state.df_clean` ada isinya. Jika belum, tampilkan info: "Silakan upload dan proses data di Tab Upload terlebih dahulu."
- Jika ada, panggil fungsi `track_perpindahan` dari `modules/tracker.py`.
- Tampilkan `st.dataframe(df_long, use_container_width=True, hide_index=True)`.
- Tambahkan `st.download_button` untuk mendownload hasil track ini ke Excel.

Aturan:
- Jangan ubah CSS/tema.
- Tampilan UI (judul, subheader) biarkan rapi.
- Setelah selesai, update ke GitHub.