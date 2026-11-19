import pandas as pd
import re
from datetime import datetime

RE_DECIMAL_ZERO = re.compile(r"\d+\.0+")
RE_NO_RM = re.compile(r"\d{5,8}")
RE_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:\b|T)")
RE_NAME_AGE = re.compile(r"\(\s*\d+\s*(?:Th|Bl|Hr)\b", re.I)
RE_AGE = re.compile(r"\d+\s*(?:Th|Bl|Hr)\b", re.I)
RE_JK_AGE = re.compile(r"^\s*(?:AN|TN|NY|NN|BY)\b.*\d+\s*(?:Th|Bl|Hr)\b", re.I)
RE_ROOM_WORDS = re.compile(r"\b(?:HCU|ICU|NICU|PICU|KEN\w*|ASTER|CEMPAKA|MELATI|MAWAR|ANGGREK|ISOLASI|PERINA)\b", re.I)
RE_PAYER_WORDS = re.compile(r"BPJS|UMUM|ASURANSI", re.I)
RE_NULL_PAREN = re.compile(r"\s*\(\s*null\s*\)\s*$", re.I)
RE_AGE_SUFFIX = re.compile(r"\s*\(\d+\s*(Th|Bl|Hr)\)\s*$", re.I)
RE_NAME_SUFFIX = re.compile(r"\s*(?:,|\|)\s*(AN|TN|NY|NN|BY)\s*$", re.I)
RE_WHITESPACE = re.compile(r"\s+")
RE_AGE_PAREN = re.compile(r"\((\d+)\s*(Th|Bl|Hr|null)?\)", re.I)
RE_JK_MALE = re.compile(r"\b(AN|TN)\b", re.I)
RE_JK_FEMALE = re.compile(r"\b(NY|NN)\b", re.I)
RE_SPLIT_SPACE = re.compile(r"\s+")


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
    df_sample = df.head(200) if len(df) > 200 else df

    def values_for(column):
        values = df_sample[column].dropna()
        return values[values.astype(str).str.strip().ne("")]

    def ratio(column, predicate):
        values = values_for(column)
        if values.empty:
            return 0.0
        return sum(bool(predicate(value)) for value in values) / len(values)

    def normalized_number(value):
        s = str(value).strip().replace(",", "")
        if RE_DECIMAL_ZERO.fullmatch(s):
            s = s.split(".", 1)[0]
        return s

    def has_date(value):
        if isinstance(value, (pd.Timestamp, datetime)):
            return True
        return bool(RE_ISO_DATE.match(str(value).strip()))

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
        (column, ratio(column, lambda v: bool(RE_NO_RM.fullmatch(normalized_number(v)))))
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
            [(column, ratio(column, lambda v: bool(RE_NAME_AGE.search(str(v)))))
             for column in candidate_columns],
            (("nama", "pasien", "lengkap"),),
        )

    jk_umur_scores = []
    for column in df.columns:
        nilai_khusus = ratio(column, lambda value: bool(RE_JK_AGE.search(str(value))))
        nilai_umur = ratio(column, lambda value: bool(RE_AGE.search(str(value))))
        # A matching gender/age token marks this as a dedicated demographic column.
        score = 2 + nilai_khusus if nilai_khusus > 0 else nilai_umur
        jk_umur_scores.append((column, score))
    guesses["jk_umur"] = choose(
        jk_umur_scores,
        (("jk", "umur", "usia", "kelamin"),),
    )

    guesses["kamar"] = choose(
        [(column, ratio(column, lambda v: "-" in str(v) or bool(RE_ROOM_WORDS.search(str(v)))))
         for column in candidate_columns],
        (("kamar", "ruang", "bed"),),
    )
    guesses["penjamin"] = choose(
        [(column, ratio(column, lambda v: bool(RE_PAYER_WORDS.search(str(v)))))
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
    s = RE_NULL_PAREN.sub('', s)
    s = RE_AGE_SUFFIX.sub('', s)
    s = RE_NAME_SUFFIX.sub('', s)
    if not s.strip(): return None
    s = s.replace('|', '').strip()
    s = RE_WHITESPACE.sub(' ', s)
    return s.upper().strip()


def clean_kelas(val):
    if pd.isna(val): return "Tidak Diketahui"
    s = str(val).strip().upper()
    if s in ['VIP', '1', '2', '3']:
        return s
    return "Tidak Diketahui"


def cek_kelas_titipan(row, master_kelas):
    kelas_jaminan = str(row['kelas_jaminan']).strip().upper()
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
    s = RE_NULL_PAREN.sub('', str(val).strip())

    m_umur = RE_AGE_PAREN.search(s)
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
    if RE_JK_MALE.search(s):
        jk = 'L'
    elif RE_JK_FEMALE.search(s):
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
    parts = RE_SPLIT_SPACE.split(s, maxsplit=1)
    kode = parts[0]
    ruang = parts[1] if len(parts) > 1 else None
    tokens = kode.split('-')
    kelas = tokens[1] if len(tokens) > 1 else None
    return kode, ruang, kelas


def clean_dataframe_vectorized(df_mentah, mapping_dict, master_kelas,
                               dict_prev=None, dict_next=None):
    """Bersihkan kolom terpilih; tanggal dikonversi sekali per kolom."""
    dict_prev = dict_prev or {}
    dict_next = dict_next or {}
    empty_selection = "— Pilih kolom —"

    def selected_series(key, default=None):
        column = mapping_dict.get(key, empty_selection)
        if column != empty_selection and column in df_mentah.columns:
            return df_mentah[column]
        return pd.Series(default, index=df_mentah.index)

    def selected_date(key, fallback):
        column = mapping_dict.get(key, empty_selection)
        if column != empty_selection and column in df_mentah.columns:
            values = pd.to_datetime(df_mentah[column], errors='coerce')
        else:
            values = pd.Series(pd.NaT, index=df_mentah.index)
        if fallback:
            rm_key = selected_series('map_rm').map(
                lambda value: str(value).replace('.0', '').strip()
                if mapping_dict.get('map_rm') != empty_selection else None
            )
            values = values.fillna(rm_key.map(fallback))
        return values

    raw_nama = selected_series('map_nama', '')
    raw_jk = selected_series('map_jk', '')
    nama = raw_nama.apply(clean_nama)
    demographics = pd.Series(
        [f"{name} {jk}" for name, jk in zip(raw_nama, raw_jk)], index=df_mentah.index
    ).apply(split_jk_umur)
    jenis_kelamin = pd.Series([result[0] for result in demographics], index=df_mentah.index)
    umur_tahun = pd.Series([result[1] for result in demographics], index=df_mentah.index)
    kamar_raw = selected_series('map_kamar', '')
    parsed_rooms = kamar_raw.apply(parse_kamar)
    kode_kamar = parsed_rooms.map(lambda result: result[0])
    ruang = parsed_rooms.map(lambda result: result[1])
    kelas_dari_kamar = ruang.map(lambda room: master_kelas.get(room, 'Tidak Diketahui'))

    raw_rm = selected_series('map_rm').map(
        lambda value: str(value).replace('.0', '').strip()
        if mapping_dict.get('map_rm') != empty_selection else None
    )
    no_rm = raw_rm.map(lambda value: None if value in (None, 'None', 'nan') else value)
    tanggal_masuk = selected_date('map_masuk', dict_prev)
    tanggal_keluar = selected_date('map_keluar', dict_next)
    raw_kelas = selected_series('map_kelas')
    kelas_jaminan = raw_kelas.map(clean_kelas)
    status = selected_series('map_status')
    diagnosa = selected_series('map_diag', 'Tidak Ada Diagnosa').map(
        lambda value: str(value).strip()
    )
    dokter = selected_series('map_dokter')

    result = pd.DataFrame({
        'no_rm': no_rm,
        'nama': nama,
        'jenis_kelamin': jenis_kelamin,
        'umur_tahun': umur_tahun,
        'kode_kamar': kode_kamar,
        'ruang': ruang,
        'kelas': kelas_dari_kamar,
        'tgl_masuk': tanggal_masuk,
        'tgl_keluar': tanggal_keluar,
        'status_pulang': status,
        'kelas_jaminan': kelas_jaminan,
        'diagnosa': diagnosa,
        'dokter': dokter,
    }, index=df_mentah.index)
    result = result.reset_index(drop=True)
    return result[result['nama'].notna()].copy()
