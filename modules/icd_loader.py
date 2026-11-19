from io import BytesIO

import pandas as pd


def upload_icd_to_supabase(file_bytes, supabase_client):
    """Read an ICD-10 workbook and upsert its rows to master_icd in batches."""
    df = pd.read_excel(BytesIO(file_bytes), header=0)
    kolom_map = {str(column).strip().upper(): column for column in df.columns}
    kolom_wajib = ["CODE", "DISPLAY", "VERSION"]
    hilang = [column for column in kolom_wajib if column not in kolom_map]
    if hilang:
        raise ValueError(f"Kolom wajib tidak ditemukan: {', '.join(hilang)}")

    data = df[[kolom_map[column] for column in kolom_wajib]].copy()
    data.columns = ["code", "display", "version"]
    data["code"] = data["code"].map(lambda value: None if pd.isna(value) else str(value).strip())
    data["display"] = data["display"].map(lambda value: None if pd.isna(value) else str(value).strip())
    data["version"] = data["version"].map(lambda value: None if pd.isna(value) else str(value).strip())
    data = data[data["code"].notna() & data["code"].ne("")]
    data = data.drop_duplicates(subset=["code"], keep="last")

    records = data.to_dict(orient="records")
    total = 0
    for start in range(0, len(records), 500):
        batch = records[start:start + 500]
        supabase_client.table("master_icd").upsert(
            batch,
            on_conflict="code",
        ).execute()
        total += len(batch)
    return total


def load_kamus_icd(supabase_client):
    """Load kamus diagnosa_simrs -> kode_icd dari tabel kamus_icd. Return dict. Kalau tabel kosong / error, return {}."""
    try:
        res = supabase_client.table('kamus_icd').select('diagnosa_simrs, kode_icd').execute()
        rows = res.data or []
        kamus = {}
        for r in rows:
            diag = (r.get('diagnosa_simrs') or '').strip()
            kode = (r.get('kode_icd') or '').strip()
            if diag and kode:
                kamus[diag] = kode
        return kamus
    except Exception:
        return {}


def save_kamus_icd(supabase_client, diagnosa, kode):
    """Upsert 1 mapping diagnosa_simrs -> kode_icd ke tabel kamus_icd."""
    return supabase_client.table('kamus_icd').upsert(
        {'diagnosa_simrs': str(diagnosa).strip(), 'kode_icd': str(kode).strip()},
        on_conflict='diagnosa_simrs',
    ).execute()
