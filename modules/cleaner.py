import pandas as pd
import re
from datetime import datetime


def guess_column_types(df):
    """Guess common raw-report columns from their contents."""
    guesses = {
        "nama": None,
        "no_rm": None,
        "kamar": None,
        "tgl_masuk": None,
        "tgl_keluar": None,
        "penjamin": None,
    }
    if df is None or df.empty:
        return guesses

    def values_for(column):
        values = df[column].dropna()
        return values[values.astype(str).str.strip().ne("")]

    def ratio(column, predicate):
        values = values_for(column)
        if values.empty:
            return 0.0
        return sum(bool(predicate(value)) for value in values) / len(values)

    def normalized_number(value):
        s = str(value).strip().replace(",", "")
        if re.fullmatch(r"\d+\.0+", s):
            s = s.split(".", 1)[0]
        return s

    def has_date(value):
        if isinstance(value, (pd.Timestamp, datetime)):
            return True
        return bool(re.match(r"^\d{4}-\d{2}-\d{2}(?:\b|T)", str(value).strip()))

    def choose(scored, keyword_groups=()):
        if not scored:
            return None
        best_score = max(score for _, score in scored)
        if best_score <= 0:
            return None
        tied = [column for column, score in scored if score == best_score]
        for keywords in keyword_groups:
            for column in tied:
                if any(word in str(column).casefold() for word in keywords):
                    return column
        return tied[0]

    no_rm_scores = [
        (column, ratio(column, lambda v: bool(re.fullmatch(r"\d{5,8}", normalized_number(v)))))
        for column in df.columns
    ]
    guesses["no_rm"] = choose(
        [(column, score) for column, score in no_rm_scores if score > 0.5],
        (("rm", "rekam", "norm"),),
    )
    guesses["nama"] = choose(
        [(column, ratio(column, lambda v: bool(re.search(r"\(\s*\d+\s*(?:Th|Bl|Hr)\b", str(v), re.I))))
         for column in df.columns],
        (("nama", "pasien", "lengkap"),),
    )
    room_words = re.compile(
        r"\b(?:HCU|ICU|NICU|PICU|KEN\w*|ASTER|CEMPAKA|MELATI|MAWAR|ANGGREK|ISOLASI|PERINA)\b",
        re.I,
    )
    guesses["kamar"] = choose(
        [(column, ratio(column, lambda v: "-" in str(v) or bool(room_words.search(str(v)))))
         for column in df.columns],
        (("kamar", "ruang", "bed"),),
    )
    payer_words = re.compile(r"BPJS|UMUM|ASURANSI", re.I)
    guesses["penjamin"] = choose(
        [(column, ratio(column, lambda v: bool(payer_words.search(str(v)))))
         for column in df.columns],
        (("jaminan", "penjamin", "asuransi"),),
    )

    date_scored = [
        (column, ratio(column, has_date))
        for column in df.columns
    ]
    date_scored = [(column, score) for column, score in date_scored if score > 0]
    masuk_named = [(column, score) for column, score in date_scored
                   if any(word in str(column).casefold() for word in ("masuk", "admit", "awal"))]
    keluar_named = [(column, score) for column, score in date_scored
                    if any(word in str(column).casefold() for word in ("keluar", "pulang", "akhir"))]
    sorted_dates = sorted(date_scored, key=lambda item: item[1], reverse=True)
    guesses["tgl_masuk"] = choose(masuk_named) if masuk_named else (sorted_dates[0][0] if sorted_dates else None)
    guesses["tgl_keluar"] = choose(keluar_named) if keluar_named else next(
        (column for column, _ in sorted_dates if column != guesses["tgl_masuk"]),
        None,
    )
    return guesses


def clean_nama(val):
    if pd.isna(val): return None
    s = str(val).strip()
    s = re.sub(r'\s*\(\s*null\s*\)\s*$', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*\([^)]*\)\s*$', '', s) # buang (...) di akhir nama
    if not s.strip(): return None
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
    s = re.sub(r'\s*\(\s*null\s*\)\s*$', '', s, flags=re.IGNORECASE).strip()
    jk_only = re.fullmatch(r'([LPMF])', s, re.IGNORECASE)
    if jk_only:
        return None, jk_only.group(1).upper(), None, None
    pattern = re.compile(
        r'^(?P<nama>.*?)\s*(?:(?:\|\s*|,\s*)'
        r'(?P<kode>AN|TN|NY|NN|BY)\s*)?'
        r'\(\s*(?P<umur>\d+)\s*(?P<satuan>Th|Bl|Hr|null)?\s*\)\s*$',
        re.IGNORECASE,
    )
    match = pattern.match(s)
    if not match:
        kode_only = re.fullmatch(
            r'\s*(AN|TN|NY|NN|BY)\s*\(\s*(\d+)\s*(Th|Bl|Hr|null)?\s*\)\s*',
            s,
            re.IGNORECASE,
        )
        if kode_only:
            kode = kode_only.group(1).upper()
            jk = {'AN': 'L', 'TN': 'L', 'NY': 'P', 'NN': 'P', 'BY': None}.get(kode)
            return None, jk, int(kode_only.group(2)), (kode_only.group(3) or 'Th').capitalize()
        return clean_nama(s), None, None, None

    nama = match.group('nama').strip().rstrip('|, ').strip()
    kode = (match.group('kode') or '').upper()
    if not kode and nama.upper() in {'AN', 'TN', 'NY', 'NN', 'BY'}:
        kode, nama = nama.upper(), ''
    jk = {'AN': 'L', 'TN': 'L', 'NY': 'P', 'NN': 'P', 'BY': None}.get(kode)
    if not kode and nama.upper() in {'L', 'P', 'M', 'F'}:
        jk, nama = nama.upper(), ''
    satuan = match.group('satuan')
    if not satuan or satuan.casefold() == 'null':
        satuan = 'Th'
    return nama or None, jk, int(match.group('umur')), satuan.capitalize()


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
    parts = re.split(r'\s+', s, maxsplit=1)
    kode = parts[0]
    ruang = parts[1] if len(parts) > 1 else None
    tokens = kode.split('-')
    kelas = tokens[1] if len(tokens) > 1 else None
    return kode, ruang, kelas
