import streamlit as st
import pandas as pd
import io
from modules.loader import get_sheet_names, load_data
from modules.cleaner import clean_nama, clean_kelas, cek_kelas_titipan, split_jk_umur, kategori_umur, parse_kamar
from modules.tracker import track_perpindahan
from modules.master_data import init_master_tt, update_master_tt, init_master_kelas, update_master_kelas
from modules.bor_calculator import hitung_bor, hitung_bor_kelas, hitung_rata_rata_bor_kelas

st.set_page_config(
    page_title="SIM-RM Helper",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    h1 {
        color: #0ea5e9;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏥 SIM-RM Helper")
st.caption("Asisten Laporan Rekam Medis — Upload, Olah, Laporkan")
st.markdown("---")

if "df_mentah" not in st.session_state:
    st.session_state.df_mentah = None

tab_master, tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Master Data", "📤 Upload", "🔁 Mutasi", "🏥 BOR", "📊 Laporan"])

with tab_master:
    init_master_tt()
    init_master_kelas()
    st.subheader("⚙️ Master Tempat Tidur (TT)")
    st.info("Silakan atur jumlah tempat tidur per ruangan.")

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
        st.success("Master TT berhasil diperbarui!")

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
        st.success("Master Kelas Kamar berhasil diperbarui!")

with tab1:
    st.subheader("📤 Upload Data Mentah")
    st.info("💡 Silakan upload file Excel/CSV hasil tarikan sistem SIMRS.")

    uploaded = st.file_uploader("Pilih file", type=["xlsx", "xls", "csv"], label_visibility="collapsed")

    if uploaded:
        file_bytes = uploaded.read()
        sheet_names = get_sheet_names(file_bytes, uploaded.name)

        if not sheet_names:
            st.error("❌ Gagal membaca file. Pastikan format file tidak corrupt.")
        elif sheet_names[0].startswith("ERROR:"):
            st.error(f"❌ Detail Error: {sheet_names[0]}")
        else:
            selected_sheet = sheet_names[0]
            if len(sheet_names) > 1:
                st.write("---")
                selected_sheet = st.selectbox("📑 Pilih Sheet yang mau diolah:", sheet_names)

            with st.spinner("Membaca data..."):
                df, error = load_data(file_bytes, uploaded.name, selected_sheet)

            if error:
                st.error(f"❌ Error saat membaca data: {error}")
            else:
                st.session_state.df_mentah = df
                st.success(f"✅ Berhasil membaca **{uploaded.name}** (Sheet: `{selected_sheet}`)")

                st.write("")
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Baris", f"{df.shape[0]:,}")
                col2.metric("Total Kolom", df.shape[1])
                col3.metric("Status", "Siap Diproses")

                st.write("")
                pv1, pv2 = st.tabs(["📋 Preview Data (5 Baris)", "🔍 Daftar Kolom"])

                with pv1:
                    st.dataframe(df.head(), use_container_width=True)

                with pv2:
                    kolom_df = {"No": range(1, len(df.columns)+1), "Nama Kolom": list(df.columns)}
                    st.dataframe(kolom_df, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.subheader("Pemetaan Kolom")
                kolom_options = list(df.columns)
                pilihan = ["— Pilih kolom —"] + kolom_options

                def default_index(kata_kunci):
                    for i, nama_kolom in enumerate(kolom_options, start=1):
                        nama = str(nama_kolom).lower()
                        if any(kata in nama for kata in kata_kunci):
                            return i
                    return 0

                nama_umur_menyatu = st.checkbox(
                    "Apakah Nama dan Umur menyatu di kolom Nama?",
                    value=False,
                    key="nama_umur_menyatu",
                )
                map_col1, map_col2, map_col3 = st.columns(3)
                with map_col1:
                    kolom_nama = st.selectbox("Kolom Nama Pasien", pilihan, index=default_index(["nama"]), key="map_nama")
                    if not nama_umur_menyatu:
                        kolom_jk_umur = st.selectbox("Kolom JK/Umur", pilihan, index=default_index(["jk", "umur", "usia", "kelamin"]), key="map_jk_umur")
                with map_col2:
                    kolom_no_rm = st.selectbox("Kolom No. RM", pilihan, index=default_index(["no rm", "norm", "no. rm", "rekam medik", "rekam medis"]), key="map_no_rm")
                    kolom_kamar = st.selectbox("Kolom Kamar", pilihan, index=default_index(["kamar", "ruang"]), key="map_kamar")
                with map_col3:
                    kolom_tgl_masuk = st.selectbox("Kolom Tanggal Masuk", pilihan, index=default_index(["tgl masuk", "tanggal masuk", "tgl_masuk", "masuk"]), key="map_tgl_masuk")
                    kolom_tgl_keluar = st.selectbox("Kolom Tanggal Keluar", pilihan, index=default_index(["tgl keluar", "tanggal keluar", "tgl_keluar", "keluar"]), key="map_tgl_keluar")
                    kolom_kelas = st.selectbox("Kolom Kelas Jaminan (VIP/1/2/3)", pilihan, index=default_index(["kelas jaminan", "kelas_jam", "jaminan", "kelas"]), key="map_kelas_jaminan")

                if st.button("🚀 Proses Data"):
                    def nilai_kolom(nama_kolom):
                        if nama_kolom == "— Pilih kolom —":
                            return pd.Series([None] * len(df), index=df.index)
                        return df[nama_kolom]

                    if nama_umur_menyatu:
                        jk_umur = nilai_kolom(kolom_nama).apply(split_jk_umur)
                    else:
                        jk_umur = nilai_kolom(kolom_jk_umur).apply(split_jk_umur)
                    kamar = nilai_kolom(kolom_kamar).apply(parse_kamar)
                    df_clean = pd.DataFrame({
                        "no_rm": nilai_kolom(kolom_no_rm),
                        "nama": nilai_kolom(kolom_nama).apply(clean_nama),
                        "jenis_kelamin": jk_umur.apply(lambda hasil: hasil[0]),
                        "umur_tahun": jk_umur.apply(lambda hasil: hasil[1]),
                        "kategori_umur": jk_umur.apply(lambda hasil: kategori_umur(hasil[1])),
                        "kelas_jam": nilai_kolom(kolom_kelas).apply(clean_kelas),
                        "kode_kamar": kamar.apply(lambda hasil: hasil[0]),
                        "ruang": kamar.apply(lambda hasil: hasil[1]),
                        "kelas": kamar.apply(lambda hasil: hasil[2]),
                        "tgl_masuk": pd.to_datetime(nilai_kolom(kolom_tgl_masuk), errors="coerce"),
                        "tgl_keluar": pd.to_datetime(nilai_kolom(kolom_tgl_keluar), errors="coerce"),
                    })
                    master_kelas = st.session_state.get("master_kelas", {})
                    df_clean["is_titipan"] = df_clean.apply(
                        lambda row: cek_kelas_titipan(row, master_kelas), axis=1
                    )
                    st.session_state.df_clean = df_clean

                if st.session_state.get("df_clean") is not None:
                    df_clean = st.session_state.df_clean
                    st.dataframe(df_clean.head(), use_container_width=True)
                    if "is_titipan" in df_clean.columns and df_clean["is_titipan"].any():
                        st.warning("Ada pasien titipan: kelas jaminan berbeda dari Kelas Kamar fisik.")
                        kolom_titipan = df_clean.loc[
                            df_clean["is_titipan"], ["no_rm", "nama", "kelas_jam", "ruang"]
                        ].rename(columns={
                            "kelas_jam": "Kelas Jaminan (Excel)",
                            "ruang": "Kamar Fisik",
                        })
                        st.dataframe(kolom_titipan, use_container_width=True, hide_index=True)
                    excel_buffer = io.BytesIO()
                    df_clean.to_excel(excel_buffer, index=False, engine="openpyxl")
                    st.download_button(
                        "Download Excel Bersih",
                        data=excel_buffer.getvalue(),
                        file_name="data_bersih.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
    else:
        st.write("")
        st.info("Belum ada file yang di-upload.")

with tab2:
    st.subheader("🔁 Track Perpindahan Kamar")
    df_clean = st.session_state.get("df_clean")
    if df_clean is None or df_clean.empty:
        st.info("Silakan upload dan proses data di Tab Upload terlebih dahulu.")
    else:
        df_long = track_perpindahan(df_clean)
        df_tampilan = df_long.rename(columns={"pindah": "Pindahan"})
        st.dataframe(df_tampilan, use_container_width=True, hide_index=True)
        excel_buffer = io.BytesIO()
        df_tampilan.to_excel(excel_buffer, index=False, engine="openpyxl")
        st.download_button(
            "Download Hasil Track (Excel)",
            data=excel_buffer.getvalue(),
            file_name="track_perpindahan.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

with tab3:
    st.subheader("🏥 BOR & Indikator")
    df_clean = st.session_state.get("df_clean")
    master_tt = st.session_state.get("master_tt")
    if df_clean is None or df_clean.empty:
        st.info("Silakan upload dan proses data di Tab Upload terlebih dahulu.")
    elif not master_tt:
        st.info("Atur jumlah tempat tidur di Tab Master Data terlebih dahulu.")
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
                "Download Hasil BOR (Excel)",
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

with tab4:
    st.subheader("📊 Laporan RL & Akreditasi")
    st.write("Fitur dalam pengembangan.")
