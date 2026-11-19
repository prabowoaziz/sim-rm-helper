# 📘 FASE 3 - PART 2: Kalkulasi BOR, ALOS, TOI, BTO

**Tujuan:** Menghitung indikator pelayanan berdasarkan data bersih dan Master TT.

---

## 🤖 PERINTAH UNTUK CODEX (Backend/Logic)

Copy-paste teks di bawah ini ke Codex:

```text
Halo Codex. Sekarang kita masuk ke perhitungan BOR, ALOS, TOI, dan BTO. Tolong kerjakan instruksi ini.

Tugas 1: Buat file baru bernama `modules/bor_calculator.py`.
Isi dengan kode ini (sesuaikan rumus dengan standar Kemenkes):

import pandas as pd
import numpy as np

def hitung_bor(df_long, master_tt, periode_hari=30):
    """
    df_long: DataFrame hasil track_perpindahan
    master_tt: dict {nama_ruang: jumlah_tt}
    periode_hari: jumlah hari dalam bulan (default 30)
    """
    if df_long.empty:
        return pd.DataFrame()
        
    # Pastikan tgl_masuk dan tgl_keluar berupa datetime
    df_long['tgl_masuk'] = pd.to_datetime(df_long['tgl_masuk'], errors='coerce')
    df_long['tgl_keluar'] = pd.to_datetime(df_long['tgl_keluar'], errors='coerce')
    
    # Isi tgl_keluar yang kosong dengan tgl_masuk (pasien masih dirawat, hitung minimal 1 hari)
    # Sebenarnya idealnya pakai tanggal akhir periode, tapi untuk simplifikasi pakai tgl_masuk
    df_long['tgl_keluar_isi'] = df_long['tgl_keluar'].fillna(df_long['tgl_masuk'])
    
    # Hitung LOS per baris (minimal 1 hari)
    df_long['los'] = (df_long['tgl_keluar_isi'] - df_long['tgl_masuk']).dt.days + 1
    
    hasil = []
    total_hari_rawat_all = 0
    total_pasien_keluar_all = 0
    total_tt_all = sum(master_tt.values())
    
    # Kelompokkan berdasarkan ruang (pastikan pakai nama ruang, bukan kode)
    # Jika ruang kosong, gunakan kode_kamar
    df_long['ruang_final'] = df_long['ruang'].fillna(df_long['kode_kamar'])
    
    for ruang, grp in df_long.groupby('ruang_final'):
        tt = master_tt.get(ruang, 0)
        if tt == 0: continue # Skip kalau TT belum diset
        
        hari_rawat = grp['los'].sum()
        pasien_keluar = len(grp[grp['tgl_keluar'].notna()]) # Pasien yang udah pulang
        
        # Rumus Kemenkes
        bor = (hari_rawat / (tt * periode_hari)) * 100 if tt > 0 else 0
        alos = hari_rawat / pasien_keluar if pasien_keluar > 0 else 0
        toi = ((tt * periode_hari) - hari_rawat) / pasien_keluar if pasien_keluar > 0 else 0
        bto = pasien_keluar / tt if tt > 0 else 0
        
        hasil.append({
            'Ruangan': ruang,
            'TT': tt,
            'Hari Rawat': int(hari_rawat),
            'Pasien Keluar': int(pasien_keluar),
            'BOR (%)': round(bor, 2),
            'ALOS (hari)': round(alos, 2),
            'TOI (hari)': round(toi, 2),
            'BTO (kali)': round(bto, 2)
        })
        
        total_hari_rawat_all += hari_rawat
        total_pasien_keluar_all += pasien_keluar

    # Hitung Total RS
    if total_tt_all > 0:
        bor_all = (total_hari_rawat_all / (total_tt_all * periode_hari)) * 100
        alos_all = total_hari_rawat_all / total_pasien_keluar_all if total_pasien_keluar_all > 0 else 0
        toi_all = ((total_tt_all * periode_hari) - total_hari_rawat_all) / total_pasien_keluar_all if total_pasien_keluar_all > 0 else 0
        bto_all = total_pasien_keluar_all / total_tt_all
        
        hasil.append({
            'Ruangan': 'TOTAL RS',
            'TT': total_tt_all,
            'Hari Rawat': int(total_hari_rawat_all),
            'Pasien Keluar': int(total_pasien_keluar_all),
            'BOR (%)': round(bor_all, 2),
            'ALOS (hari)': round(alos_all, 2),
            'TOI (hari)': round(toi_all, 2),
            'BTO (kali)': round(bto_all, 2)
        })
        
    return pd.DataFrame(hasil)

Tugas 2: Update `app.py` di bagian Tab BOR (tab3).
- Cek apakah `st.session_state.df_clean` dan `st.session_state.master_tt` ada.
- Panggil `track_perpindahan` untuk dapatkan `df_long`.
- Panggil `hitung_bor(df_long, master_tt, periode_hari=30)`.
- Tampilkan hasilnya dalam bentuk tabel (`st.dataframe`) dan metric cards di atasnya untuk TOTAL RS (BOR, ALOS, TOI, BTO).
- Tambahkan tombol `st.download_button` untuk download hasil BOR ini ke Excel.

Aturan:
- Jangan ubah CSS/tema.
- Setelah selesai, update ke GitHub.