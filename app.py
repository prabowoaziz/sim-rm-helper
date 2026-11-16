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

/* Card untuk Merge Lintas Bulan */
.merge-card {
    background-color: #f8fafc;
    border: 1px dashed #cbd5e1;
    border-radius: 10px;
    padding: 16px;
    margin-top: 10px;
    margin-bottom: 10px;
}
.merge-card h4 {
    margin-top: 0;
    color: #0ea5e9;
    font-size: 15px;
    display: flex;
    align-items: center;
    gap: 8px;
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
if "master_grup_kamar" not in st.session_state: st.session_state.master_grup_kamar = {"RPA": [], "RPM": []}

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
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"**{ruang}**")
                st.session_state.master_tt[ruang] = c2.number_input(f"TT {ruang}", min_value=0, value=tt, label_visibility="collapsed", key=f"tt_{ruang}")

                # Tombol Hapus
                if c3.button("️ Hapus", key=f"hapus_{ruang}"):
                    del st.session_state.master_tt[ruang]
                    # Hapus juga dari master_kelas jika ada
                    if ruang in st.session_state.master_kelas:
                        del st.session_state.master_kelas[ruang]
                    st.rerun() # Refresh halaman agar baris langsung hilang

            st.markdown("---")
            c_add1, c_add2 = st.columns([3, 1])
            new_ruang = c_add1.text_input("Tambah Kamar Baru", placeholder="Nama Kamar Baru...")
            if c_add2.button("➕ Tambah"):
                if new_ruang and new_ruang not in st.session_state.master_tt:
                    st.session_state.master_tt[new_ruang] = 0
                    st.rerun()
                elif new_ruang in st.session_state.master_tt:
                    st.warning("Kamar sudah ada!")
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

    with st.expander(" Pengelompokan Kamar (RPA/RPM)", expanded=False):
        st.write("Tentukan kamar mana saja yang masuk ke dalam grup RPA dan RPM.")

        # Ambil semua nama ruangan dari master_tt
        semua_ruangan = list(st.session_state.master_tt.keys())

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Grup RPA**")
            st.session_state.master_grup_kamar["RPA"] = st.multiselect(
                "Pilih kamar untuk RPA:",
                semua_ruangan,
                default=st.session_state.master_grup_kamar.get("RPA", [])
            )

        with c2:
            st.markdown("**Grup RPM**")
            st.session_state.master_grup_kamar["RPM"] = st.multiselect(
                "Pilih kamar untuk RPM:",
                semua_ruangan,
                default=st.session_state.master_grup_kamar.get("RPM", [])
            )

        if st.button(" Simpan Pengelompokan Kamar"):
            st.success("Pengelompokan Kamar (RPA/RPM) berhasil disimpan!")

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
            uploaded = st.file_uploader("Pilih file Excel (File Utama)", type=["xlsx", "xls"])

        st.markdown("""
        <div class="merge-card">
            <h4> Opsional: Merge Data Lintas Bulan</h4>
            <p style="font-size:13px; color:#64748b; margin-bottom:0;">
                Upload file bulan lalu dan/atau bulan depan jika ada pasien yang dirawat lintas bulan (misal: masuk September, pulang November).
            </p>
        </div>
        """, unsafe_allow_html=True)

        c_merge1, c_merge2 = st.columns(2)
        with c_merge1:
            uploaded_prev = st.file_uploader(" File Bulan Lalu (Opsional)", type=["xlsx", "xls"], key="upload_prev")
        with c_merge2:
            uploaded_next = st.file_uploader(" File Bulan Depan (Opsional)", type=["xlsx", "xls"], key="upload_next")

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
                        default_diag = next((c for c in df.columns if 'diag' in str(c).lower() or 'penyakit' in str(c).lower()), kolom_options[0])
                        map_diag = st.selectbox("Kolom Diagnosa (Penyakit)", kolom_options, index=kolom_options.index(default_diag) if default_diag in kolom_options else 0)
                        # Deteksi otomatis kolom dokter
                        default_dokter = next((c for c in df.columns if 'dokter' in str(c).lower() or 'dpjp' in str(c).lower()), kolom_options[0])
                        map_dokter = st.selectbox("Kolom Dokter (DPJP)", kolom_options, index=kolom_options.index(default_dokter) if default_dokter in kolom_options else 0)
                    
                    if st.button(" Proses Data Pasien"):
                        # --- LOGIKA MERGE LINTAS BULAN ---
                        dict_prev = {} # {no_rm: tgl_masuk}
                        dict_next = {} # {no_rm: tgl_keluar}

                        def ambil_data_tambahan(file_upload, mode="prev"):
                            if not file_upload:
                                return {}
                            try:
                                f_bytes = file_upload.getvalue()
                                f_sheets = get_sheet_names(f_bytes, file_upload.name)
                                if not f_sheets or f_sheets[0].startswith("ERROR:"):
                                    return {}
                                f_df, f_err = load_sheet_by_name(f_bytes, f_sheets[0])
                                if f_err:
                                    return {}

                                c_rm = next((c for c in f_df.columns if 'rm' in str(c).lower()), None)
                                c_tgl = next((c for c in f_df.columns if ('masuk' if mode == 'prev' else 'keluar') in str(c).lower()), None)

                                res_dict = {}
                                if c_rm and c_tgl:
                                    for _, r in f_df.iterrows():
                                        rm_value = r[c_rm]
                                        rm = str(rm_value).replace('.0', '').strip() if pd.notna(rm_value) else ""
                                        tgl = pd.to_datetime(r[c_tgl], errors='coerce')
                                        if pd.notna(tgl) and rm not in ["", "None", "nan"]:
                                            res_dict[rm] = tgl
                                return res_dict
                            except Exception:
                                return {}

                        if uploaded_prev:
                            dict_prev = ambil_data_tambahan(uploaded_prev, mode="prev")
                        if uploaded_next:
                            dict_next = ambil_data_tambahan(uploaded_next, mode="next")
                        # ---------------------------------

                        data_bersih = []

                        for idx, row in df.iterrows():
                            raw_nama = row[map_nama] if map_nama != "— Pilih kolom —" else ""
                            raw_jk = row[map_jk] if map_jk != "— Pilih kolom —" else ""
                            # Ambil RM dan Tanggal dari file UTAMA
                            rm_utama = str(row[map_rm]).replace('.0', '').strip() if map_rm != "— Pilih kolom —" else None

                            tgl_masuk_utama = pd.to_datetime(row[map_masuk], errors='coerce') if map_masuk != "— Pilih kolom —" else pd.NaT
                            if pd.isna(tgl_masuk_utama) and rm_utama in dict_prev:
                                tgl_masuk_final = dict_prev[rm_utama]
                            else:
                                tgl_masuk_final = tgl_masuk_utama

                            tgl_keluar_utama = pd.to_datetime(row[map_keluar], errors='coerce') if map_keluar != "— Pilih kolom —" else pd.NaT
                            if pd.isna(tgl_keluar_utama) and rm_utama in dict_next:
                                tgl_keluar_final = dict_next[rm_utama]
                            else:
                                tgl_keluar_final = tgl_keluar_utama
                            no_rm = rm_utama if rm_utama not in (None, "None", "nan") else None
                            
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
                                "no_rm": no_rm,
                                "nama": nama_bersih,
                                "jenis_kelamin": jk,
                                "umur_tahun": umur,
                                "kode_kamar": kode_kamar,
                                "ruang": ruang,
                                "kelas": kelas,
                                "tgl_masuk": tgl_masuk_final,
                                "tgl_keluar": tgl_keluar_final,
                                "status_pulang": row[map_status] if map_status != "— Pilih kolom —" else None,
                                "kelas_jaminan": kelas_jaminan,
                                "diagnosa": str(row[map_diag]).strip() if map_diag != "— Pilih kolom —" else "Tidak Ada Diagnosa",
                                "dokter": row[map_dokter] if map_dokter != "— Pilih kolom —" else None,
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
        st.markdown("###  Download Laporan Per Kamar (Multi-Sheet)")
        st.write("Unduh semua data pasien yang dipisah rapi berdasarkan ruangannya ke dalam 1 file Excel.")

        df_clean = st.session_state.df_clean
        if 'ruang' in df_clean.columns and not df_clean['ruang'].isna().all():
            if st.button(" Generate Laporan Per Kamar (Excel)"):
                with st.spinner("Menyiapkan file per kamar..."):
                    buf_kamar = io.BytesIO()
                    with pd.ExcelWriter(buf_kamar, engine='openpyxl') as writer:
                        # Looping setiap ruangan untuk dijadikan sheet
                        for ruang in df_clean['ruang'].dropna().unique():
                            df_ruang = df_clean[df_clean['ruang'] == ruang]
                            # Beri nama sheet maksimal 31 karakter (batas Excel)
                            nama_sheet = str(ruang)[:31]
                            df_ruang.to_excel(writer, sheet_name=nama_sheet, index=False)

                    st.download_button(
                        label="⬇️ Download Semua Kamar (1 File Excel)",
                        data=buf_kamar.getvalue(),
                        file_name="Data_Pasien_Per_Kamar.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_per_kamar_multi"
                    )
        else:
            st.warning("Kolom 'ruang' tidak ditemukan atau kosong.")

        st.markdown("---")
        st.markdown("###  Rekap Pasien Harian (Multi-Sheet)")

        # Ambil bulan dan tahun dari data (asumsi berdasarkan data pertama)
        df_clean = st.session_state.df_clean
        if 'tgl_masuk' in df_clean.columns and df_clean['tgl_masuk'].notna().any():
            # Tentukan bulan & tahun
            df_clean['tgl_masuk'] = pd.to_datetime(df_clean['tgl_masuk'])
            bulan_tahun = df_clean['tgl_masuk'].dt.strftime('%B %Y').mode()[0]
            st.info(f" Sistem mendeteksi data untuk periode: **{bulan_tahun}**")

            if st.button(" Generate Rekap Harian (Excel)"):
                with st.spinner("Menyiapkan file multi-sheet..."):
                    buf_harian = io.BytesIO()

                    with pd.ExcelWriter(buf_harian, engine='openpyxl') as writer:
                        # 1. Sheet Utama (Semua Pasien)
                        df_urut = df_clean.sort_values(by='tgl_masuk')
                        df_urut.to_excel(writer, sheet_name="Semua Pasien", index=False)

                        # 2. Sheet Per Tanggal
                        # Ambil unik tanggal (hanya tanggal, tanpa jam)
                        unik_tanggal = df_urut['tgl_masuk'].dt.date.dropna().unique()

                        for tgl in sorted(unik_tanggal):
                            df_tgl = df_urut[df_urut['tgl_masuk'].dt.date == tgl]
                            # Format nama sheet: "1", "2", "3", dst (sesuai tanggal)
                            nama_sheet = f"{tgl.day}"
                            df_tgl.to_excel(writer, sheet_name=nama_sheet, index=False)

                    # Tombol Download
                    st.download_button(
                        label="⬇️ Download Rekap Harian (Excel Multi-Sheet)",
                        data=buf_harian.getvalue(),
                        file_name=f"Rekap_Pasien_Harian_{bulan_tahun.replace(' ', '_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_harian"
                    )
        else:
            st.warning("Kolom tanggal masuk tidak ditemukan atau kosong. Pastikan pemetaan tanggal sudah benar.")

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
            # Ambil data RL 4a dari fungsi yang sudah ada
            df_rl4a = hitung_rl_4a(df_long)

            st.markdown("**Pemetaan Kode ICD-10 (Bisa langsung diedit di tabel)**")
            st.info("Silakan ketik/pilih kode ICD-10 langsung di kolom terakhir. Lalu klik tombol Simpan di bawah.")

            # Pastikan ada kolom Kode ICD di dataframe (jika belum ada, buat kosong)
            if 'Kode ICD' not in df_rl4a.columns:
                df_rl4a['Kode ICD'] = ""

            # Tampilkan tabel interaktif
            edited_df = st.data_editor(
                df_rl4a,
                column_config={
                    "Kode ICD": st.column_config.TextColumn(
                        "Kode ICD-10",
                        help="Ketik kode di sini (misal: A91)",
                        max_chars=10,
                    )
                },
                use_container_width=True,
                hide_index=True,
                key="editor_icd"
            )

            # Tombol Simpan ke Database
            if st.button(" Simpan Pemetaan ICD dari Tabel"):
                # Ambil data yang berubah (yang ada Kode ICD-nya)
                df_simpan = edited_df[edited_df['Kode ICD'] != ""]

                berhasil = 0
                for idx, row in df_simpan.iterrows():
                    diag = row['Diagnosa']
                    kode = row['Kode ICD']
                    try:
                        supabase.table('kamus_icd').upsert({'diagnosa_simrs': diag, 'kode_icd': kode}, on_conflict='diagnosa_simrs').execute()
                        berhasil += 1
                    except Exception:
                        pass

                st.success(f"✅ {berhasil} pemetaan ICD-10 berhasil disimpan ke database!")
                st.rerun()

        with st.expander(" Rekap Pasien per DPJP (Dokter)", expanded=False):
            st.write("Rekapitulasi jumlah pasien yang ditangani oleh masing-masing dokter.")

            df_clean = st.session_state.df_clean
            if 'dokter' in df_clean.columns:
                rekap_dpjp = df_clean.groupby('dokter')['no_rm'].nunique().reset_index()
                rekap_dpjp.columns = ['Nama Dokter (DPJP)', 'Jumlah Pasien Unik']
                rekap_dpjp = rekap_dpjp.sort_values(by='Jumlah Pasien Unik', ascending=False)

                # Hapus baris yang dokternya kosong (NaN)
                rekap_dpjp = rekap_dpjp.dropna(subset=['Nama Dokter (DPJP)'])

                st.dataframe(rekap_dpjp, use_container_width=True, hide_index=True)

                # Tombol Download
                buf_dpjp = io.BytesIO()
                with pd.ExcelWriter(buf_dpjp, engine='openpyxl') as writer:
                    rekap_dpjp.to_excel(writer, index=False)

                st.download_button(
                    label="⬇️ Download Rekap DPJP (Excel)",
                    data=buf_dpjp.getvalue(),
                    file_name="Rekap_Pasien_DPJP.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_dpjp"
                )
            else:
                st.warning("Kolom dokter tidak ditemukan. Pastikan sudah di-map di Tab Upload.")
