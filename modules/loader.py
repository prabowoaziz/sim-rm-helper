import pandas as pd
import streamlit as st
import io

__all__ = ["get_sheet_names", "load_sheet_by_name"]


# Mapping positional untuk format laporan rawat inap 15 kolom (A-O).
MAPPING_15COL = {
    0: "no_registrasi",
    1: "nama_lengkap",
    2: "_drop_1",
    3: "no_rm",
    4: "_drop_2",
    5: "diagnosa",
    6: "dokter",
    7: "jaminan",
    8: "kelas_jaminan",
    9: "kamar",
    10: "_drop_3",
    11: "_drop_4",
    12: "tgl_masuk",
    13: "tgl_keluar",
    14: "keterangan",
}

# Mapping positional untuk format laporan rawat inap 14 kolom (A-N).
MAPPING_14COL = {
    0: "no_registrasi",
    1: "nama_lengkap",
    2: "_drop_1",
    3: "no_rm",
    4: "diagnosa",
    5: "dokter",
    6: "jaminan",
    7: "kamar",
    8: "tgl_masuk",
    9: "tgl_keluar",
    10: "keterangan",
    11: "_drop_2",
    12: "_drop_3",
    13: "_drop_4",
}


def _default_excel_column_names(column_count):
    """Return Excel-style labels (Kolom A, Kolom B, ..., Kolom AA)."""
    names = []
    for index in range(column_count):
        number = index + 1
        label = ""
        while number:
            number, remainder = divmod(number - 1, 26)
            label = chr(65 + remainder) + label
        names.append(f"Kolom {label}")
    return names


def _normalize_doctor_aliases(df):
    """Normalize doctor and diagnosis header aliases without duplicate doctor columns."""
    doctor_aliases = {
        "dpjp", "dokter", "dokter (dpjp)", "dpjp (dokter)", "nama dokter",
        "dokter penanggung jawab", "dpjp/dokter",
    }
    diagnosis_aliases = {"diagnosa", "diagnosis", "penyakit", "diag"}
    columns = []
    used = set()
    doctor_count = 0
    for column in df.columns:
        label = str(column).strip().casefold()
        if label in doctor_aliases:
            doctor_count += 1
            name = "dokter" if doctor_count == 1 else f"dokter_{doctor_count}"
            while name in used:
                doctor_count += 1
                name = f"dokter_{doctor_count}"
            used.add(name)
            columns.append(name)
        elif label in diagnosis_aliases:
            columns.append("diagnosa")
            used.add("diagnosa")
        else:
            columns.append(column)
            used.add(column)
    df.columns = columns
    return df

SHEET_GROUP_15COL_NO_HEADER = {
    "px masuk": "15col_no_header",
    "doble": "15col_no_header",
    "isolasi": "15col_no_header",
    "lt 2 anak": "15col_no_header",
    "icu isolasi": "15col_no_header",
    "picu": "15col_no_header",
    "px sisa": "15col_no_header",
}

SHEET_GROUP_14COL_PARTIAL_HEADER = {
    "lantai 2": "14col_partial_header",
    "lantai 3": "14col_partial_header",
}

SHEET_GROUP_15COL_PARTIAL_HEADER = {
    "hcu": "15col_partial_header",
    "nicu": "15col_partial_header",
    "icu": "15col_partial_header",
    "perina masuk": "15col_partial_header",
}
SHEET_GROUP_15COL_EXTRA = {
    'sakinah': '15col_partial_header',
    'sakinah 1': '15col_partial_header',
    'sakinah 2': '15col_partial_header',
    'firdaus': '15col_partial_header',
    'ar rahmah': '15col_partial_header',
    'safa': '15col_partial_header',
    'marwah': '15col_partial_header',
    'transit igd': '15col_partial_header',
    'perina level 2': '15col_partial_header',
}


def detect_sheet_group(sheet_name):
    """Return group identifier for known raw-report sheets, otherwise None."""
    nama = " ".join(str(sheet_name).casefold().split())
    groups = (
        SHEET_GROUP_15COL_PARTIAL_HEADER,
        SHEET_GROUP_15COL_EXTRA,
        SHEET_GROUP_14COL_PARTIAL_HEADER,
        SHEET_GROUP_15COL_NO_HEADER,
    )
    matches = [
        (len(fragment), group_name)
        for group in groups
        for fragment, group_name in group.items()
        if fragment in nama
    ]
    return max(matches, default=(0, None))[1]


@st.cache_data(show_spinner=False)
def load_sheet_by_name(file_bytes, file_name, sheet_name):
    """Load and normalize one sheet from immutable file bytes; return ``(df, error)``."""
    try:
        source = io.BytesIO(file_bytes)
        is_csv = str(file_name).casefold().endswith('.csv')
        header_preserved = False
        if is_csv:
            df = pd.read_csv(source)
            mapping = None
        else:
            group = detect_sheet_group(sheet_name)
            df = pd.read_excel(source, sheet_name=sheet_name, header=None)
            if group in ('15col_no_header', '15col_partial_header'):
                mapping = MAPPING_15COL
            elif group == '14col_partial_header':
                mapping = MAPPING_14COL
            else:
                mapping = None
                df_header = pd.read_excel(
                    io.BytesIO(file_bytes), sheet_name=sheet_name, header=0
                )
                normalized_headers = [
                    str(column).strip().casefold().replace(" ", "_").replace(".", "").replace("-", "_")
                    for column in df_header.columns
                ]
                has_recognized_header = any(
                    any(marker in column for marker in ("dokter", "dpjp", "diagnosa", "diagnosis", "nama", "no_rm"))
                    for column in normalized_headers
                )
                if has_recognized_header:
                    df = df_header
                    header_preserved = True
                elif len(df.columns) == 15:
                    mapping = MAPPING_15COL
                elif len(df.columns) == 14:
                    mapping = MAPPING_14COL

        if mapping is not None:
            df = df.rename(columns=mapping)
        elif not is_csv and not header_preserved:
            df.columns = _default_excel_column_names(len(df.columns))

        df = _normalize_doctor_aliases(df)

        if {"nama_lengkap", "no_rm"}.issubset(df.columns):
            df[["nama_lengkap", "no_rm"]] = df[["nama_lengkap", "no_rm"]].replace(
                r"^\s*$", pd.NA, regex=True
            )
        return df, None
    except Exception as e:
        return None, str(e)

@st.cache_data(show_spinner=False)
def get_sheet_names(file_bytes, file_name):
    if file_name.endswith(('.xlsx', '.xls')):
        try:
            # Bungkus bytes ke BytesIO
            file_obj = io.BytesIO(file_bytes)
            xls = pd.ExcelFile(file_obj)
            return xls.sheet_names
        except Exception as e:
            return [f"ERROR: {str(e)}"]
    return ["Sheet1"]

@st.cache_data(show_spinner=False)
def load_data(file_bytes, file_name, sheet_name=None):
    """Compatibility wrapper; keep all file parsing in the cached sheet loader."""
    if sheet_name is None:
        sheets = get_sheet_names(file_bytes, file_name)
        if not sheets or sheets[0].startswith('ERROR:'):
            return None, sheets[0] if sheets else 'Sheet tidak ditemukan.'
        sheet_name = sheets[0]
    return load_sheet_by_name(file_bytes, file_name, sheet_name)
