import streamlit as st
import pandas as pd
import io
from pathlib import Path
from modules.loader import get_sheet_names, load_sheet_by_name
from modules.cleaner import clean_nama, clean_kelas, guess_column_types, guess_jk_from_nama, split_jk_umur, kategori_umur, parse_kamar
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
                uploaded.seek(0)
                df, error = load_sheet_by_name(uploaded, selected_sheet)

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

                map_col1, map_col2, map_col3 = st.columns(3)
                with map_col1:
                    kolom_nama = st.selectbox("Kolom Nama Pasien", pilihan, index=default_index(["nama"], tebakan_kolom["nama"]), key="map_nama")
                    kolom_jk_umur = st.selectbox("Kolom JK/Umur", pilihan, index=default_index(["jk", "umur", "usia", "kelamin"]), key="map_jk_umur")
                with map_col2:
                    kolom_no_rm = st.selectbox("Kolom No. RM", pilihan, index=default_index(["no rm", "norm", "no. rm", "rekam medik", "rekam medis"], tebakan_kolom["no_rm"]), key="map_no_rm")
                    kolom_kamar = st.selectbox("Kolom Kamar", pilihan, index=default_index(["kamar", "ruang"], tebakan_kolom["kamar"]), key="map_kamar")
                    kolom_penjamin = st.selectbox("Kolom Penjamin", pilihan, index=default_index(["penjamin", "jaminan", "asuransi"], tebakan_kolom["penjamin"]), key="map_penjamin")
                with map_col3:
                    kolom_tgl_masuk = st.selectbox("Kolom Tanggal Masuk", pilihan, index=default_index(["tgl masuk", "tanggal masuk", "tgl_masuk", "masuk"], tebakan_kolom["tgl_masuk"]), key="map_tgl_masuk")
                    kolom_tgl_keluar = st.selectbox("Kolom Tanggal Keluar", pilihan, index=default_index(["tgl keluar", "tanggal keluar", "tgl_keluar", "keluar"], tebakan_kolom["tgl_keluar"]), key="map_tgl_keluar")
                    kolom_kelas = st.selectbox("Kolom Kelas Jaminan (VIP/1/2/3)", pilihan, index=default_index(["kelas jaminan", "kelas_jam", "jaminan", "kelas"]), key="map_kelas_jaminan")
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
                            "penjamin", "kelas_jam", "kode_kamar", "ruang", "kelas",
                            "tgl_masuk", "tgl_keluar", "status_pulang", "is_titipan",
                        ]
                        df_clean = pd.DataFrame(data_bersih, columns=kolom_bersih)
                        df_clean = df_clean.dropna(subset=["nama", "no_rm"])
                        df_clean = df_clean.reset_index(drop=True)
                        st.session_state.df_clean = df_clean
                    st.success("✅ Data berhasil dibersihkan!")

                if st.session_state.get("df_clean") is not None:
                    df_clean = st.session_state.df_clean
                    st.dataframe(df_clean.head(), use_container_width=True)
                    excel_buffer = io.BytesIO()
                    df_clean.to_excel(excel_buffer, index=False, engine="openpyxl")
                    nama_file_asli = Path(uploaded.name).stem
                    st.download_button(
                        "Download Excel Bersih",
                        data=excel_buffer.getvalue(),
                        file_name=f"Data_Bersih_{nama_file_asli}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
