Halo Codex. Kita lanjut ke Fase 4: Laporan. Karena data cleaning (status_pulang, dll) sudah beres, sekarang kita buat modul laporannya.

Tugas 1: Buat file baru bernama `modules/reporter.py`.
Isi dengan fungsi untuk menghitung statistik dan mortalitas:

import pandas as pd

def hitung_statistik_dan_mortalitas(df_long):
    """
    df_long: DataFrame hasil track_perpindahan
    """
    if df_long.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    # Ambil baris terakhir per pasien untuk melihat status akhirnya
    df_last = df_long.sort_values('urutan').groupby('no_rm').tail(1)
    
    # 1. Hitung distribusi status pulang
    status_counts = df_last['status_pulang'].value_counts().reset_index()
    status_counts.columns = ['Status Pulang', 'Jumlah']
    
    # 2. Mortalitas (NDR & GDR)
    total_keluar = len(df_last)
    total_mati = len(df_last[df_last['status_pulang'].str.contains('Meninggal', case=False, na=False)])
    
    # Asumsi NDR = GDR dulu (karena data jam tidak ada)
    gdr = (total_mati / total_keluar * 1000) if total_keluar > 0 else 0
    ndr = gdr 
    
    mortalitas_df = pd.DataFrame({
        'Indikator': ['Total Pasien Keluar', 'Total Pasien Meninggal', 'GDR (per 1000)', 'NDR (per 1000)'],
        'Nilai': [total_keluar, total_mati, round(gdr, 2), round(ndr, 2)]
    })
    
    return status_counts, mortalitas_df

Tugas 2: Update `app.py` di bagian Tab 4 (`with tab4:`).
- Cek apakah `st.session_state.df_clean` ada.
- Panggil fungsi `track_perpindahan` untuk dapatkan `df_long`.
- Panggil `hitung_statistik_dan_mortalitas(df_long)`.
- Tampilkan subheader "📈 Statistik Pasien" dan tabel `status_counts`.
- Tampilkan subheader "🪦 Angka Kematian (Mortalitas)" dan tabel `mortalitas_df`.
- Tambahkan 2 tombol `st.download_button` (satu untuk statistik, satu untuk mortalitas).

Aturan:
- Jangan ubah CSS/tema.
- Setelah selesai, update ke GitHub.