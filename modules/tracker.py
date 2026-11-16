import pandas as pd


def track_perpindahan(df):
    """Menerima df_clean dan mengembalikan detail perjalanan pasien per kamar."""
    d = df.copy()
    # Sediakan kolom dasar agar data lama atau tidak lengkap tetap dapat diproses.
    kolom_dasar = [
        'no_rm', 'nama', 'kode_kamar', 'ruang', 'kelas', 'tgl_masuk',
        'tgl_keluar', 'status_pulang',
    ]
    for kolom in kolom_dasar:
        if kolom not in d.columns:
            d[kolom] = pd.NA

    # Buang Transit IGD dari hitungan
    d = d[~d['kode_kamar'].astype(str).str.contains('TIG|Transit IGD', case=False, na=False)]
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
    # Pecah LOS per segmen kamar
    d['tgl_masuk'] = pd.to_datetime(d['tgl_masuk'], errors='coerce')
    d['tgl_keluar'] = pd.to_datetime(d['tgl_keluar'], errors='coerce')
    d = d.sort_values(['no_rm', 'urutan'])
    d['tgl_masuk_segmen'] = d['tgl_masuk']
    d['tgl_keluar_segmen'] = d['tgl_keluar']
    for rm in d['no_rm'].unique():
        mask = d['no_rm'] == rm
        idx = d[mask].index.tolist()
        for i in range(len(idx) - 1):
            d.loc[idx[i], 'tgl_keluar_segmen'] = d.loc[idx[i+1], 'tgl_masuk']
    d['tgl_masuk'] = d['tgl_masuk_segmen']
    d['tgl_keluar'] = d['tgl_keluar_segmen']
    d = d.drop(columns=['tgl_masuk_segmen', 'tgl_keluar_segmen'])

    # Format kamar gabungan
    d['kamar'] = d['kode_kamar'].astype(str) + ' ' + d['ruang'].fillna('').astype(str)

    kolom_long = ['no_rm', 'nama', 'urutan', 'kamar', 'ruang', 'kelas', 'tgl_masuk', 'tgl_keluar', 'masuk', 'pindah', 'dipindahkan']
    for kolom_tambahan in ['jenis_kelamin', 'diagnosa']:
        if kolom_tambahan in d.columns:
            kolom_long.append(kolom_tambahan)
    if 'kelas_jam' in d.columns:
        kolom_long.append('kelas_jam')
    # Handle jika ada kolom status_pulang, masukkan juga
    if 'status_pulang' in d.columns:
        kolom_long.append('status_pulang')

    kolom_tersedia = [col for col in kolom_long if col in d.columns]
    return d[kolom_tersedia].copy()
