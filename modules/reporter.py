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
        status = pd.Series("", index=df_last.index, dtype="string")
        total_mati = 0

    total_keluar = len(df_last)
    gdr = (total_mati / total_keluar * 1000) if total_keluar > 0 else 0
    # NDR: hanya kematian >= 48 jam
    if 'los_hari' in df_last.columns:
        mati_48jam = df_last[status.str.contains('Meninggal', case=False, na=False) & (df_last['los_hari'] >= 2)]
        ndr = (len(mati_48jam) / total_keluar * 1000) if total_keluar > 0 else 0
    else:
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
    if df_long.empty:
        return pd.DataFrame()

    # 1. Cari kolom diagnosa (antisipasi jika namanya beda)
    kolom_diag = None
    for col in ['diagnosa', 'diagnosis', 'penyakit', 'dx']:
        if col in df_long.columns:
            kolom_diag = col
            break

    if kolom_diag is None:
        # Jika tidak ada kolom diagnosa sama sekali, return dataframe kosong
        return pd.DataFrame(columns=['No', 'Diagnosa', 'L', 'P', 'Total'])

    # 2. Ambil baris terakhir per pasien (menghindari hitung dobel jika pindah kamar)
    df_last = df_long.sort_values('urutan').groupby('no_rm').tail(1).copy()

    # 3. Bersihkan teks diagnosa (isi yang kosong dengan teks tertentu)
    df_last[kolom_diag] = df_last[kolom_diag].fillna("Tidak Ada Diagnosa").astype(str).str.strip()

    # 4. Group by diagnosa dan hitung L/P
    # Pastikan kolom jenis_kelamin ada, jika tidak, buat dummy
    if 'jenis_kelamin' not in df_last.columns:
        df_last['jenis_kelamin'] = 'Tidak Diketahui'

    # Buat pivot table
    df_last['L'] = (df_last['jenis_kelamin'] == 'L').astype(int)
    df_last['P'] = (df_last['jenis_kelamin'] == 'P').astype(int)

    rekap = df_last.groupby(kolom_diag).agg(
        L=('L', 'sum'),
        P=('P', 'sum'),
        Total=('no_rm', 'nunique')
    ).reset_index()

    # 5. Urutkan berdasarkan Total terbanyak
    rekap = rekap.sort_values(by='Total', ascending=False)

    # 6. Rapikan format
    rekap = rekap.rename(columns={kolom_diag: 'Diagnosa'})
    rekap.insert(0, 'No', range(1, len(rekap) + 1))

    # 7. Tambahkan kolom kosong untuk Kode ICD
    rekap['Kode ICD-10'] = ""

    return rekap
