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


def split_jk_umur(val):
    if pd.isna(val): return None, None
    s = str(val).strip()
    m = re.search(r'\((\d+)\s*(Th|Bl|Hr)?\)', s, re.IGNORECASE)
    if not m:
        jk_only = re.fullmatch(r'\s*([LPFM])\s*', s, re.IGNORECASE)
        return (jk_only.group(1).upper() if jk_only else None), None
    prefix = s[:m.start()].strip()
    jk_match = re.fullmatch(r'([LPFM])', prefix, re.IGNORECASE)
    jk = jk_match.group(1).upper() if jk_match else None
    angka = int(m.group(1))
    satuan = (m.group(2) or 'Th').lower()
    if satuan == 'bl': umur = round(angka / 12, 2)
    elif satuan == 'hr': umur = round(angka / 365, 2)
    else: umur = float(angka)
    return jk, umur


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
