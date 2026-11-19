import pandas as pd


def _episode_key(df):
    """Kunci episode: utamakan no_registrasi jika memiliki isi."""
    if 'no_registrasi' in df.columns and df['no_registrasi'].notna().any():
        return df['no_registrasi'].astype(str)
    return None


def track_perpindahan(df):
    """Kembalikan satu baris untuk setiap segmen kamar dalam suatu episode."""
    d = df.copy()
    kolom_dasar = [
        'no_rm', 'nama', 'kode_kamar', 'ruang', 'kelas', 'tgl_masuk',
        'tgl_keluar', 'status_pulang',
    ]
    for kolom in kolom_dasar:
        if kolom not in d.columns:
            d[kolom] = pd.NA

    # Buang hanya kode Transit IGD yang persis, bukan kode yang sekadar memuat TIG.
    kode = d['kode_kamar'].astype(str).str.strip().str.upper()
    d = d[~kode.isin(['TIG', 'TRANSIT IGD'])]
    d = d[d['no_rm'].notna() & d['kode_kamar'].notna()]
    if d.empty:
        return d.copy()

    d['tgl_masuk'] = pd.to_datetime(d['tgl_masuk'], errors='coerce')
    d['tgl_keluar_episode'] = pd.to_datetime(d['tgl_keluar'], errors='coerce')
    d = d[d['tgl_masuk'].notna()].copy()
    d['_idx'] = d.index
    d = d.sort_values(['no_rm', 'tgl_masuk', 'tgl_keluar_episode', '_idx'], na_position='last')
    d['episode_id'] = None
    ep_counter = 0

    for no_rm, grp in d.groupby('no_rm', sort=False):
        if 'no_registrasi' in grp.columns:
            registrasi = grp['no_registrasi'].astype('string').str.strip()
            registrasi = registrasi.mask(registrasi.eq(''))
        else:
            registrasi = pd.Series(pd.NA, index=grp.index, dtype='string')

        # Nomor registrasi yang tersedia langsung menentukan episode.
        for reg in registrasi.dropna().drop_duplicates().tolist():
            ep_counter += 1
            indexes = grp.index[registrasi.eq(reg)]
            d.loc[indexes, 'episode_id'] = f'{no_rm}-{reg}-{ep_counter}'

        # Baris tanpa nomor registrasi menggunakan jeda antar episode.
        missing_reg = registrasi.isna()
        fallback = grp.loc[missing_reg]
        if not fallback.empty:
            cur_ep = None
            cur_end = None
            for idx, row in fallback.iterrows():
                masuk = row['tgl_masuk']
                keluar = row['tgl_keluar_episode']
                if cur_ep is None or (pd.notna(cur_end) and pd.notna(masuk) and masuk > cur_end):
                    ep_counter += 1
                    cur_ep = f'{no_rm}-EP{ep_counter}'
                    cur_end = keluar
                elif pd.notna(keluar) and (pd.isna(cur_end) or keluar > cur_end):
                    cur_end = keluar
                d.loc[idx, 'episode_id'] = cur_ep

    d = d[d['episode_id'].notna()].copy()
    d = d.sort_values(['episode_id', 'tgl_masuk', '_idx'])
    d['urutan'] = d.groupby('episode_id').cumcount() + 1
    d['total_segmen'] = d.groupby('episode_id')['urutan'].transform('max')
    d['total'] = d['total_segmen']  # Alias untuk pemanggil lama.
    d['is_segmen_terakhir'] = d['urutan'] == d['total_segmen']
    d['masuk'] = d['urutan'] == 1
    d['pindah'] = d['urutan'] > 1
    d['dipindahkan'] = ~d['is_segmen_terakhir']

    d['tgl_keluar_segmen'] = d['tgl_keluar_episode']
    for _, grp in d.groupby('episode_id', sort=False):
        indexes = grp.index.tolist()
        for i in range(len(indexes) - 1):
            d.loc[indexes[i], 'tgl_keluar_segmen'] = d.loc[indexes[i + 1], 'tgl_masuk']

    d['episode_masuk'] = d.groupby('episode_id')['tgl_masuk'].transform('min')

    def hitung_los(masuk, keluar):
        if pd.isna(masuk) or pd.isna(keluar):
            return pd.NA
        hari = (keluar.normalize() - masuk.normalize()).days
        return 1 if hari == 0 else hari

    d['los_episode'] = [
        hitung_los(row['episode_masuk'], row['tgl_keluar_episode'])
        for _, row in d.iterrows()
    ]

    def hitung_hp(masuk, keluar_segmen, terakhir, los):
        if pd.isna(masuk) or pd.isna(keluar_segmen):
            return pd.NA
        hari = (keluar_segmen.normalize() - masuk.normalize()).days
        if pd.notna(los) and los == 1 and terakhir:
            return 1
        return max(0, hari)

    d['hari_rawat_segmen'] = [
        hitung_hp(row['tgl_masuk'], row['tgl_keluar_segmen'],
                  row['is_segmen_terakhir'], row['los_episode'])
        for _, row in d.iterrows()
    ]

    # Pertahankan tgl_keluar untuk pemanggil lama; tanggal asli ada di tgl_keluar_episode.
    d['tgl_keluar'] = d['tgl_keluar_segmen']
    d['kamar'] = d['kode_kamar'].astype(str) + ' ' + d['ruang'].fillna('').astype(str)
    kolom_long = [
        'no_rm', 'nama', 'episode_id', 'urutan', 'total_segmen', 'total',
        'is_segmen_terakhir', 'kamar', 'ruang', 'kelas', 'tgl_masuk', 'tgl_keluar',
        'tgl_keluar_episode', 'tgl_keluar_segmen', 'los_episode', 'hari_rawat_segmen',
        'masuk', 'pindah', 'dipindahkan',
    ]
    for kolom in ['jenis_kelamin', 'diagnosa', 'no_registrasi', 'jam_masuk', 'jam_keluar', 'status_pulang']:
        if kolom in d.columns:
            kolom_long.append(kolom)
    return d[[kolom for kolom in kolom_long if kolom in d.columns]].copy()
