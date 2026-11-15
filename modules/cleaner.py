import pandas as pd
import re
from datetime import datetime


def clean_nama(val):
    if pd.isna(val): return None
    s = str(val).strip()
    s = re.sub(r'\s*\([^)]*\)\s*$', '', s) # buang (...) di akhir
    return s.upper().strip()


def clean_kelas(val):
    if pd.isna(val): return "Tidak Diketahui"
    s = str(val).strip().upper()
    if s in ['VIP', '1', '2', '3']:
        return s
    return "Tidak Diketahui"


def cek_kelas_titipan(row, master_kelas):
    kelas_jaminan = str(row['kelas_jam']).strip().upper()
    kelas_kamar = master_kelas.get(row['ruang'])
    return kelas_jaminan != str(kelas_kamar).strip().upper() if kelas_kamar is not None else True


def _parse_nama_lengkap(val):
    """Parse nama rawat, optional kode gender, umur, dan satuan dari satu string."""
    if pd.isna(val):
        return None, None, None, None

    s = str(val).strip()
    jk_only = re.fullmatch(r'([LPMF])', s, re.IGNORECASE)
    if jk_only:
        return None, jk_only.group(1).upper(), None, None
    pattern = re.compile(
        r'^(?P<nama>.*?)\s*(?:(?:\|\s*|,\s*)'
        r'(?P<kode>AN|TN|NY|NN|BY)\s*)?'
        r'\(\s*(?P<umur>\d+)\s*(?P<satuan>Th|Bl|Hr)\s*\)\s*$',
        re.IGNORECASE,
    )
    match = pattern.match(s)
    if not match:
        kode_only = re.fullmatch(
            r'\s*(AN|TN|NY|NN|BY)\s*\(\s*(\d+)\s*(Th|Bl|Hr)\s*\)\s*',
            s,
            re.IGNORECASE,
        )
        if kode_only:
            kode = kode_only.group(1).upper()
            jk = {'AN': 'L', 'TN': 'L', 'NY': 'P', 'NN': 'P', 'BY': None}.get(kode)
            return None, jk, int(kode_only.group(2)), kode_only.group(3).capitalize()
        return clean_nama(s), None, None, None

    nama = match.group('nama').strip().rstrip('|, ').strip()
    kode = (match.group('kode') or '').upper()
    if not kode and nama.upper() in {'AN', 'TN', 'NY', 'NN', 'BY'}:
        kode, nama = nama.upper(), ''
    jk = {'AN': 'L', 'TN': 'L', 'NY': 'P', 'NN': 'P', 'BY': None}.get(kode)
    if not kode and nama.upper() in {'L', 'P', 'M', 'F'}:
        jk, nama = nama.upper(), ''
    return nama or None, jk, int(match.group('umur')), match.group('satuan').capitalize()


def split_jk_umur(val):
    nama, jk, umur, satuan = _parse_nama_lengkap(val)
    if umur is None:
        return nama, jk, None
    if satuan == 'Bl':
        umur_tahun = round(umur / 12, 2)
    elif satuan == 'Hr':
        umur_tahun = round(umur / 365, 2)
    else:
        umur_tahun = float(umur)
    return nama, jk, umur_tahun


def kategori_umur(umur):
    if umur is None or pd.isna(umur): return None
    if umur < 0.08: return 'Neonatus'
    if umur < 1: return 'Bayi'
    if umur < 5: return 'Balita'
    if umur < 18: return 'Anak'
    if umur < 60: return 'Dewasa'
    return 'Lansia'


def parse_kamar(val):
    if pd.isna(val): return None, None, None
    s = str(val).strip()
    parts = s.split(' ', 1)
    kode = parts[0]
    ruang = parts[1] if len(parts) > 1 else None
    tokens = kode.split('-')
    kelas = tokens[1] if len(tokens) > 1 else None
    return kode, ruang, kelas
