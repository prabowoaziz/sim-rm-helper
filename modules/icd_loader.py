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
