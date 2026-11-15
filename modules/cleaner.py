import pandas as pd
import re
from datetime import datetime


def guess_column_types(df):
    """Guess common raw-report columns from their contents."""
    guesses = {
        "nama": None,
        "jk_umur": None,
        "no_rm": None,
        "kamar": None,
        "tgl_masuk": None,
        "tgl_keluar": None,
        "penjamin": None,
        "kelas_jaminan": None,
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

    candidate_columns = [
        column for column in df.columns
        if not str(column).casefold().startswith(("_drop_", "unnamed"))
    ]

    no_rm_scores = [
        (column, ratio(column, lambda v: bool(re.fullmatch(r"\d{5,8}", normalized_number(v)))))
        for column in candidate_columns
    ]
    guesses["no_rm"] = choose(
        [(column, score) for column, score in no_rm_scores if score > 0.5],
        (("rm", "rekam", "norm"),),
    )
    nama_headers = [
        column for column in candidate_columns
        if "nama_lengkap" in str(column).casefold()
    ]
    if nama_headers and not values_for(nama_headers[0]).empty:
        guesses["nama"] = nama_headers[0]
    else:
        guesses["nama"] = choose(
            [(column, ratio(column, lambda v: bool(re.search(r"\(\s*\d+\s*(?:Th|Bl|Hr)\b", str(v), re.I))))
             for column in candidate_columns],
            (("nama", "pasien", "lengkap"),),
        )

    pola_umur = re.compile(r"\d+\s*(?:Th|Bl|Hr)\b", re.I)
    pola_jk_umur = re.compile(
        r"^\s*(?:AN|TN|NY|NN|BY)\b.*\d+\s*(?:Th|Bl|Hr)\b",
        re.I,
    )
    jk_umur_scores = []
    for column in df.columns:
        nilai_khusus = ratio(column, lambda value: bool(pola_jk_umur.search(str(value))))
        nilai_umur = ratio(column, lambda value: bool(pola_umur.search(str(value))))
        # A matching gender/age token marks this as a dedicated demographic column.
        score = 2 + nilai_khusus if nilai_khusus > 0 else nilai_umur
        jk_umur_scores.append((column, score))
    guesses["jk_umur"] = choose(
        jk_umur_scores,
        (("jk", "umur", "usia", "kelamin"),),
    )

    room_words = re.compile(
        r"\b(?:HCU|ICU|NICU|PICU|KEN\w*|ASTER|CEMPAKA|MELATI|MAWAR|ANGGREK|ISOLASI|PERINA)\b",
        re.I,
    )
    guesses["kamar"] = choose(
        [(column, ratio(column, lambda v: "-" in str(v) or bool(room_words.search(str(v)))))
         for column in candidate_columns],
        (("kamar", "ruang", "bed"),),
    )
    payer_words = re.compile(r"BPJS|UMUM|ASURANSI", re.I)
    guesses["penjamin"] = choose(
        [(column, ratio(column, lambda v: bool(payer_words.search(str(v)))))
         for column in candidate_columns],
        (("jaminan", "penjamin", "asuransi"),),
    )

    def is_class_value(value):
        s = normalized_number(value).upper()
        if s in {"1.0", "2.0", "3.0"}:
            s = s[0]
        return s in {"1", "2", "3", "VIP"}

    guesses["kelas_jaminan"] = choose(
        [(column, ratio(column, is_class_value)) for column in candidate_columns],
        (("kelas_jaminan", "kelas_jam", "kelas"),),
    )

    date_scored = [
        (column, ratio(column, has_date))
        for column in candidate_columns
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
    s = re.sub(r'\s*\(\d+\s*(Th|Bl|Hr)\)\s*$', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*(?:,|\|)\s*(AN|TN|NY|NN|BY)\s*$', '', s, flags=re.IGNORECASE)
    if not s.strip(): return None
    s = s.replace('|', '').strip()
    s = re.sub(r'\s+', ' ', s)
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


def guess_jk_from_nama(nama):
    if nama is None or pd.isna(nama): return None
    if not str(nama).strip(): return None
    s = str(nama).upper()
    if any(w in s for w in ["NYONYA", "NY.", " NY ", "NN", "NONA", "HAJAH", "HJ.", "IBU", "PUAN", "SITI"]): return 'P'
    if any(w in s for w in ["TUAN", "TN.", " TN ", "BAPAK", "BPK", "HAJI", "HJ", "OM"]): return 'L'
    return None


def split_jk_umur(val):
    if pd.isna(val): return None, None
    s = re.sub(r'\s*\(\s*null\s*\)\s*$', '', str(val).strip(), flags=re.IGNORECASE)

    m_umur = re.search(r'\((\d+)\s*(Th|Bl|Hr|null)?\)', s, flags=re.IGNORECASE)
    umur_tahun = None
    if m_umur:
        angka = int(m_umur.group(1))
        satuan = (m_umur.group(2) or 'Th').lower()
        if satuan == 'bl':
            umur_tahun = round(angka / 12, 2)
        elif satuan == 'hr':
            umur_tahun = round(angka / 365, 2)
        else:
            umur_tahun = float(angka)

    jk = None
    if re.search(r'\b(AN|TN)\b', s, flags=re.IGNORECASE):
        jk = 'L'
    elif re.search(r'\b(NY|NN)\b', s, flags=re.IGNORECASE):
        jk = 'P'

    return jk, umur_tahun


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
