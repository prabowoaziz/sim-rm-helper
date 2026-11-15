import pandas as pd


def track_perpindahan(df):
    """Menerima df_clean dan mengembalikan detail perjalanan pasien per kamar."""
    if df.empty:
        return df.copy()

    d = df.copy()
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

    # Format kamar gabungan
    d['kamar'] = d['kode_kamar'].astype(str) + ' ' + d['ruang'].fillna('').astype(str)

    kolom_long = ['no_rm', 'nama', 'urutan', 'kamar', 'ruang', 'kelas', 'tgl_masuk', 'tgl_keluar', 'masuk', 'pindah', 'dipindahkan']
    if 'kelas_jam' in d.columns:
        kolom_long.append('kelas_jam')
    # Handle jika ada kolom status_pulang, masukkan juga
    if 'status_pulang' in d.columns:
        kolom_long.append('status_pulang')

    return d[kolom_long].copy()
