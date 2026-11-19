import pandas as pd


def _periode(periode_awal, periode_akhir):
    if periode_awal is None or periode_akhir is None:
        raise ValueError("periode_awal dan periode_akhir wajib diisi, jangan ditebak dari data.")
    awal = pd.to_datetime(periode_awal).normalize()
    akhir = pd.to_datetime(periode_akhir).normalize()
    if akhir < awal:
        raise ValueError("periode_akhir harus >= periode_awal")
    return awal, akhir, (akhir - awal).days + 1


def _siapkan_segmen(df_long):
    d = df_long.copy()
    d['tgl_masuk'] = pd.to_datetime(d['tgl_masuk'], errors='coerce').dt.normalize()
    col_keluar = 'tgl_keluar_segmen' if 'tgl_keluar_segmen' in d.columns else 'tgl_keluar'
    d['tgl_keluar_segmen'] = pd.to_datetime(d[col_keluar], errors='coerce').dt.normalize()
    if 'tgl_keluar_episode' in d.columns:
        d['tgl_keluar_episode'] = pd.to_datetime(d['tgl_keluar_episode'], errors='coerce').dt.normalize()
    else:
        d['tgl_keluar_episode'] = d['tgl_keluar_segmen']
    if 'ruang' in d.columns:
        ruang = d['ruang'].astype('string').str.strip()
        if 'kode_kamar' in d.columns:
            ruang = ruang.mask(ruang.isna() | ruang.eq(''), d['kode_kamar'].astype('string'))
        d['ruang_final'] = ruang.fillna('Tidak diketahui')
    elif 'kode_kamar' in d.columns:
        d['ruang_final'] = d['kode_kamar'].fillna('Tidak diketahui').astype(str)
    else:
        d['ruang_final'] = 'Tidak diketahui'

    if 'episode_id' not in d.columns:
        # Tracker lama memberi urutan kamar per no_rm. Tiap baris tetap segmen,
        # dan urutan terakhir menandai episode keluar.
        if 'urutan' in d.columns and 'no_rm' in d.columns:
            d['episode_id'] = d['no_rm'].astype(str)
            d['_is_last'] = d['urutan'].eq(d.groupby('no_rm')['urutan'].transform('max'))
        else:
            d['episode_id'] = d.index.map(lambda i: f"row-{i}")
            d['_is_last'] = True
    else:
        d['_is_last'] = d.get('is_segmen_terakhir', True)
    if 'is_segmen_terakhir' in d.columns:
        d['_is_last'] = d['is_segmen_terakhir'].fillna(False).astype(bool)

    if 'los_episode' not in d.columns:
        ep_first = d.groupby('episode_id')['tgl_masuk'].transform('min')
        ep_exit = d['tgl_keluar_episode']
        d['los_episode'] = (ep_exit - ep_first).dt.days.clip(lower=0)
        same_day = ep_exit.notna() & ep_exit.eq(ep_first)
        d.loc[same_day, 'los_episode'] = 1
    if 'hari_rawat_segmen' not in d.columns:
        d['hari_rawat_segmen'] = (d['tgl_keluar_segmen'] - d['tgl_masuk']).dt.days.clip(lower=0)
        same_day_segmen = d['tgl_keluar_segmen'].notna() & d['tgl_keluar_segmen'].eq(d['tgl_masuk'])
        d.loc[same_day_segmen, 'hari_rawat_segmen'] = 1
    return d


def _episode_keluar_mask(d, awal, akhir):
    return (
        d['_is_last']
        & d['tgl_keluar_episode'].notna()
        & d['tgl_keluar_episode'].between(awal, akhir, inclusive='both')
    )


def _hp_overlap(row, awal, akhir):
    masuk = row['tgl_masuk']
    if pd.isna(masuk):
        return 0
    keluar = row['tgl_keluar_segmen']
    if pd.isna(keluar):
        keluar = akhir + pd.Timedelta(days=1)
    start = max(masuk, awal)
    stop = min(keluar, akhir + pd.Timedelta(days=1))
    hp = (stop - start).days
    if hp <= 0 and pd.notna(row['tgl_keluar_episode']) and row['tgl_keluar_episode'] == masuk:
        return int(awal <= masuk <= akhir)
    return max(0, hp)


def hitung_bor(df_long, master_tt, master_dihitung_bor=None,
               periode_awal=None, periode_akhir=None):
    """BOR / ALOS / TOI / BTO per ruangan dan total RS untuk periode wajib."""
    awal, akhir, periode_hari = _periode(periode_awal, periode_akhir)
    if df_long is None or df_long.empty:
        return pd.DataFrame()
    d = _siapkan_segmen(df_long)
    if master_dihitung_bor:
        d = d[d['ruang_final'].map(lambda r: master_dihitung_bor.get(r, True))]
    d['hp_periode'] = d.apply(_hp_overlap, axis=1, args=(awal, akhir))
    keluar_mask = _episode_keluar_mask(d, awal, akhir)
    tt_dihitung = {
        ruang: int(jumlah) for ruang, jumlah in master_tt.items()
        if not master_dihitung_bor or master_dihitung_bor.get(ruang, True)
    }
    total_tt = sum(tt_dihitung.values())
    hasil = []
    total_hp = total_keluar = 0
    for ruang, grp in d.groupby('ruang_final'):
        tt = tt_dihitung.get(ruang, 0)
        if tt <= 0:
            continue
        hari_rawat = int(grp['hp_periode'].sum())
        keluar_grp = grp.loc[keluar_mask.loc[grp.index]]
        # Per ruangan ALOS memakai HP dari segmen terakhir yang keluar dari ruang itu.
        pasien_keluar = int(keluar_grp['episode_id'].nunique())
        los_ruang = float(keluar_grp.drop_duplicates('episode_id')['hp_periode'].sum())
        kapasitas = tt * periode_hari
        hasil.append({
            'Ruangan': ruang, 'TT': tt, 'Hari Rawat': hari_rawat,
            'Pasien Keluar': pasien_keluar,
            'BOR (%)': round(hari_rawat / kapasitas * 100, 2) if kapasitas else 0,
            'ALOS (hari)': round(los_ruang / pasien_keluar, 2) if pasien_keluar else 0,
            'TOI (hari)': round((kapasitas - hari_rawat) / pasien_keluar, 2) if pasien_keluar else 0,
            'BTO (kali)': round(pasien_keluar / tt, 2),
        })
        total_hp += hari_rawat
        total_keluar += pasien_keluar
    keluar_ep = d.loc[keluar_mask].drop_duplicates('episode_id')
    total_los = float(pd.to_numeric(keluar_ep['los_episode'], errors='coerce').fillna(0).sum())
    if total_tt > 0:
        kapasitas_total = total_tt * periode_hari
        hasil.append({
            'Ruangan': 'TOTAL RS', 'TT': total_tt, 'Hari Rawat': total_hp,
            'Pasien Keluar': total_keluar,
            'BOR (%)': round(total_hp / kapasitas_total * 100, 2),
            'ALOS (hari)': round(total_los / total_keluar, 2) if total_keluar else 0,
            'TOI (hari)': round((kapasitas_total - total_hp) / total_keluar, 2) if total_keluar else 0,
            'BTO (kali)': round(total_keluar / total_tt, 2),
        })
    return pd.DataFrame(hasil)


def hitung_bor_harian(df_long, kapasitas_tt=None, kapasitas_per_kelas=None,
                      periode_awal=None, periode_akhir=None,
                      master_dihitung_bor=None):
    """BOR harian half-open per episode; episode same-day dihitung satu hari."""
    awal, akhir, _ = _periode(periode_awal, periode_akhir)
    columns = ['tanggal', 'pasien_terisi', 'bor_persen']
    if df_long is None or df_long.empty or not kapasitas_tt:
        return pd.DataFrame(columns=columns)
    d = _siapkan_segmen(df_long)
    if master_dihitung_bor:
        d = d[d['ruang_final'].map(lambda room: master_dihitung_bor.get(room, True))]
    d = d[d['tgl_masuk'].notna()]
    rows = []
    for tanggal in pd.date_range(awal, akhir, freq='D'):
        aktif = d[(d['tgl_masuk'] <= tanggal) &
                  (d['tgl_keluar_segmen'].isna() | (d['tgl_keluar_segmen'] > tanggal))]
        same_day = d[(d['tgl_masuk'] == tanggal) & (d['tgl_keluar_segmen'] == tanggal)]
        episode_ids = set(aktif['episode_id'].dropna()) | set(same_day['episode_id'].dropna())
        pasien = len(episode_ids)
        rows.append({'tanggal': tanggal, 'pasien_terisi': pasien,
                     'bor_persen': round(pasien / kapasitas_tt * 100, 2)})
    return pd.DataFrame(rows, columns=columns)


def hitung_bor_kelas(df_mutasi, kapasitas_tt=None, master_dihitung_bor=None,
                     master_tt=None, periode_awal=None, periode_akhir=None):
    """Okupansi harian per kelas dengan periode dan kapasitas yang diberikan."""
    awal, akhir, _ = _periode(periode_awal, periode_akhir)
    columns = ['tanggal', 'VIP', 'BOR_VIP', 'Kelas_1', 'BOR_1', 'Kelas_2',
               'BOR_2', 'Kelas_3', 'BOR_3', 'Total_Pasien', 'BOR_Total']
    if master_tt is not None:
        kapasitas_tt = sum(int(v) for k, v in master_tt.items()
                           if not master_dihitung_bor or master_dihitung_bor.get(k, True))
    if df_mutasi is None or df_mutasi.empty or not kapasitas_tt:
        return pd.DataFrame(columns=columns)
    d = _siapkan_segmen(df_mutasi)
    if master_dihitung_bor:
        d = d[d['ruang_final'].map(lambda r: master_dihitung_bor.get(r, True))]
    d = d[d['tgl_masuk'].notna()]
    kelas = (d['kelas_jaminan'].fillna('Tidak Diketahui').astype(str).str.strip().str.upper()
             if 'kelas_jaminan' in d.columns else pd.Series('Tidak Diketahui', index=d.index))
    kelas = kelas.replace({'': 'TIDAK DIKETAHUI', 'KELAS 1': '1', 'KELAS 2': '2', 'KELAS 3': '3'})
    kelas = kelas.where(~kelas.str.startswith('VIP'), 'VIP')
    rows = []
    for tanggal in pd.date_range(awal, akhir, freq='D'):
        aktif = d[(d['tgl_masuk'] <= tanggal) &
                  (d['tgl_keluar_segmen'].isna() | (d['tgl_keluar_segmen'] > tanggal))]
        same_day = d[(d['tgl_masuk'] == tanggal) & (d['tgl_keluar_segmen'] == tanggal)]
        active = pd.concat([aktif, same_day]).drop_duplicates('episode_id')
        active = active.sort_values('tgl_masuk').drop_duplicates('episode_id', keep='last')
        counts = kelas.loc[active.index].value_counts()
        values = {label: int(counts.get(label, 0)) for label in ('VIP', '1', '2', '3')}
        total = sum(values.values())
        rows.append({'tanggal': tanggal, 'VIP': values['VIP'],
                     'BOR_VIP': round(values['VIP'] / kapasitas_tt * 100, 2),
                     'Kelas_1': values['1'], 'BOR_1': round(values['1'] / kapasitas_tt * 100, 2),
                     'Kelas_2': values['2'], 'BOR_2': round(values['2'] / kapasitas_tt * 100, 2),
                     'Kelas_3': values['3'], 'BOR_3': round(values['3'] / kapasitas_tt * 100, 2),
                     'Total_Pasien': total, 'BOR_Total': round(total / kapasitas_tt * 100, 2)})
    return pd.DataFrame(rows, columns=columns)


def hitung_rata_rata_bor_kelas(df_bor_kelas):
    columns = ['BOR_VIP', 'BOR_1', 'BOR_2', 'BOR_3', 'BOR_Total']
    if df_bor_kelas is None or df_bor_kelas.empty:
        return {column: 0.0 for column in columns}
    return {column: float(df_bor_kelas[column].mean()) if column in df_bor_kelas else 0.0
            for column in columns}


def hitung_rata_rata_bor(df_bor_harian):
    if df_bor_harian is None or df_bor_harian.empty or 'bor_persen' not in df_bor_harian.columns:
        return 0.0
    return round(float(df_bor_harian['bor_persen'].mean()), 2)
