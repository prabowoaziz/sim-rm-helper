import pandas as pd

def _baris_terakhir_per_episode(df_long):
    """Ambil 1 baris terakhir per episode. Kalau episode_id nggak ada, fallback ke no_rm."""
    if df_long is None or df_long.empty:
        return pd.DataFrame()
    if 'episode_id' in df_long.columns and df_long['episode_id'].notna().any():
        # Grouping per episode_id, bukan per no_rm — 1 pasien bisa punya 2 episode
        if 'urutan' in df_long.columns:
            return df_long.sort_values('urutan').groupby('episode_id', dropna=False).tail(1)
        return df_long.groupby('episode_id', dropna=False).tail(1)
    # Fallback data lama: grouping per no_rm
    if 'urutan' in df_long.columns:
        return df_long.sort_values('urutan').groupby('no_rm', dropna=False).tail(1)
    return df_long.groupby('no_rm', dropna=False).tail(1)

def _is_keluar(row_status, tgl_keluar_episode):
    """Episode udah keluar atau masih dirawat?"""
    s = str(row_status or '').strip().lower()
    if s in ('', 'masih dirawat', 'masih di rawat', 'dirawat', 'nan', 'none'):
        # Kalau status kosong / masih dirawat, cek tgl_keluar_episode
        if tgl_keluar_episode is None or (isinstance(tgl_keluar_episode, float) and pd.isna(tgl_keluar_episode)):
            return False
        try:
            return not pd.isna(tgl_keluar_episode)
        except Exception:
            return False
    return True

def _los_episode_value(row):
    """Ambil LOS episode: los_episode dulu, fallback los_hari / LOS / los."""
    for col in ('los_episode', 'los_hari', 'LOS', 'los', 'los_episode_hari'):
        if col in row and row[col] is not None:
            try:
                v = float(row[col])
                if not pd.isna(v):
                    return v
            except Exception:
                continue
    return None

def hitung_statistik_dan_mortalitas(df_long):
    """Hitung distribusi status akhir pasien dan angka mortalitas. Denominator = pasien keluar aja, bukan termasuk masih dirawat."""
    if df_long is None or df_long.empty:
        return pd.DataFrame(), pd.DataFrame()
    df_last = _baris_terakhir_per_episode(df_long).copy()
    if df_last.empty:
        return pd.DataFrame(), pd.DataFrame()
    # Status pulang
    if 'status_pulang' in df_last.columns:
        status = df_last['status_pulang'].astype('string').fillna('')
    else:
        status = pd.Series('', index=df_last.index, dtype='string')
        df_last['status_pulang'] = ''
    # Tgl keluar episode
    tgl_keluar_col = 'tgl_keluar_episode' if 'tgl_keluar_episode' in df_last.columns else ('tgl_keluar' if 'tgl_keluar' in df_last.columns else None)
    # Filter: hanya episode yang udah keluar
    is_keluar = []
    for idx, row in df_last.iterrows():
        tgl = row[tgl_keluar_col] if tgl_keluar_col else None
        is_keluar.append(_is_keluar(row.get('status_pulang'), tgl))
    df_keluar = df_last[pd.Series(is_keluar, index=df_last.index)].copy()
    # Status counts: hanya yang keluar aja, biar konsisten sama GDR denominator
    if not df_keluar.empty and 'status_pulang' in df_keluar.columns:
        status_counts = df_keluar['status_pulang'].value_counts().reset_index()
        status_counts.columns = ['Status Pulang', 'Jumlah']
    else:
        status_counts = pd.DataFrame(columns=['Status Pulang', 'Jumlah'])
    total_keluar = len(df_keluar)
    if total_keluar > 0:
        status_keluar = df_keluar['status_pulang'].astype('string').fillna('')
        total_mati = int(status_keluar.str.contains('Meninggal', case=False, na=False).sum())
    else:
        total_mati = 0
    gdr = (total_mati / total_keluar * 1000) if total_keluar > 0 else 0
    # NDR: hanya kematian >= 48 jam (LOS episode >= 2)
    if total_keluar > 0 and total_mati > 0:
        mati_mask = df_keluar['status_pulang'].astype('string').str.contains('Meninggal', case=False, na=False)
        df_mati = df_keluar[mati_mask]
        mati_48 = 0
        for _, r in df_mati.iterrows():
            los = _los_episode_value(r)
            if los is not None and los >= 2:
                mati_48 += 1
        ndr = (mati_48 / total_keluar * 1000) if total_keluar > 0 else 0
    else:
        ndr = 0
    mortalitas_df = pd.DataFrame({
        'Indikator': ['Total Pasien Keluar', 'Total Pasien Meninggal', 'GDR (per 1000)', 'NDR (per 1000)'],
        'Nilai': [total_keluar, total_mati, round(gdr, 2), round(ndr, 2)],
    })
    return status_counts, mortalitas_df

def _baris_terakhir_per_pasien(df_long):
    # Backward compat: sekarang pakai per episode, bukan per no_rm
    return _baris_terakhir_per_episode(df_long)

def hitung_rl_31(df_long, periode_tahun=None, periode_bulan=None):
    """Susun ringkasan kegiatan pelayanan rawat inap RL 3.1. Kalau periode dikasih, hitung per periode. Kalau nggak, fallback ke seluruh data tapi Pindah di-exclude dari Keluar Hidup."""
    indicators = ['Pasien Awal Bulan', 'Pasien Masuk', 'Pasien Keluar Hidup', 'Pasien Keluar Mati', 'Pasien Pindah', 'Pasien Sisa']
    if df_long is None or df_long.empty:
        return pd.DataFrame({'Indikator': indicators, 'Jumlah': [0]*len(indicators)})
    df_last = _baris_terakhir_per_episode(df_long).copy()
    if df_last.empty:
        return pd.DataFrame({'Indikator': indicators, 'Jumlah': [0]*len(indicators)})
    # Normalisasi tanggal
    for col in ('tgl_masuk', 'tgl_keluar_episode', 'tgl_keluar'):
        if col in df_last.columns:
            df_last[col] = pd.to_datetime(df_last[col], errors='coerce')
    status = df_last['status_pulang'].astype('string').fillna('') if 'status_pulang' in df_last.columns else pd.Series('', index=df_last.index, dtype='string')
    meninggal = status.str.contains('Meninggal', case=False, na=False)
    pindah = status.str.contains(r'Pindah|Rujuk', case=False, na=False, regex=True)
    # Kalau periode nggak dikasih: fallback seluruh data, tapi Pindah di-exclude dari Keluar Hidup
    if periode_tahun is None or periode_bulan is None:
        # Keluar = status nggak kosong + nggak masih dirawat
        masih = status.str.strip().str.lower().isin(['', 'masih dirawat', 'masih di rawat', 'dirawat', 'nan', 'none'])
        keluar_mask = ~masih
        keluar_hidup = keluar_mask & ~meninggal & ~pindah
        jumlah = [0, int(len(df_last)), int(keluar_hidup.sum()), int((keluar_mask & meninggal).sum()), int((keluar_mask & pindah).sum()), 0]
        return pd.DataFrame({'Indikator': indicators, 'Jumlah': jumlah})
    # Kalau periode dikasih: hitung per periode
    try:
        awal = pd.Timestamp(year=int(periode_tahun), month=int(periode_bulan), day=1)
    except Exception:
        return pd.DataFrame({'Indikator': indicators, 'Jumlah': [0]*len(indicators)})
    if awal.month == 12:
        akhir = pd.Timestamp(year=awal.year+1, month=1, day=1)
    else:
        akhir = pd.Timestamp(year=awal.year, month=awal.month+1, day=1)
    tgl_masuk = df_last['tgl_masuk'] if 'tgl_masuk' in df_last.columns else pd.Series(pd.NaT, index=df_last.index)
    tgl_keluar = df_last['tgl_keluar_episode'] if 'tgl_keluar_episode' in df_last.columns else (df_last['tgl_keluar'] if 'tgl_keluar' in df_last.columns else pd.Series(pd.NaT, index=df_last.index))
    # Awal: masuk < awal periode DAN (keluar >= awal periode ATAU masih dirawat)
    awal_mask = (tgl_masuk < awal) & (tgl_keluar.isna() | (tgl_keluar >= awal))
    # Masuk: tgl_masuk di [awal, akhir)
    masuk_mask = (tgl_masuk >= awal) & (tgl_masuk < akhir)
    # Keluar di periode: tgl_keluar di [awal, akhir)
    keluar_periode = (tgl_keluar >= awal) & (tgl_keluar < akhir)
    keluar_hidup = keluar_periode & ~meninggal & ~pindah
    keluar_mati = keluar_periode & meninggal
    pindah_mask = keluar_periode & pindah & ~meninggal
    # Kalau pindah + meninggal dua-duanya (jarang), hitung sebagai meninggal aja, jangan dobel
    awal_n = int(awal_mask.sum())
    masuk_n = int(masuk_mask.sum())
    hidup_n = int(keluar_hidup.sum())
    mati_n = int(keluar_mati.sum())
    pindah_n = int(pindah_mask.sum())
    sisa_n = awal_n + masuk_n - hidup_n - mati_n - pindah_n
    if sisa_n < 0:
        sisa_n = 0
    jumlah = [awal_n, masuk_n, hidup_n, mati_n, pindah_n, sisa_n]
    return pd.DataFrame({'Indikator': indicators, 'Jumlah': jumlah})

def hitung_rl_4a(df_long, kamus_icd=None):
    """Rekap morbiditas rawat inap per diagnosa, per episode. kamus_icd: dict diagnosa_simrs -> kode_icd, buat auto-fill Kode ICD-10."""
    if df_long is None or df_long.empty:
        return pd.DataFrame(columns=['No', 'Diagnosa', 'L', 'P', 'Total', 'Kode ICD-10'])
    kolom_diag = None
    for col in ['diagnosa', 'diagnosis', 'penyakit', 'dx']:
        if col in df_long.columns:
            kolom_diag = col
            break
    if kolom_diag is None:
        return pd.DataFrame(columns=['No', 'Diagnosa', 'L', 'P', 'Total', 'Kode ICD-10'])
    df_last = _baris_terakhir_per_episode(df_long).copy()
    if df_last.empty:
        return pd.DataFrame(columns=['No', 'Diagnosa', 'L', 'P', 'Total', 'Kode ICD-10'])
    df_last[kolom_diag] = df_last[kolom_diag].fillna('').astype(str).str.strip()
    # Exclude diagnosa kosong / Tidak Ada Diagnosa dari RL 4a
    df_last = df_last[~df_last[kolom_diag].isin(['', 'nan', 'None', 'Tidak Ada Diagnosa', 'TIDAK ADA DIAGNOSA'])]
    if df_last.empty:
        return pd.DataFrame(columns=['No', 'Diagnosa', 'L', 'P', 'Total', 'Kode ICD-10'])
    if 'jenis_kelamin' not in df_last.columns:
        df_last['jenis_kelamin'] = 'Tidak Diketahui'
    df_last['L'] = (df_last['jenis_kelamin'] == 'L').astype(int)
    df_last['P'] = (df_last['jenis_kelamin'] == 'P').astype(int)
    rekap = df_last.groupby(kolom_diag).agg(L=('L', 'sum'), P=('P', 'sum'), Total=('L', 'size')).reset_index()
    # Total = L + P (jumlah episode), bukan nunique no_rm
    rekap['Total'] = rekap['L'] + rekap['P']
    rekap = rekap.sort_values(by='Total', ascending=False).reset_index(drop=True)
    rekap = rekap.rename(columns={kolom_diag: 'Diagnosa'})
    rekap.insert(0, 'No', range(1, len(rekap)+1))
    # Auto-fill Kode ICD-10 dari kamus kalau ada
    if kamus_icd and isinstance(kamus_icd, dict):
        rekap['Kode ICD-10'] = rekap['Diagnosa'].map(lambda d: str(kamus_icd.get(d, kamus_icd.get(str(d).strip(), '')) or ''))
    else:
        rekap['Kode ICD-10'] = ''
    return rekap

def hitung_rekap_penyakit(df_long):
    """Rekap penyakit terbanyak per episode (bukan per segmen). Return df dengan kolom diagnosa, jumlah_episode, jumlah_pasien_unik, persentase."""
    if df_long is None or df_long.empty:
        return pd.DataFrame(columns=['diagnosa', 'jumlah_episode', 'jumlah_pasien_unik', 'persentase'])
    df_last = _baris_terakhir_per_episode(df_long).copy()
    if df_last.empty or 'diagnosa' not in df_last.columns:
        return pd.DataFrame(columns=['diagnosa', 'jumlah_episode', 'jumlah_pasien_unik', 'persentase'])
    df_last['diagnosa'] = df_last['diagnosa'].astype(str).str.strip()
    df_last = df_last[~df_last['diagnosa'].isin(['', 'nan', 'None', 'Tidak Ada Diagnosa', 'TIDAK ADA DIAGNOSA'])]
    if df_last.empty:
        return pd.DataFrame(columns=['diagnosa', 'jumlah_episode', 'jumlah_pasien_unik', 'persentase'])
    rekap = df_last.groupby('diagnosa').agg(jumlah_episode=('diagnosa', 'size'), jumlah_pasien_unik=('no_rm', 'nunique') if 'no_rm' in df_last.columns else ('diagnosa', 'size')).reset_index()
    rekap = rekap.sort_values('jumlah_episode', ascending=False).reset_index(drop=True)
    total = rekap['jumlah_episode'].sum()
    rekap['persentase'] = (rekap['jumlah_episode'] / total * 100).round(2) if total > 0 else 0
    return rekap

def hitung_rekap_dpjp(df_long):
    """Rekap pasien per DPJP per episode (dokter di episode terakhir)."""
    if df_long is None or df_long.empty:
        return pd.DataFrame(columns=['Nama Dokter (DPJP)', 'Jumlah Pasien Unik'])
    df_last = _baris_terakhir_per_episode(df_long).copy()
    if df_last.empty or 'dokter' not in df_last.columns and 'dpjp' not in df_last.columns:
        return pd.DataFrame(columns=['Nama Dokter (DPJP)', 'Jumlah Pasien Unik'])
    col_dokter = 'dokter' if 'dokter' in df_last.columns else 'dpjp'
    df_last = df_last[df_last[col_dokter].notna() & (df_last[col_dokter].astype(str).str.strip() != '') & (df_last[col_dokter].astype(str).str.strip().str.lower() != 'nan')]
    if df_last.empty:
        return pd.DataFrame(columns=['Nama Dokter (DPJP)', 'Jumlah Pasien Unik'])
    rekap = df_last.groupby(col_dokter)['no_rm'].nunique().reset_index() if 'no_rm' in df_last.columns else df_last.groupby(col_dokter).size().reset_index(name='Jumlah Pasien Unik')
    rekap.columns = ['Nama Dokter (DPJP)', 'Jumlah Pasien Unik']
    rekap = rekap.sort_values(by='Jumlah Pasien Unik', ascending=False).reset_index(drop=True)
    return rekap
