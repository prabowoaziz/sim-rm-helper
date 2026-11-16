import streamlit as st
import pandas as pd
import io
import json
import hashlib
from supabase import create_client, Client

from modules.loader import get_sheet_names, load_sheet_by_name
from modules.cleaner import clean_nama, split_jk_umur, parse_kamar, clean_kelas
from modules.tracker import track_perpindahan
from modules.bor_calculator import hitung_bor, hitung_bor_harian, hitung_rata_rata_bor
from modules.reporter import hitung_statistik_dan_mortalitas, hitung_rl_31, hitung_rl_4a

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="SIM-RM Helper", page_icon="", layout="wide")

st.markdown("""
<style>
/* Hilangkan toolbar/menu bawaan Streamlit di kanan atas */
header[data-testid="stHeader"],
div[data-testid="stToolbar"],
div[data-testid="stDecoration"],
#MainMenu,
footer {
    display: none !important;
}

/* Memperbesar dan mempertebal teks Tab Navigasi */
.stTabs [data-baseweb="tab"] {
    font-size: 20px !important;
    font-weight: 800 !important;
    color: #1e293b !important;
    padding: 12px 24px !important;
    letter-spacing: 0.5px;
}

/* Warna saat tab aktif (dipilih) */
.stTabs [aria-selected="true"] {
    color: #0ea5e9 !important;
    border-bottom: 4px solid #0ea5e9 !important;
}

/* Memperbesar teks di dalam tabel agar mudah dibaca */
[data-testid="stDataFrame"] {
    font-size: 16px !important;
}

/* CSS untuk Card & Tombol Download Profesional */
.download-card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
}
.download-card h4 {
    margin-top: 0;
    color: #1e293b;
    font-weight: 700;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.stDownloadButton > button {
    background-color: #10b981 !important;
    color: white !important;
    border-radius: 8px !important;
    border: none !important;
    padding: 10px 20px !important;
    font-weight: 600 !important;
    width: 100% !important;
    transition: all 0.2s !important;
}
.stDownloadButton > button:hover {
    background-color: #059669 !important;
    box-shadow: 0 4px 12px rgba(16,185,129,0.3) !important;
}
</style>
""", unsafe_allow_html=True)

# Inisialisasi Supabase (Pastikan di Streamlit Secrets sudah ada url & key)
try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
except Exception as e:
    st.error(f"Gagal koneksi ke Supabase: {e}")

st.title(" SIM-RM Helper")
st.caption("Asisten Laporan Rekam Medis — Upload, Olah, Laporkan")
st.markdown("---")

# ==========================================
# 2. INITIALIZE SESSION STATE
# ==========================================
if "df_mentah" not in st.session_state: st.session_state.df_mentah = None
if "df_clean" not in st.session_state: st.session_state.df_clean = None
if "master_tt" not in st.session_state: st.session_state.master_tt = {"HCU": 6, "ICU": 4, "NICU": 3, "PICU": 2, "Ar Rahmah-1": 10, "Marwah-1": 8, "Kenanga": 10}
if "master_kelas" not in st.session_state: st.session_state.master_kelas = {}

# ==========================================
# 3. TABS
# ==========================================
tab_dash, tab1, tab2, tab3, tab4, tab_master = st.tabs([
    " Dashboard", " Upload", " Mutasi", " BOR", " Laporan", "⚙️ Master Data"
])

# --- TAB: DASHBOARD ---
with tab_dash:
    st.subheader("Ringkasan Operasional RS")
    
    with st.container(border=True):
        st.write("**Unggah Cepat**")
        uploaded_dash = st.file_uploader("Upload data di sini", type=["xlsx", "xls"], key="uploader_dash")
        if uploaded_dash:
            file_bytes_dash = uploaded_dash.getvalue()
            dashboard_hash = hashlib.sha256(
                uploaded_dash.name.encode("utf-8") + b"\0" + file_bytes_dash
            ).hexdigest()
            if dashboard_hash != st.session_state.get("dashboard_loaded_hash"):
                sheet_names_dash = get_sheet_names(file_bytes_dash, uploaded_dash.name)
                if not sheet_names_dash:
                    st.error("Gagal membaca file. Pastikan format file tidak rusak.")
                elif sheet_names_dash[0].startswith("ERROR:"):
                    st.error(f"Gagal membaca file: {sheet_names_dash[0]}")
                else:
                    selected_sheet_dash = sheet_names_dash[0]
                    df_dash, error_dash = load_sheet_by_name(file_bytes_dash, selected_sheet_dash)
                    if error_dash:
                        st.error(f"Gagal membaca file: {error_dash}")
                    else:
                        st.session_state.df_mentah = df_dash
                        st.session_state.nama_file_dash = uploaded_dash.name
                        st.session_state.file_bytes_dash = file_bytes_dash
                        st.session_state.sheet_dash = selected_sheet_dash
                        st.session_state.dashboard_loaded_hash = dashboard_hash
                        st.success("File berhasil dimuat dari Dashboard. Silakan buka Tab Upload untuk memetakan kolom.")

    if st.session_state.df_clean is not None:
        df = st.session_state.df_clean
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Pasien", len(df))
        if 'jenis_kelamin' in df.columns:
            c2.metric("Laki-laki", len(df[df['jenis_kelamin'] == 'L']))
            c3.metric("Perempuan", len(df[df['jenis_kelamin'] == 'P']))
        if 'umur_tahun' in df.columns:
            c4.metric("Rata-rata Umur", f"{df['umur_tahun'].mean():.1f} thn")
        
        with st.container(border=True):
            if 'status_pulang' in df.columns:
                st.bar_chart(df['status_pulang'].value_counts())
    else:
        st.info("Belum ada data.")

# --- TAB: MASTER DATA ---
with tab_master:
    with st.expander("🛏️ Master Tempat Tidur (TT)", expanded=False):
        with st.container(border=True):
            for ruang, tt in list(st.session_state.master_tt.items()):
                col1, col2 = st.columns([3, 1])
                col1.write(f"**{ruang}**")
                st.session_state.master_tt[ruang] = col2.number_input(f"TT {ruang}", min_value=0, value=tt, label_visibility="collapsed", key=f"tt_{ruang}")
            if st.button(" Simpan Master TT"):
                st.success("Master TT disimpan.")

    with st.expander("️ Master Kelas Kamar", expanded=False):
        opsi_kelas = ["VIP", "1", "2", "3", "Khusus (HCU/ICU/NICU/PICU)"]
        for nama_ruangan in st.session_state.master_tt:
            kolom_nama_ruangan, kolom_pilih_kelas = st.columns([2, 3])
            kolom_nama_ruangan.write(nama_ruangan)
            kelas_saat_ini = st.session_state.master_kelas.get(nama_ruangan, "1")
            index_kelas = opsi_kelas.index(kelas_saat_ini) if kelas_saat_ini in opsi_kelas else 1
            pilihan_kelas = kolom_pilih_kelas.selectbox(
                f"Kelas untuk {nama_ruangan}",
                opsi_kelas,
                index=index_kelas,
                key=f"pilih_master_kelas_{nama_ruangan}",
                label_visibility="collapsed",
            )
            st.session_state.master_kelas[nama_ruangan] = pilihan_kelas
        if st.button(" Simpan Master Kelas"):
            st.success("Master Kelas Kamar berhasil disimpan.")

    with st.expander(" Master ICD-10", expanded=False):
        with st.container(border=True):
            uploaded_icd = st.file_uploader("Pilih file ICD-10", type=["xlsx"], key="uploader_icd")
            
            if uploaded_icd:
                if st.button(" Import ICD-10 ke Supabase"):
                    with st.spinner("Mengimpor data ICD-10..."):
                        try:
                            df_icd = pd.read_excel(uploaded_icd)
                            df_icd = df_icd[['CODE', 'DISPLAY', 'VERSION']].dropna()
                            data_icd = df_icd.to_dict('records')
                            for i in range(0, len(data_icd), 500):
                                supabase.table('master_icd').upsert(data_icd[i:i+500], on_conflict='code').execute()
                                
                            st.success(f"✅ Berhasil mengimpor {len(data_icd)} kode ICD-10!")
                        except Exception as e:
                            st.error(f"Gagal import: {e}")

# --- TAB: UPLOAD ---
with tab1:
    st.subheader(" Upload Data Mentah")

    # FITUR MUAT DATA SUPABASE (YANG TADI ILANG)
    with st.container(border=True):
        st.write("**Muat Data dari Sesi Terakhir**")
        if st.button(" Muat Data Terakhir dari Database"):
            try:
                res = supabase.table('riwayat_upload').select('*').order('created_at', desc=True).limit(1).execute()
                if res.data:
                    latest = res.data[0]
                    data_json = latest['data_json']
                    if isinstance(data_json, str):
                        data_json = json.loads(data_json)
                    st.session_state.df_clean = pd.DataFrame(data_json)
                    st.success(f"✅ Berhasil memuat data dari file: {latest['nama_file']}")
                else:
                    st.warning("Belum ada riwayat data.")
            except Exception as e:
                st.error(f"Gagal memuat data: {e}")
    
    with st.container(border=True):
        if st.session_state.df_mentah is not None and not st.session_state.df_mentah.empty:
            st.info(
                f"File aktif saat ini: {st.session_state.get('nama_file_dash', 'Telah dimuat dari Dashboard')}"
            )
            if st.button("Batal / Upload File Baru"):
                st.session_state.df_mentah = None
                st.session_state.pop("nama_file_dash", None)
                st.session_state.pop("file_bytes_dash", None)
                st.session_state.pop("sheet_dash", None)
                st.rerun()
            else:
                uploaded = io.BytesIO(st.session_state.get("file_bytes_dash", b""))
                uploaded.name = st.session_state.get("nama_file_dash", "data_dashboard.xlsx")
        else:
            uploaded = st.file_uploader("Pilih file Excel", type=["xlsx", "xls"])

        if uploaded:
            file_bytes = uploaded.read()
            sheet_names = get_sheet_names(file_bytes, uploaded.name)
            
            if sheet_names:
                selected_sheet = st.selectbox(" Pilih Sheet:", sheet_names) if len(sheet_names) > 1 else sheet_names[0]
                df, error = load_sheet_by_name(file_bytes, selected_sheet)
                
                if error:
                    st.error(f"❌ Error: {error}")
                else:
                    st.success(f"✅ File dimuat: **{uploaded.name}** (Sheet: `{selected_sheet}`)")
                    st.session_state.df_mentah = df
                    st.session_state.nama_file_dash = uploaded.name
                    st.session_state.file_bytes_dash = file_bytes
                    st.session_state.sheet_dash = selected_sheet
                    
                    st.markdown("---")
                    # --- FITUR PREVIEW DATA MENTAH ---
                    with st.expander("️ Lihat Preview Data Mentah (20 Baris Pertama)", expanded=False):
                        st.dataframe(df.head(20), use_container_width=True)
                    # ---------------------------------
                    st.subheader("⚙️ Pemetaan Kolom")
                    kolom_options = ["— Pilih kolom —"] + list(df.columns)
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        map_nama = st.selectbox("Kolom Nama Pasien", kolom_options, index=kolom_options.index('nama_lengkap') if 'nama_lengkap' in kolom_options else 0)
                        map_jk = st.selectbox("Kolom JK/Umur", kolom_options, index=kolom_options.index('_drop_1') if '_drop_1' in kolom_options else 0)
                        map_rm = st.selectbox("Kolom No. RM", kolom_options, index=kolom_options.index('no_rm') if 'no_rm' in kolom_options else 0)
                        map_kamar = st.selectbox("Kolom Kamar", kolom_options, index=kolom_options.index('kamar') if 'kamar' in kolom_options else 0)
                    with c2:
                        map_masuk = st.selectbox("Kolom Tanggal Masuk", kolom_options, index=kolom_options.index('tgl_masuk') if 'tgl_masuk' in kolom_options else 0)
                        map_keluar = st.selectbox("Kolom Tanggal Keluar", kolom_options, index=kolom_options.index('tgl_keluar') if 'tgl_keluar' in kolom_options else 0)
                        map_status = st.selectbox("Kolom Status Pulang", kolom_options, index=kolom_options.index('status_pulang') if 'status_pulang' in kolom_options else 0)
                        map_kelas = st.selectbox("Kolom Kelas Jaminan", kolom_options, index=kolom_options.index('kelas_jaminan') if 'kelas_jaminan' in kolom_options else 0)
                    
                    if st.button(" Proses Data Pasien"):
                        data_bersih = []
                        for idx, row in df.iterrows():
                            raw_nama = row[map_nama] if map_nama != "— Pilih kolom —" else ""
                            raw_jk = row[map_jk] if map_jk != "— Pilih kolom —" else ""
                            
                            nama_bersih = clean_nama(raw_nama)
                            jk, umur = split_jk_umur(f"{raw_nama} {raw_jk}")
                            kode_kamar, ruang, kelas_kamar = parse_kamar(row[map_kamar] if map_kamar != "— Pilih kolom —" else "")
                            raw_kelas = row[map_kelas] if map_kelas != "— Pilih kolom —" else None
                            kelas_dari_master = st.session_state.master_kelas.get(ruang, "Tidak Diketahui")
                            kelas_excel_kosong = (
                                raw_kelas is None
                                or pd.isna(raw_kelas)
                                or not str(raw_kelas).strip()
                            )
                            kelas_jaminan = (
                                kelas_dari_master
                                if kelas_excel_kosong
                                else clean_kelas(raw_kelas)
                            )
                            kelas = kelas_dari_master if kelas_excel_kosong else raw_kelas
                            
                            data_bersih.append({
                                "no_rm": str(row[map_rm]).replace('.0','') if map_rm != "— Pilih kolom —" else None,
                                "nama": nama_bersih,
                                "jenis_kelamin": jk,
                                "umur_tahun": umur,
                                "kode_kamar": kode_kamar,
                                "ruang": ruang,
                                "kelas": kelas,
                                "tgl_masuk": pd.to_datetime(row[map_masuk], errors='coerce') if map_masuk != "— Pilih kolom —" else pd.NaT,
                                "tgl_keluar": pd.to_datetime(row[map_keluar], errors='coerce') if map_keluar != "— Pilih kolom —" else pd.NaT,
                                "status_pulang": row[map_status] if map_status != "— Pilih kolom —" else None,
                                "kelas_jaminan": kelas_jaminan
                            })
                        
                        df_clean = pd.DataFrame(data_bersih).dropna(subset=['nama', 'no_rm'])
                        st.session_state.df_clean = df_clean
                        
                        # Otomatis simpan ke Supabase (riwayat_upload)
                        try:
                            data_json = df_clean.to_json(orient='records', date_format='iso')
                            supabase.table('riwayat_upload').insert({'nama_file': uploaded.name, 'data_json': data_json}).execute()
                            st.success(f"✅ Berhasil memproses {len(df_clean)} baris data dan menyimpannya ke database!")
                        except Exception as e:
                            st.warning(f"Data diproses, tapi gagal simpan ke database: {e}")

    if st.session_state.df_clean is not None:
        with st.container(border=True):
            st.subheader("✅ Preview Data Bersih")
            st.dataframe(st.session_state.df_clean, use_container_width=True)
            
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                st.session_state.df_clean.to_excel(writer, index=False)
            st.download_button("⬇️ Download Data Bersih", data=buf.getvalue(), file_name="Data_Bersih.xlsx")

        st.markdown("---")
        st.markdown("###  Download Laporan Per Kamar")

        # Logika pengelompokan ruangan
        df_clean = st.session_state.df_clean
        if 'ruang' in df_clean.columns and not df_clean['ruang'].isna().all():
            kategori_kamar = df_clean['ruang'].dropna().unique()

            # Tampilkan dalam bentuk Grid (2 Kolom)
            cols = st.columns(2)
            for i, kamar in enumerate(kategori_kamar):
                df_kamar = df_clean[df_clean['ruang'] == kamar]
                jumlah = len(df_kamar)

                # Buat file Excel di memori
                buf_kamar = io.BytesIO()
                with pd.ExcelWriter(buf_kamar, engine='openpyxl') as writer:
                    df_kamar.to_excel(writer, index=False)

                # Tampilan Card Profesional
                with cols[i % 2]:
                    st.markdown(f'''
                    <div class="download-card">
                        <h4> Kamar: {kamar}</h4>
                        <p style="color:#64748b; font-size:14px; margin-bottom:10px;">Total: {jumlah} Pasien</p>
                    ''', unsafe_allow_html=True)

                    st.download_button(
                        label=f"⬇️ Download Excel ({kamar})",
                        data=buf_kamar.getvalue(),
                        file_name=f"Data_{kamar}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_{kamar}"
                    )
                    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB: MUTASI ---
with tab2:
    st.subheader(" Track Perpindahan Kamar")
    if st.session_state.df_clean is None:
        st.info("Silakan upload dan proses data terlebih dahulu.")
    else:
        with st.container(border=True):
            df_long = track_perpindahan(st.session_state.df_clean)
            st.dataframe(df_long, use_container_width=True)

# --- TAB: BOR ---
with tab3:
    st.subheader(" BOR & Indikator")
    if st.session_state.df_clean is None:
        st.info("Silakan upload dan proses data terlebih dahulu.")
    else:
        with st.container(border=True):
            df_long = track_perpindahan(st.session_state.df_clean)
            df_bor = hitung_bor(df_long, st.session_state.master_tt)
            
            if not df_bor.empty:
                total = df_bor.iloc[-1]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("BOR RS", f"{total['BOR (%)']}%")
                c2.metric("ALOS", f"{total['ALOS (hari)']} hari")
                c3.metric("TOI", f"{total['TOI (hari)']} hari")
                c4.metric("BTO", f"{total['BTO (kali)']} kali")
                st.markdown("---")
                st.dataframe(df_bor, use_container_width=True, hide_index=True)

            st.subheader(" BOR RPA/RPM (Kapasitas 35 TT)")
            df_harian = hitung_bor_harian(df_long, kapasitas_tt=35)
            rata_rata = hitung_rata_rata_bor(df_harian)
            st.metric("Rata-rata BOR Harian", f"{rata_rata}%")
            st.dataframe(df_harian, use_container_width=True)
            if not df_harian.empty:
                st.line_chart(df_harian.set_index('tanggal')['bor_persen'])

# --- TAB: LAPORAN ---
with tab4:
    st.subheader(" Laporan RL & Akreditasi")
    if st.session_state.df_clean is None:
        st.info("Silakan upload dan proses data terlebih dahulu.")
    else:
        df_long = track_perpindahan(st.session_state.df_clean)
        
        with st.expander(" Laporan Statistik & Mortalitas", expanded=False):
            status_counts, mortalitas_df = hitung_statistik_dan_mortalitas(df_long)
            st.dataframe(status_counts, use_container_width=True)
            st.dataframe(mortalitas_df, use_container_width=True)
            buf_stat_mortalitas = io.BytesIO()
            with pd.ExcelWriter(buf_stat_mortalitas, engine='openpyxl') as writer:
                status_counts.to_excel(writer, sheet_name="Statistik", index=False)
                mortalitas_df.to_excel(writer, sheet_name="Mortalitas", index=False)
            st.download_button(
                "⬇️ Download Statistik & Mortalitas (Excel)",
                data=buf_stat_mortalitas.getvalue(),
                file_name="Statistik_Mortalitas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_statistik_mortalitas",
            )
            
        with st.expander(" RL 3.1 — Kegiatan Ranap", expanded=False):
            df_rl31 = hitung_rl_31(df_long)
            st.dataframe(df_rl31, use_container_width=True)
            buf_rl31 = io.BytesIO()
            with pd.ExcelWriter(buf_rl31, engine='openpyxl') as writer:
                df_rl31.to_excel(writer, index=False)
            st.download_button(
                "⬇️ Download RL 3.1 (Excel)",
                data=buf_rl31.getvalue(),
                file_name="RL_3.1.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_rl31",
            )
            
        with st.expander(" RL 4a — Morbiditas Rawat Inap & ICD-10", expanded=False):
            st.write("**Pemetaan Kode ICD-10 (Manual & Otomatis)**")
            c_left, c_right = st.columns(2)
            
            with c_left:
                st.write("**Manual**")
                manual_diag = st.text_input("Diagnosa SIMRS (Ketik Manual)", key="manual_diag")
                manual_kode = st.text_input("Kode ICD-10 (Ketik Manual)", key="manual_kode")
                if st.button(" Simpan Pemetaan Manual"):
                    if manual_diag and manual_kode:
                        try:
                            supabase.table('kamus_icd').upsert({'diagnosa_simrs': manual_diag, 'kode_icd': manual_kode}, on_conflict='diagnosa_simrs').execute()
                            st.success("Pemetaan manual berhasil disimpan!")
                        except Exception as e:
                            st.error(f"Gagal simpan: {e}")
                            
            with c_right:
                st.write("**Otomatis (Cari di Kamus)**")
                search_icd = st.text_input("Cari Diagnosa di Kamus ICD-10", key="search_icd")
                st.caption("Ketik nama penyakit (misal: Dengue) atau kode ICD-10 (misal: A91).")
                search_term = search_icd.strip()
                if search_term:
                    try:
                        res = (
                            supabase.table('master_icd')
                            .select('code', 'display')
                            .or_(f'code.ilike.%{search_term}%,display.ilike.%{search_term}%')
                            .limit(10)
                            .execute()
                        )
                        if res.data:
                            opsi_icd = [f"{r['code']} - {r['display']}" for r in res.data]
                            pilih_icd = st.selectbox("Pilih kode yang sesuai:", opsi_icd)
                            if st.button("Gunakan Kode Otomatis Ini"):
                                st.info(f"Kode {pilih_icd.split(' - ')[0]} siap digunakan (Fitur ini opsional untuk melengkapi tabel).")
                        else:
                            st.warning("Diagnosa tidak ditemukan di kamus.")
                    except Exception as e:
                        st.error(f"Gagal mencari: {e}")

            df_rl4a = hitung_rl_4a(df_long)
            st.dataframe(df_rl4a, use_container_width=True)
            buf_rl4a = io.BytesIO()
            with pd.ExcelWriter(buf_rl4a, engine='openpyxl') as writer:
                df_rl4a.to_excel(writer, index=False)
            st.download_button(
                "⬇️ Download RL 4a (Excel)",
                data=buf_rl4a.getvalue(),
                file_name="RL_4a.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_rl4a",
            )
