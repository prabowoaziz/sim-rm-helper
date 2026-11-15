import streamlit as st
import pandas as pd
import io
import json
import hashlib
from pathlib import Path
from modules.loader import get_sheet_names, load_sheet_by_name
from modules.cleaner import clean_nama, clean_kelas, guess_column_types, guess_jk_from_nama, split_jk_umur, kategori_umur, parse_kamar
from modules.tracker import track_perpindahan
from modules.master_data import (
    init_master_tt,
    update_master_tt,
    init_master_kelas,
    update_master_kelas,
    load_master_from_supabase,
    save_master_to_supabase,
)
from modules.bor_calculator import hitung_bor, hitung_bor_kelas, hitung_rata_rata_bor_kelas
from modules.reporter import hitung_statistik_dan_mortalitas, hitung_rl_31, hitung_rl_4a
from modules.icd_loader import upload_icd_to_supabase


def kategori_ruangan(row):
    kode_nilai = row.get("kode_kamar")
    ruang_nilai = row.get("ruang")
    kode = "" if pd.isna(kode_nilai) else str(kode_nilai).upper()
    ruang = "" if pd.isna(ruang_nilai) else str(ruang_nilai).upper()
    teks = f"{kode} {ruang}"
    if "PER" in teks:
        return "PERINA"
    if "HCU" in teks:
        return "HCU"
    if "NIC" in teks:
        return "NICU"
    if "PIC" in teks:
        return "PICU"
    if "ICU" in teks:
        return "ICU"
    return "RAWAT INAP LAINNYA"


st.set_page_config(
    page_title="SIM-RM Helper",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Font & Background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background-color: #f8fafc;
    }

    /* Sembunyikan menu Streamlit bawaan */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Percantik Card Metrics */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border-top: 4px solid #0ea5e9;
    }
    div[data-testid="stMetric"] label {
        color: #64748b;
        font-weight: 600;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #0f172a;
        font-weight: 700;
    }

    /* Percantik Tombol */
    .stButton > button {
        background-color: #0ea5e9;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.2s ease;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #0284c7;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);
    }

    /* Percantik Tab */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #ffffff;
        padding: 8px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e0f2fe !important;
        color: #0284c7 !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_supabase_client():
    try:
        from supabase import create_client
        config = st.secrets["supabase"]
        return create_client(config["url"], config["key"])
    except Exception:
        return None


def simpan_riwayat_upload(client, df_clean, nama_file):
    data_json = json.loads(df_clean.to_json(orient="records", date_format="iso"))
    return client.table("riwayat_upload").insert({
        "nama_file": nama_file,
        "data_json": data_json,
    }).execute()


def muat_riwayat_upload_terakhir(client):
    response = (
        client.table("riwayat_upload")
        .select("nama_file, data_json")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        return None, None

    row = rows[0]
    data_json = row.get("data_json") or []
    if isinstance(data_json, str):
        data_json = json.loads(data_json)
    df_clean = pd.read_json(
        io.StringIO(json.dumps(data_json)),
        orient="records",
        dtype=False,
    )
    for kolom_tanggal in ("tgl_masuk", "tgl_keluar"):
        if kolom_tanggal in df_clean.columns:
            df_clean[kolom_tanggal] = pd.to_datetime(df_clean[kolom_tanggal], errors="coerce")
    return df_clean, row.get("nama_file")


supabase_client = get_supabase_client()

st.markdown("<h1 style='text-align: center; color: #0f172a;'>🏥 SIM-RM Helper</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 16px;'>Asisten Laporan Rekam Medis — Upload, Olah, Laporkan</p>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

if "df_mentah" not in st.session_state:
    st.session_state.df_mentah = None

init_master_tt()
init_master_kelas()
if "master_ruangan_loaded" not in st.session_state:
    st.session_state.master_ruangan_load_error = None
    if supabase_client is not None:
        try:
            load_master_from_supabase(supabase_client)
        except Exception as error:
            st.session_state.master_ruangan_load_error = str(error)
    st.session_state.master_ruangan_loaded = True

menu = st.sidebar.radio(
    "Navigasi Menu",
    [" Dashboard", " Upload Data", " Perpindahan Kamar", " BOR & Indikator", " Laporan RL & Akreditasi", "⚙️ Master Data"],
)

judul_halaman = {
    " Dashboard": "Dashboard",
    " Upload Data": "Unggah Data",
    " Perpindahan Kamar": "Perpindahan Kamar",
    " BOR & Indikator": "BOR & Indikator",
    " Laporan RL & Akreditasi": "Laporan RL & Akreditasi",
    "⚙️ Master Data": "Master Data",
}
st.markdown(
    f"<h1 style='color: #0f172a;'>{judul_halaman[menu]}</h1>",
    unsafe_allow_html=True,
)

if menu == " Dashboard":
    st.subheader("Unggah Cepat")
    uploaded_dash = st.file_uploader(
        "Unggah data SIMRS di sini",
        type=["xlsx", "xls"],
        key="uploader_dash",
    )
    if uploaded_dash is not None:
        dash_bytes = uploaded_dash.getvalue()
        dash_sheet_names = get_sheet_names(dash_bytes, uploaded_dash.name)
        if not dash_sheet_names:
            st.error("Gagal membaca berkas. Pastikan formatnya tidak rusak.")
        elif dash_sheet_names[0].startswith("ERROR:"):
            st.error(f"Gagal membaca berkas: {dash_sheet_names[0]}")
        else:
            dash_sheet = dash_sheet_names[0]
            dash_df, dash_error = load_sheet_by_name(io.BytesIO(dash_bytes), dash_sheet)
            if dash_error:
                st.error(f"Gagal membaca data: {dash_error}")
            else:
                st.session_state.df_mentah = dash_df
                st.session_state.berkas_mentah_bytes = dash_bytes
                st.session_state.berkas_mentah_nama = uploaded_dash.name
                st.session_state.berkas_mentah_sheet = dash_sheet
                st.success("Berkas berhasil dimuat! Silakan atur pemetaan di menu Unggah Data.")

    st.subheader("Ringkasan Operasional RS")
    df_dashboard = st.session_state.get("df_clean")
    if df_dashboard is None or df_dashboard.empty:
        st.info("Belum ada data. Silakan unggah melalui menu Unggah Data.")
    else:
        if "no_rm" in df_dashboard.columns:
            df_dashboard_pasien = df_dashboard.drop_duplicates(subset=["no_rm"], keep="last")
            total_pasien = int(df_dashboard["no_rm"].nunique())
        else:
            df_dashboard_pasien = df_dashboard
            total_pasien = len(df_dashboard)
        jenis_kelamin = (
            df_dashboard_pasien["jenis_kelamin"].astype("string").str.strip().str.upper()
            if "jenis_kelamin" in df_dashboard_pasien.columns
            else pd.Series(dtype="string")
        )
        total_laki = int(jenis_kelamin.eq("L").sum())
        total_perempuan = int(jenis_kelamin.eq("P").sum())
        umur = (
            pd.to_numeric(df_dashboard_pasien["umur_tahun"], errors="coerce")
            if "umur_tahun" in df_dashboard_pasien.columns
            else pd.Series(dtype="float64")
        )
        rata_rata_umur = umur.mean()
        umur_label = f"{rata_rata_umur:.1f} tahun" if pd.notna(rata_rata_umur) else "—"

        metrik = st.columns(4)
        metrik[0].metric("Total Pasien", f"{total_pasien:,}")
        metrik[1].metric("Laki-laki", f"{total_laki:,}")
        metrik[2].metric("Perempuan", f"{total_perempuan:,}")
        metrik[3].metric("Rata-rata Umur", umur_label)

        st.subheader("Distribusi Status Pulang")
        if "status_pulang" in df_dashboard.columns:
            status_counts_dashboard = df_dashboard["status_pulang"].value_counts()
        else:
            status_counts_dashboard = pd.Series(dtype="int64")
        if status_counts_dashboard.empty:
            st.info("Belum ada data status pulang.")
        else:
            st.bar_chart(status_counts_dashboard)

        st.subheader("Top 5 Ruangan Terbanyak")
        if "ruang" in df_dashboard.columns:
            ruang_counts_dashboard = df_dashboard["ruang"].value_counts().head(5)
        else:
            ruang_counts_dashboard = pd.Series(dtype="int64")
        if ruang_counts_dashboard.empty:
            st.info("Belum ada data ruangan.")
        else:
            st.bar_chart(ruang_counts_dashboard)

        st.subheader("Distribusi Kelompok Umur")
        kelompok_umur = pd.cut(
            umur,
            bins=[0, 6, 18, 60, float("inf")],
            labels=["0-5", "6-17", "18-59", "60+"],
            right=False,
        )
        distribusi_umur = kelompok_umur.value_counts(sort=False).reindex(
            ["0-5", "6-17", "18-59", "60+"],
            fill_value=0,
        )
        st.bar_chart(distribusi_umur)

if menu == "⚙️ Master Data":
    init_master_tt()
    init_master_kelas()
    st.subheader("⚙️ Master Tempat Tidur (TT)")
    st.info("Silakan atur jumlah tempat tidur per ruangan.")
    if st.session_state.get("master_ruangan_load_error"):
        st.warning(f"Master ruangan gagal dimuat dari Supabase: {st.session_state.master_ruangan_load_error}")
    elif supabase_client is None:
        st.warning("Supabase belum dikonfigurasi. Perubahan Master Data hanya tersimpan selama sesi ini.")

    master_tt_baru = {}
    for ruang, jumlah in st.session_state.master_tt.items():
        master_tt_baru[ruang] = st.number_input(
            ruang,
            min_value=0,
            value=int(jumlah),
            step=1,
            key=f"master_tt_{ruang}",
        )

    ruang_baru = st.text_input("Nama ruang baru", key="master_tt_ruang_baru")
    if st.button("Tambah Ruangan"):
        ruang_baru = ruang_baru.strip()
        if ruang_baru and ruang_baru not in st.session_state.master_tt:
            update_master_tt(ruang_baru, 0)
            st.rerun()
        elif ruang_baru in st.session_state.master_tt:
            st.warning("Ruangan tersebut sudah ada.")

    if st.button("Simpan Master TT"):
        for ruang, jumlah in master_tt_baru.items():
            update_master_tt(ruang, jumlah)
        if supabase_client is not None:
            try:
                save_master_to_supabase(supabase_client)
                st.success("Master TT berhasil disimpan ke Supabase!")
            except Exception as error:
                st.error(f"Gagal menyimpan Master TT ke Supabase: {error}")
        else:
            st.warning("Master TT diperbarui di sesi ini, tetapi belum tersimpan ke Supabase.")

    st.markdown("### 🛏️ Master Kelas Kamar")
    kelas_opsi = ["VIP", "1", "2", "3"]
    kelas_kamar_baru = {}
    kolom_kelas_kamar = st.columns(4)
    for idx, ruang in enumerate(st.session_state.master_tt):
        kelas_saat_ini = st.session_state.master_kelas.get(ruang, "1")
        index_kelas = kelas_opsi.index(kelas_saat_ini) if kelas_saat_ini in kelas_opsi else 1
        with kolom_kelas_kamar[idx % 4]:
            kelas_kamar_baru[ruang] = st.selectbox(
                ruang,
                kelas_opsi,
                index=index_kelas,
                key=f"master_kelas_{ruang}",
            )

    if st.button("Simpan Master Kelas Kamar"):
        for ruang, kelas in kelas_kamar_baru.items():
            update_master_kelas(ruang, kelas)
        if supabase_client is not None:
            try:
                save_master_to_supabase(supabase_client)
                st.success("Master Kelas Kamar berhasil disimpan ke Supabase!")
            except Exception as error:
                st.error(f"Gagal menyimpan Master Kelas Kamar ke Supabase: {error}")
        else:
            st.warning("Master Kelas Kamar diperbarui di sesi ini, tetapi belum tersimpan ke Supabase.")

    st.subheader("🧾 Kamus ICD-10")
    if supabase_client is None:
        st.info("Total kamus ICD-10 di database: tidak tersedia (Supabase belum dikonfigurasi).")
    else:
        try:
            jumlah_master_icd = (
                supabase_client.table("master_icd")
                .select("code", count="exact")
                .limit(0)
                .execute()
                .count
            )
            st.info(f"Total kamus ICD-10 di database: {jumlah_master_icd or 0:,} baris.")
        except Exception as error:
            st.warning(f"Jumlah kamus ICD-10 gagal dimuat: {error}")

    icd_file = st.file_uploader("Unggah berkas ICD-10 (.xlsx)", type=["xlsx"], key="upload_master_icd")
    if icd_file is not None:
        icd_bytes = icd_file.getvalue()
        icd_hash = hashlib.sha256(icd_bytes).hexdigest()
        if st.session_state.get("icd_import_hash") == icd_hash:
            st.caption("Berkas ICD-10 ini sudah diimpor pada sesi ini.")
        elif supabase_client is None:
            st.error("Supabase belum dikonfigurasi. Master ICD-10 tidak dapat diimpor.")
        else:
            try:
                with st.spinner("Mengimpor data ICD..."):
                    jumlah_icd = upload_icd_to_supabase(icd_bytes, supabase_client)
                st.session_state.icd_import_hash = icd_hash
                st.success(f"Berhasil mengimpor {jumlah_icd:,} kode ICD-10.")
            except Exception as error:
                st.error(f"Gagal mengimpor ICD-10 ke Supabase: {error}")

if menu == " Upload Data":
    st.subheader("📤 Unggah Data Mentah")
    if st.button("⬇️ Muat Data dari Sesi Terakhir"):
        if supabase_client is None:
            st.error("Supabase belum dikonfigurasi. Data riwayat tidak dapat dimuat.")
        else:
            try:
                df_terakhir, nama_file_terakhir = muat_riwayat_upload_terakhir(supabase_client)
                if df_terakhir is None:
                    st.warning("Belum ada riwayat upload di database.")
                else:
                    st.session_state.df_clean = df_terakhir
                    st.session_state.nama_file_riwayat = nama_file_terakhir
                    st.success("Berhasil memuat data dari database!")
            except Exception as error:
                st.error(f"Gagal memuat data dari database: {error}")
    st.info("💡 Silakan unggah berkas Excel/CSV hasil tarikan sistem SIMRS.")

    uploaded = st.file_uploader("Pilih berkas", type=["xlsx", "xls", "csv"], label_visibility="collapsed")
    if uploaded is None and st.session_state.get("berkas_mentah_bytes") is not None:
        uploaded = io.BytesIO(st.session_state.berkas_mentah_bytes)
        uploaded.name = st.session_state.get("berkas_mentah_nama", "data_simrs.xlsx")

    if uploaded:
        file_bytes = uploaded.read()
        st.session_state.berkas_mentah_bytes = file_bytes
        st.session_state.berkas_mentah_nama = uploaded.name
        sheet_names = get_sheet_names(file_bytes, uploaded.name)

        if not sheet_names:
            st.error("❌ Gagal membaca berkas. Pastikan formatnya tidak rusak.")
        elif sheet_names[0].startswith("ERROR:"):
            st.error(f"❌ Detail Error: {sheet_names[0]}")
        else:
            selected_sheet = (
                st.session_state.get("berkas_mentah_sheet")
                if st.session_state.get("berkas_mentah_sheet") in sheet_names
                else sheet_names[0]
            )
            if len(sheet_names) > 1:
                st.write("---")
                selected_sheet = st.selectbox(
                    "📑 Pilih lembar yang akan diolah:",
                    sheet_names,
                    index=sheet_names.index(selected_sheet),
                )

            with st.spinner("Membaca data..."):
                uploaded.seek(0)
                df, error = load_sheet_by_name(uploaded, selected_sheet)

            if error:
                st.error(f"❌ Error saat membaca data: {error}")
            else:
                st.session_state.df_mentah = df
                st.session_state.berkas_mentah_sheet = selected_sheet
                st.success(f"✅ Berhasil membaca **{uploaded.name}** (Sheet: `{selected_sheet}`)")

                st.write("")
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Baris", f"{df.shape[0]:,}")
                col2.metric("Total Kolom", df.shape[1])
                col3.metric("Status", "Siap Diproses")

                st.write("")
                pv1, pv2 = st.tabs(["📋 Pratinjau Data (20 Baris)", "🔍 Daftar Kolom"])

                with pv1:
                    with st.expander("👁️ Lihat Pratinjau Data Mentah (20 Baris)", expanded=False):
                        st.dataframe(df.head(20), use_container_width=True)

                with pv2:
                    kolom_df = {"No": range(1, len(df.columns)+1), "Nama Kolom": list(df.columns)}
                    st.dataframe(kolom_df, use_container_width=True, hide_index=True)

                tebakan_kolom = guess_column_types(df)
                st.info("✨ Sistem telah menebak kolom secara otomatis. Silakan koreksi jika ada yang salah.")

                st.markdown("---")
                st.subheader("Pemetaan Kolom")
                kolom_options = list(df.columns)
                pilihan = ["— Pilih kolom —"] + kolom_options

                def default_index(kata_kunci, tebakan=None):
                    if tebakan in kolom_options:
                        return kolom_options.index(tebakan) + 1
                    for i, nama_kolom in enumerate(kolom_options, start=1):
                        nama = str(nama_kolom).lower()
                        if any(kata in nama for kata in kata_kunci):
                            return i
                    return 0

                tebakan_jk_umur = tebakan_kolom["jk_umur"] or next(
                    (
                        column for column in kolom_options
                        if not str(column).casefold().startswith(("_drop_", "unnamed"))
                        and any(kata in str(column).casefold() for kata in ("jk", "umur", "usia", "kelamin"))
                    ),
                    tebakan_kolom["nama"],
                )
                map_col1, map_col2, map_col3 = st.columns(3)
                with map_col1:
                    kolom_nama = st.selectbox("Kolom Nama Pasien", pilihan, index=default_index(["nama"], tebakan_kolom["nama"]), key="map_nama")
                    kolom_jk_umur = st.selectbox("Kolom JK/Umur", pilihan, index=default_index(["jk", "umur", "usia", "kelamin"], tebakan_jk_umur), key="map_jk_umur")
                with map_col2:
                    kolom_no_rm = st.selectbox("Kolom No. RM", pilihan, index=default_index(["no rm", "norm", "no. rm", "rekam medik", "rekam medis"], tebakan_kolom["no_rm"]), key="map_no_rm")
                    kolom_kamar = st.selectbox("Kolom Kamar", pilihan, index=default_index(["kamar", "ruang"], tebakan_kolom["kamar"]), key="map_kamar")
                    kolom_penjamin = st.selectbox("Kolom Penjamin", pilihan, index=default_index(["penjamin", "jaminan", "asuransi"], tebakan_kolom["penjamin"]), key="map_penjamin")
                    kolom_diagnosa = st.selectbox("Kolom Diagnosa", pilihan, index=default_index(["diagnosa", "diagnosis"]), key="map_diagnosa")
                with map_col3:
                    kolom_tgl_masuk = st.selectbox("Kolom Tanggal Masuk", pilihan, index=default_index(["tgl masuk", "tanggal masuk", "tgl_masuk", "masuk"], tebakan_kolom["tgl_masuk"]), key="map_tgl_masuk")
                    kolom_tgl_keluar = st.selectbox("Kolom Tanggal Keluar", pilihan, index=default_index(["tgl keluar", "tanggal keluar", "tgl_keluar", "keluar"], tebakan_kolom["tgl_keluar"]), key="map_tgl_keluar")
                    kolom_kelas = st.selectbox("Kolom Kelas Jaminan (VIP/1/2/3)", pilihan, index=default_index(["kelas_jam", "kelas"], tebakan_kolom["kelas_jaminan"]), key="map_kelas_jaminan")
                    kolom_status = st.selectbox("Kolom Status Pulang (Sembuh/Meninggal)", pilihan, index=default_index(["status pulang", "status_pulang", "status", "pulang"]), key="map_status_pulang")

                if st.button("🚀 Proses Data"):
                    with st.spinner("Membersihkan data..."):
                        df_temp = st.session_state.df_mentah.copy()
                        data_bersih = []
                        kolom_tidak_dipilih = pilihan[0]

                        def nilai_baris(row, nama_kolom):
                            if nama_kolom == kolom_tidak_dipilih or nama_kolom not in row.index:
                                return None
                            nilai = row[nama_kolom]
                            return None if pd.isna(nilai) else nilai

                        for _, row in df_temp.iterrows():
                            raw_nama = nilai_baris(row, kolom_nama) or ""
                            raw_jk_umur = nilai_baris(row, kolom_jk_umur) or ""
                            jk, umur = split_jk_umur(f"{raw_nama} {raw_jk_umur}".strip())
                            if jk is None and umur is None:
                                jk, umur = split_jk_umur(raw_nama)
                            if jk is None:
                                jk = guess_jk_from_nama(raw_nama)

                            nama_bersih = clean_nama(raw_nama)
                            raw_kamar = nilai_baris(row, kolom_kamar) or ""
                            kode_kamar, ruang, kelas_kamar = parse_kamar(raw_kamar)
                            tgl_masuk = pd.to_datetime(nilai_baris(row, kolom_tgl_masuk), errors="coerce")
                            raw_tgl_keluar = nilai_baris(row, kolom_tgl_keluar)
                            tgl_keluar = (
                                pd.to_datetime(raw_tgl_keluar, errors="coerce")
                                if raw_tgl_keluar is not None else pd.NaT
                            )
                            raw_kelas = nilai_baris(row, kolom_kelas)
                            master_kelas = st.session_state.get("master_kelas", {})
                            kelas_fisik_raw = master_kelas.get(ruang, kelas_kamar)

                            def kelas_standar(nilai):
                                if nilai is None:
                                    return ""
                                teks = str(nilai).strip().upper()
                                if teks in {"1.0", "2.0", "3.0"}:
                                    teks = teks[0]
                                return teks if teks in {"1", "2", "3", "VIP"} else ""

                            kelas_excel = kelas_standar(raw_kelas)
                            kelas_fisik = kelas_standar(kelas_fisik_raw)
                            is_titipan = (
                                kelas_excel in {"1", "2", "3", "VIP"}
                                and kelas_fisik in {"1", "2", "3", "VIP"}
                                and kelas_excel != kelas_fisik
                            )
                            kelas_jam = clean_kelas(kelas_excel or kelas_fisik)
                            no_rm = nilai_baris(row, kolom_no_rm)
                            if no_rm is None:
                                no_rm = None
                            elif isinstance(no_rm, (int, float)) and float(no_rm).is_integer():
                                no_rm = str(int(no_rm))
                            else:
                                no_rm = str(no_rm).strip()
                                if "." in no_rm:
                                    bagian_bilangan = no_rm.split(".", 1)
                                    if bagian_bilangan[0].isdigit() and not bagian_bilangan[1].strip("0"):
                                        no_rm = bagian_bilangan[0]
                            status_raw = nilai_baris(row, kolom_status)

                            data_bersih.append({
                                "no_rm": no_rm or None,
                                "nama": nama_bersih,
                                "jenis_kelamin": jk,
                                "umur_tahun": umur,
                                "kategori_umur": kategori_umur(umur),
                                "penjamin": nilai_baris(row, kolom_penjamin),
                                "diagnosa": nilai_baris(row, kolom_diagnosa),
                                "kelas_jam": kelas_jam,
                                "kode_kamar": kode_kamar,
                                "ruang": ruang,
                                "kelas": kelas_kamar,
                                "tgl_masuk": tgl_masuk,
                                "tgl_keluar": tgl_keluar,
                                "status_pulang": status_raw,
                                "is_titipan": is_titipan,
                            })

                        kolom_bersih = [
                            "no_rm", "nama", "jenis_kelamin", "umur_tahun", "kategori_umur",
                            "penjamin", "diagnosa", "kelas_jam", "kode_kamar", "ruang", "kelas",
                            "tgl_masuk", "tgl_keluar", "status_pulang", "is_titipan",
                        ]
                        df_clean = pd.DataFrame(data_bersih, columns=kolom_bersih)
                        df_clean = df_clean.dropna(subset=["nama", "no_rm"])
                        df_clean = df_clean.reset_index(drop=True)
                        st.session_state.df_clean = df_clean
                        st.session_state.nama_file_riwayat = uploaded.name
                        if supabase_client is not None:
                            try:
                                simpan_riwayat_upload(supabase_client, df_clean, uploaded.name)
                                st.success("Salinan data berhasil disimpan ke riwayat database.")
                            except Exception as error:
                                st.warning(f"Data bersih tersedia, tetapi gagal disimpan ke database: {error}")
                        else:
                            st.warning("Supabase belum dikonfigurasi; data bersih hanya tersedia di sesi ini.")
                    st.success("✅ Data berhasil dibersihkan!")

                if st.session_state.get("df_clean") is not None:
                    df_clean = st.session_state.df_clean
                    with st.expander("✅ Lihat Pratinjau Data Bersih", expanded=False):
                        st.dataframe(df_clean.head(20), use_container_width=True)
                    excel_buffer = io.BytesIO()
                    df_clean.to_excel(excel_buffer, index=False, engine="openpyxl")
                    nama_file_asli = Path(uploaded.name).stem
                    st.download_button(
                        "Unduh Semua Data (Excel)",
                        data=excel_buffer.getvalue(),
                        file_name=f"Data_Bersih_{nama_file_asli}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                    with st.expander("⬇️ Unduh Data per Ruangan"):
                        kategori_per_baris = df_clean.apply(kategori_ruangan, axis=1)
                        for kategori in kategori_per_baris.dropna().unique():
                            mask_ruangan = kategori_per_baris == kategori
                            df_ruangan = df_clean.loc[mask_ruangan]
                            if df_ruangan.empty:
                                continue
                            buffer_ruangan = io.BytesIO()
                            df_ruangan.to_excel(buffer_ruangan, index=False, engine="openpyxl")
                            st.download_button(
                                f"Unduh {kategori} ({len(df_ruangan)} baris)",
                                data=buffer_ruangan.getvalue(),
                                file_name=f"Data_Bersih_{kategori.replace(' ', '_')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"download_ruangan_{kategori}",
                            )
                    if "is_titipan" in df_clean.columns and df_clean["is_titipan"].any():
                        st.warning("Ada pasien titipan: kelas jaminan berbeda dari Kelas Kamar fisik.")
                        kolom_titipan = df_clean.loc[
                            df_clean["is_titipan"], ["no_rm", "nama", "kelas_jam", "ruang"]
                        ].rename(columns={
                            "kelas_jam": "Kelas Jaminan (Excel)",
                            "ruang": "Kamar Fisik",
                        })
                        st.dataframe(kolom_titipan, use_container_width=True, hide_index=True)
    else:
        st.write("")
        df_clean_tersimpan = st.session_state.get("df_clean")
        if df_clean_tersimpan is not None:
            st.info(f"Data bersih tersedia dari riwayat: {st.session_state.get('nama_file_riwayat') or 'upload terakhir'}.")
            with st.expander("✅ Lihat Pratinjau Data Bersih", expanded=False):
                st.dataframe(df_clean_tersimpan.head(20), use_container_width=True)
        else:
            st.info("Belum ada berkas yang diunggah.")

if menu == " Perpindahan Kamar":
    st.subheader("🔁 Perpindahan Kamar")
    df_clean = st.session_state.get("df_clean")
    if df_clean is None or df_clean.empty:
        st.info("Silakan unggah dan proses data di menu Unggah Data terlebih dahulu.")
    else:
        df_long = track_perpindahan(df_clean)
        df_tampilan = df_long.rename(columns={"pindah": "Pindahan"})
        st.dataframe(df_tampilan, use_container_width=True, hide_index=True)
        excel_buffer = io.BytesIO()
        df_tampilan.to_excel(excel_buffer, index=False, engine="openpyxl")
        st.download_button(
            "Unduh Hasil Perpindahan (Excel)",
            data=excel_buffer.getvalue(),
            file_name="track_perpindahan.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

if menu == " BOR & Indikator":
    st.subheader("🏥 BOR & Indikator")
    df_clean = st.session_state.get("df_clean")
    master_tt = st.session_state.get("master_tt")
    if df_clean is None or df_clean.empty:
        st.info("Silakan unggah dan proses data di menu Unggah Data terlebih dahulu.")
    elif not master_tt:
        st.info("Atur jumlah tempat tidur di menu Master Data terlebih dahulu.")
    else:
        df_long = track_perpindahan(df_clean)
        df_bor = hitung_bor(df_long, master_tt, periode_hari=30)
        if df_bor.empty:
            st.info("Belum ada data BOR yang dapat dihitung untuk ruangan dengan jumlah TT.")
        else:
            total_rs = df_bor[df_bor["Ruangan"] == "TOTAL RS"]
            if not total_rs.empty:
                total = total_rs.iloc[0]
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("BOR", f"{total['BOR (%)']:.2f}%")
                col2.metric("ALOS", f"{total['ALOS (hari)']:.2f} hari")
                col3.metric("TOI", f"{total['TOI (hari)']:.2f} hari")
                col4.metric("BTO", f"{total['BTO (kali)']:.2f} kali")

            st.dataframe(df_bor, use_container_width=True, hide_index=True)
            excel_buffer = io.BytesIO()
            df_bor.to_excel(excel_buffer, index=False, engine="openpyxl")
            st.download_button(
                "Unduh Hasil BOR (Excel)",
                data=excel_buffer.getvalue(),
                file_name="hasil_bor.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            st.markdown("### BOR per Kelas (Kapasitas 35 TT)")
            df_bor_kelas = hitung_bor_kelas(df_long, kapasitas_tt=35)
            if df_bor_kelas.empty:
                st.info("Belum ada data BOR per kelas yang dapat dihitung.")
            else:
                rata_rata = hitung_rata_rata_bor_kelas(df_bor_kelas)
                metrik = st.columns(5)
                metrik[0].metric("BOR VIP", f"{rata_rata['BOR_VIP']:.2f}%")
                metrik[1].metric("BOR Kelas 1", f"{rata_rata['BOR_1']:.2f}%")
                metrik[2].metric("BOR Kelas 2", f"{rata_rata['BOR_2']:.2f}%")
                metrik[3].metric("BOR Kelas 3", f"{rata_rata['BOR_3']:.2f}%")
                metrik[4].metric("BOR Total", f"{rata_rata['BOR_Total']:.2f}%")
                st.dataframe(df_bor_kelas, use_container_width=True, hide_index=True)

if menu == " Laporan RL & Akreditasi":
    st.subheader("📊 Laporan RL & Akreditasi")
    df_clean = st.session_state.get("df_clean")
    if df_clean is None or df_clean.empty:
        st.info("Silakan unggah dan proses data di menu Unggah Data terlebih dahulu.")
        df_long = pd.DataFrame()
    else:
        df_long = track_perpindahan(df_clean)

    status_counts, mortalitas_df = hitung_statistik_dan_mortalitas(df_long)
    with st.expander("📊 Laporan Statistik & Mortalitas", expanded=False):
        st.subheader("📈 Statistik Pasien")
        st.dataframe(status_counts, use_container_width=True, hide_index=True)
        statistik_buffer = io.BytesIO()
        status_counts.to_excel(statistik_buffer, index=False, engine="openpyxl")
        st.download_button(
            "Unduh Statistik Pasien (Excel)",
            data=statistik_buffer.getvalue(),
            file_name="statistik_pasien.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_statistik_pasien",
        )

        st.subheader("🪦 Angka Kematian (Mortalitas)")
        st.dataframe(mortalitas_df, use_container_width=True, hide_index=True)
        mortalitas_buffer = io.BytesIO()
        mortalitas_df.to_excel(mortalitas_buffer, index=False, engine="openpyxl")
        st.download_button(
            "Unduh Mortalitas (Excel)",
            data=mortalitas_buffer.getvalue(),
            file_name="mortalitas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_mortalitas",
        )

    with st.expander("📋 RL 3.1 — Kegiatan Pelayanan Ranap", expanded=False):
        rl_31_df = hitung_rl_31(df_long)
        st.dataframe(rl_31_df, use_container_width=True, hide_index=True)
        rl_31_buffer = io.BytesIO()
        rl_31_df.to_excel(rl_31_buffer, index=False, engine="openpyxl")
        st.download_button(
            "Unduh RL 3.1 (Excel)",
            data=rl_31_buffer.getvalue(),
            file_name="RL_3_1_kegiatan_pelayanan_ranap.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_rl_31",
        )

    with st.expander("📋 RL 4a — Morbiditas Rawat Inap", expanded=False):
        rl_4a_df = hitung_rl_4a(df_long)
        st.dataframe(rl_4a_df, use_container_width=True, hide_index=True)
        rl_4a_buffer = io.BytesIO()
        rl_4a_df.to_excel(rl_4a_buffer, index=False, engine="openpyxl")
        st.download_button(
            "Unduh RL 4a (Excel)",
            data=rl_4a_buffer.getvalue(),
            file_name="RL_4a_morbiditas_rawat_inap.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_rl_4a",
        )

        with st.expander("⚙️ Pemetaan Kode ICD-10", expanded=False):
            teks_diagnosa = st.text_input(
                "Cari diagnosa untuk saran kode ICD-10",
                key="icd_diagnosa_search",
            ).strip()
            if len(teks_diagnosa) >= 2:
                if supabase_client is None:
                    st.info("Supabase belum dikonfigurasi; pencarian ICD-10 tidak tersedia.")
                else:
                    try:
                        hasil_icd = (
                            supabase_client.table("master_icd")
                            .select("code, display, version")
                            .ilike("display", f"%{teks_diagnosa}%")
                            .limit(20)
                            .execute()
                            .data
                            or []
                        )
                        icd_by_code = {
                            str(item["code"]): item
                            for item in hasil_icd
                            if item.get("code") is not None
                        }
                        if icd_by_code:
                            kode_sebelumnya = st.session_state.get("icd_kode_terpilih")
                            index_kode = (
                                list(icd_by_code).index(kode_sebelumnya)
                                if kode_sebelumnya in icd_by_code
                                else 0
                            )
                            kode_terpilih = st.selectbox(
                                "Pilih kode ICD-10 yang sesuai",
                                options=list(icd_by_code),
                                index=index_kode,
                                format_func=lambda code: f"{code} — {icd_by_code[code].get('display', '')}",
                                key="icd_diagnosa_code",
                            )
                            data_icd_terpilih = icd_by_code[kode_terpilih]
                            st.session_state.icd_kode_terpilih = kode_terpilih
                            st.caption(
                                f"Terpilih: {kode_terpilih} — {data_icd_terpilih.get('display', '')} "
                                f"(Versi {data_icd_terpilih.get('version', '—')})"
                            )
                        else:
                            st.session_state.pop("icd_kode_terpilih", None)
                            st.info("Tidak ada kode ICD-10 yang cocok dengan teks tersebut.")
                    except Exception as error:
                        st.error(f"Pencarian ICD-10 gagal: {error}")
            elif teks_diagnosa:
                st.caption("Masukkan minimal 2 karakter untuk mencari.")

    with st.expander(
        "📝 Audit KLPCM (Kelengkapan Rekam Medis)",
        expanded=st.session_state.get("klpcm_expanded", False),
    ):
        with st.form("form_klpcm"):
            jumlah_diaudit = st.number_input("Jumlah RM yang diaudit", min_value=1, value=20)
            jumlah_lengkap = st.number_input(
                "RM Lengkap (Identitas, Diagnosa, TTD Dokter, dll)",
                min_value=0,
                value=15,
            )
            hitung_klpcm = st.form_submit_button("Hitung KLPCM")

        if hitung_klpcm:
            st.session_state.klpcm_persentase = (jumlah_lengkap / jumlah_diaudit) * 100
            st.session_state.klpcm_expanded = True
            st.rerun()

        if "klpcm_persentase" in st.session_state:
            persentase = st.session_state.klpcm_persentase
            st.metric("Persentase KLPCM", f"{persentase:.2f}%")
            if persentase >= 80:
                st.success("✅ Memenuhi standar akreditasi (≥ 80%)")
            else:
                st.error("❌ Belum memenuhi standar akreditasi (< 80%)")
