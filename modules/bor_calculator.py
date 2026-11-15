import pandas as pd


def hitung_bor(df_long, master_tt, periode_hari=30):
    """Hitung BOR, ALOS, TOI, dan BTO per ruangan serta total rumah sakit."""
    if df_long.empty:
        return pd.DataFrame()

    # Salin agar kalkulasi tidak mengubah dataframe yang dipakai tab Mutasi.
    d = df_long.copy()
    d['tgl_masuk'] = pd.to_datetime(d['tgl_masuk'], errors='coerce')
    d['tgl_keluar'] = pd.to_datetime(d['tgl_keluar'], errors='coerce')
    d['tgl_keluar_isi'] = d['tgl_keluar'].fillna(d['tgl_masuk'])
    d['los'] = (d['tgl_keluar_isi'] - d['tgl_masuk']).dt.days.add(1).clip(lower=1)

    if 'ruang' in d.columns:
        ruang = d['ruang'].astype('string').str.strip()
        ruang_kosong = ruang.isna() | ruang.eq('')
        if 'kode_kamar' in d.columns:
            ruang = ruang.mask(ruang_kosong, d['kode_kamar'].astype('string'))
        d['ruang_final'] = ruang.fillna('Tidak diketahui')
    elif 'kode_kamar' in d.columns:
        d['ruang_final'] = d['kode_kamar'].fillna('Tidak diketahui').astype(str)
    else:
        return pd.DataFrame()

    hasil = []
    total_hari_rawat = 0
    total_pasien_keluar = 0
    total_tt = sum(int(jumlah) for jumlah in master_tt.values())

    for ruang, grp in d.groupby('ruang_final'):
        tt = int(master_tt.get(ruang, 0))
        if tt <= 0:
            continue

        hari_rawat = int(grp['los'].fillna(0).sum())
        pasien_keluar = int(grp['tgl_keluar'].notna().sum())
        kapasitas = tt * periode_hari
        hasil.append({
            'Ruangan': ruang,
            'TT': tt,
            'Hari Rawat': hari_rawat,
            'Pasien Keluar': pasien_keluar,
            'BOR (%)': round(hari_rawat / kapasitas * 100, 2) if kapasitas else 0,
            'ALOS (hari)': round(hari_rawat / pasien_keluar, 2) if pasien_keluar else 0,
            'TOI (hari)': round((kapasitas - hari_rawat) / pasien_keluar, 2) if pasien_keluar else 0,
            'BTO (kali)': round(pasien_keluar / tt, 2),
        })
        total_hari_rawat += hari_rawat
        total_pasien_keluar += pasien_keluar

    if total_tt > 0:
        total_kapasitas = total_tt * periode_hari
        hasil.append({
            'Ruangan': 'TOTAL RS',
            'TT': total_tt,
            'Hari Rawat': total_hari_rawat,
            'Pasien Keluar': total_pasien_keluar,
            'BOR (%)': round(total_hari_rawat / total_kapasitas * 100, 2),
            'ALOS (hari)': round(total_hari_rawat / total_pasien_keluar, 2) if total_pasien_keluar else 0,
            'TOI (hari)': round((total_kapasitas - total_hari_rawat) / total_pasien_keluar, 2) if total_pasien_keluar else 0,
            'BTO (kali)': round(total_pasien_keluar / total_tt, 2),
        })

    return pd.DataFrame(hasil)
