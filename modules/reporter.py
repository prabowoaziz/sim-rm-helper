import pandas as pd


def hitung_statistik_dan_mortalitas(df_long):
    """Hitung distribusi status akhir pasien dan angka mortalitas."""
    if df_long.empty:
        return pd.DataFrame(), pd.DataFrame()

    df_last = df_long.sort_values("urutan").groupby("no_rm").tail(1)
    if "status_pulang" in df_last.columns:
        status_counts = df_last["status_pulang"].value_counts().reset_index()
        status_counts.columns = ["Status Pulang", "Jumlah"]
        status = df_last["status_pulang"].astype("string")
        total_mati = int(status.str.contains("Meninggal", case=False, na=False).sum())
    else:
        status_counts = pd.DataFrame(columns=["Status Pulang", "Jumlah"])
        total_mati = 0

    total_keluar = len(df_last)
    gdr = (total_mati / total_keluar * 1000) if total_keluar > 0 else 0
    ndr = gdr

    mortalitas_df = pd.DataFrame({
        "Indikator": [
            "Total Pasien Keluar",
            "Total Pasien Meninggal",
            "GDR (per 1000)",
            "NDR (per 1000)",
        ],
        "Nilai": [total_keluar, total_mati, round(gdr, 2), round(ndr, 2)],
    })

    return status_counts, mortalitas_df


def _baris_terakhir_per_pasien(df_long):
    if df_long.empty or "no_rm" not in df_long.columns:
        return pd.DataFrame()
    if "urutan" in df_long.columns:
        return df_long.sort_values("urutan").groupby("no_rm", dropna=False).tail(1)
    return df_long.groupby("no_rm", dropna=False).tail(1)


def hitung_rl_31(df_long):
    """Susun ringkasan kegiatan pelayanan rawat inap RL 3.1."""
    indicators = [
        "Pasien Awal Bulan",
        "Pasien Masuk",
        "Pasien Keluar Hidup",
        "Pasien Keluar Mati",
        "Pasien Pindah",
        "Pasien Sisa",
    ]
    if df_long.empty:
        return pd.DataFrame({"Indikator": indicators, "Jumlah": [0] * len(indicators)})

    df_last = _baris_terakhir_per_pasien(df_long)
    status = (
        df_last["status_pulang"].astype("string").fillna("")
        if "status_pulang" in df_last.columns
        else pd.Series("", index=df_last.index, dtype="string")
    )
    meninggal = status.str.contains("Meninggal", case=False, na=False)
    pindah = status.str.contains(r"Pindah|Rujuk", case=False, na=False, regex=True)
    keluar_hidup = status.str.strip().ne("") & ~meninggal
    jumlah = [
        0,
        int(df_long["no_rm"].nunique()) if "no_rm" in df_long.columns else len(df_last),
        int(keluar_hidup.sum()),
        int(meninggal.sum()),
        int(pindah.sum()),
        0,
    ]
    return pd.DataFrame({"Indikator": indicators, "Jumlah": jumlah})


def hitung_rl_4a(df_long):
    """Hitung sepuluh besar morbiditas rawat inap menurut diagnosa dan jenis kelamin."""
    columns = ["No", "Diagnosa", "L", "P", "Total"]
    df_last = _baris_terakhir_per_pasien(df_long)
    if df_last.empty:
        return pd.DataFrame(columns=columns)

    if "diagnosa" in df_last.columns:
        diagnosis = df_last["diagnosa"].astype("string").str.strip()
        diagnosis = diagnosis.mask(diagnosis.isna() | diagnosis.eq(""), "Diagnosa Tidak Terisi")
    else:
        diagnosis = pd.Series("Diagnosa Tidak Terisi", index=df_last.index, dtype="string")

    jenis_kelamin = (
        df_last["jenis_kelamin"].astype("string").str.strip().str.upper()
        if "jenis_kelamin" in df_last.columns
        else pd.Series("", index=df_last.index, dtype="string")
    )
    data = pd.DataFrame({"Diagnosa": diagnosis, "jenis_kelamin": jenis_kelamin})
    data = data[data["jenis_kelamin"].isin(["L", "P"])]
    if data.empty:
        return pd.DataFrame(columns=columns)

    counts = data.groupby(["Diagnosa", "jenis_kelamin"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=["L", "P"], fill_value=0)
    counts["Total"] = counts["L"] + counts["P"]
    counts = counts.sort_values(["Total", "Diagnosa"], ascending=[False, True]).head(10)
    result = counts.reset_index()
    result.insert(0, "No", range(1, len(result) + 1))
    result.columns.name = None
    return result[columns]
