import pandas as pd


def hitung_bor(df_long, master_tt, master_dihitung_bor=None, periode_hari=30):
    """Hitung BOR, ALOS, TOI, dan BTO per ruangan serta total rumah sakit."""
    if df_long.empty:
        return pd.DataFrame()
    if master_dihitung_bor:
        df_long = df_long[df_long['ruang'].map(lambda r: master_dihitung_bor.get(r, True))]
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


def hitung_bor_kelas(df_mutasi, kapasitas_tt=35):
    """Hitung okupansi harian dan BOR untuk kelas jaminan VIP, 1, 2, dan 3."""
    columns = [
        'tanggal', 'VIP', 'BOR_VIP', 'Kelas_1', 'BOR_1', 'Kelas_2', 'BOR_2',
        'Kelas_3', 'BOR_3', 'Total_Pasien', 'BOR_Total',
    ]
    if df_mutasi.empty or kapasitas_tt <= 0:
        return pd.DataFrame(columns=columns)

    required = {'tgl_masuk', 'tgl_keluar', 'kelas_jam'}
    if not required.issubset(df_mutasi.columns):
        return pd.DataFrame(columns=columns)

    d = df_mutasi.copy()
    d['tgl_masuk'] = pd.to_datetime(d['tgl_masuk'], errors='coerce').dt.normalize()
    d['tgl_keluar'] = pd.to_datetime(d['tgl_keluar'], errors='coerce').dt.normalize()
    d = d[d['tgl_masuk'].notna()]
    if d.empty:
        return pd.DataFrame(columns=columns)

    tanggal_awal = d['tgl_masuk'].min()
    tanggal_akhir = max(d['tgl_masuk'].max(), d['tgl_keluar'].max())
    tanggal_semua = pd.date_range(tanggal_awal, tanggal_akhir, freq='D')
    kelas = d['kelas_jam'].fillna('Tidak Diketahui').astype(str).str.strip().str.upper()
    kelas = kelas.replace({'': 'TIDAK DIKETAHUI', 'KELAS 1': '1', 'KELAS 2': '2', 'KELAS 3': '3'})
    kelas = kelas.where(~kelas.str.startswith('VIP'), 'VIP')
    occupancy = {key: [] for key in ('VIP', '1', '2', '3')}

    for tanggal in tanggal_semua:
        # Tanggal keluar tidak dihitung sebagai hari rawat, sesuai konvensi hari rawat.
        aktif = d[
            (d['tgl_masuk'] <= tanggal)
            & (d['tgl_keluar'].isna() | (d['tgl_keluar'] > tanggal))
        ]
        aktif_kelas = kelas.loc[aktif.index]
        counts = aktif_kelas.value_counts()
        for key in occupancy:
            occupancy[key].append(int(counts.get(key, 0)))

    result = pd.DataFrame({
        'tanggal': tanggal_semua,
        'VIP': occupancy['VIP'],
        'BOR_VIP': [round(count / kapasitas_tt * 100, 2) for count in occupancy['VIP']],
        'Kelas_1': occupancy['1'],
        'BOR_1': [round(count / kapasitas_tt * 100, 2) for count in occupancy['1']],
        'Kelas_2': occupancy['2'],
        'BOR_2': [round(count / kapasitas_tt * 100, 2) for count in occupancy['2']],
        'Kelas_3': occupancy['3'],
        'BOR_3': [round(count / kapasitas_tt * 100, 2) for count in occupancy['3']],
    })
    result['Total_Pasien'] = result[['VIP', 'Kelas_1', 'Kelas_2', 'Kelas_3']].sum(axis=1)
    result['BOR_Total'] = (result['Total_Pasien'] / kapasitas_tt * 100).round(2)
    return result[columns]


def hitung_rata_rata_bor_kelas(df_bor_kelas):
    """Kembalikan rata-rata BOR harian untuk tiap kelas dan total."""
    bor_columns = ['BOR_VIP', 'BOR_1', 'BOR_2', 'BOR_3', 'BOR_Total']
    if df_bor_kelas.empty:
        return {column: 0.0 for column in bor_columns}
    return {
        column: float(df_bor_kelas[column].mean()) if column in df_bor_kelas else 0.0
        for column in bor_columns
    }


def hitung_bor_harian(df_long, kapasitas_tt=35):
    """Hitung jumlah pasien terisi dan BOR untuk setiap tanggal."""
    columns = ['tanggal', 'pasien_terisi', 'bor_persen']
    if df_long.empty or kapasitas_tt <= 0:
        return pd.DataFrame(columns=columns)

    required = {'tgl_masuk', 'tgl_keluar'}
    if not required.issubset(df_long.columns):
        return pd.DataFrame(columns=columns)

    d = df_long.copy()
    d['tgl_masuk'] = pd.to_datetime(d['tgl_masuk'], errors='coerce').dt.normalize()
    d['tgl_keluar'] = pd.to_datetime(d['tgl_keluar'], errors='coerce').dt.normalize()
    d = d[d['tgl_masuk'].notna()]
    if d.empty:
        return pd.DataFrame(columns=columns)

    tanggal_awal = d['tgl_masuk'].min()
    tanggal_akhir = d['tgl_keluar'].max()
    if pd.isna(tanggal_akhir):
        tanggal_akhir = d['tgl_masuk'].max()
    else:
        tanggal_akhir = max(tanggal_akhir, d['tgl_masuk'].max())

    rows = []
    for tanggal in pd.date_range(tanggal_awal, tanggal_akhir, freq='D'):
        aktif = d[
            (d['tgl_masuk'] <= tanggal)
            & (d['tgl_keluar'].isna() | (d['tgl_keluar'] > tanggal))
        ]
        pasien_terisi = (
            int(aktif['no_rm'].nunique())
            if 'no_rm' in aktif.columns
            else len(aktif)
        )
        rows.append({
            'tanggal': tanggal,
            'pasien_terisi': pasien_terisi,
            'bor_persen': round(pasien_terisi / kapasitas_tt * 100, 2),
        })
    return pd.DataFrame(rows, columns=columns)


def hitung_rata_rata_bor(df_bor_harian):
    """Kembalikan rata-rata BOR harian dalam persen."""
    if df_bor_harian.empty or 'bor_persen' not in df_bor_harian.columns:
        return 0.0
    return round(float(df_bor_harian['bor_persen'].mean()), 2)
