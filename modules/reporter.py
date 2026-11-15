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
