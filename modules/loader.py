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
    6: "dpjp",
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
    5: "dpjp",
    6: "jaminan",
    7: "kamar",
    8: "tgl_masuk",
    9: "tgl_keluar",
    10: "keterangan",
    11: "_drop_2",
    12: "_drop_3",
    13: "_drop_4",
}

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


def detect_sheet_group(sheet_name):
    """Return group identifier for known raw-report sheets, otherwise None."""
    nama = " ".join(str(sheet_name).casefold().split())
    groups = (
        SHEET_GROUP_15COL_PARTIAL_HEADER,
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


def load_sheet_by_name(file, sheet_name):
    """Load and normalize a known inpatient sheet; return ``(df, error)``."""
    try:
        file_name = getattr(file, "name", "")
        source = file
        if isinstance(file, (bytes, bytearray)):
            source = io.BytesIO(file)
        elif hasattr(file, "seek"):
            file.seek(0)

        if str(file_name).casefold().endswith(".csv"):
            df = pd.read_csv(source)
            mapping = None
        else:
            group = detect_sheet_group(sheet_name)
            if group == "15col_no_header":
                df = pd.read_excel(source, sheet_name=sheet_name, header=None)
                mapping = MAPPING_15COL
            elif group == "14col_partial_header":
                df = pd.read_excel(source, sheet_name=sheet_name, header=None, skiprows=1)
                mapping = MAPPING_14COL
            elif group == "15col_partial_header":
                df = pd.read_excel(source, sheet_name=sheet_name, header=None, skiprows=1)
                mapping = MAPPING_15COL
            else:
                df = pd.read_excel(source, sheet_name=sheet_name, header=0)
                mapping = None

        if mapping is not None:
            df = df.rename(columns=mapping)

        drop_cols = [
            column for column in df.columns
            if str(column).startswith("_drop_") or str(column).casefold().startswith("unnamed")
        ]
        if drop_cols:
            df = df.drop(columns=drop_cols)

        if {"nama_lengkap", "no_rm"}.issubset(df.columns):
            df[["nama_lengkap", "no_rm"]] = df[["nama_lengkap", "no_rm"]].replace(
                r"^\s*$", pd.NA, regex=True
            )
            df = df.dropna(subset=["nama_lengkap", "no_rm"])
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
    try:
        # Bungkus bytes ke BytesIO
        file_obj = io.BytesIO(file_bytes)
        
        if file_name.endswith('.csv'):
            df = pd.read_csv(file_obj)
        else:
            df = pd.read_excel(file_obj, sheet_name=sheet_name, header=0)
        return df, None
    except Exception as e:
        return None, str(e)
