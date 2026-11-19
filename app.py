import streamlit as st
import pandas as pd
import io
import json
import hashlib
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    create_client = None
    Client = None
    SUPABASE_AVAILABLE = False

from modules.loader import get_sheet_names, load_sheet_by_name
from modules.cleaner import clean_dataframe_vectorized
from modules.tracker import track_perpindahan
from modules.bor_calculator import hitung_bor, hitung_bor_harian, hitung_rata_rata_bor
from modules.reporter import (
    hitung_statistik_dan_mortalitas, hitung_rl_31, hitung_rl_4a,
    hitung_rekap_penyakit, hitung_rekap_dpjp,
)
from modules.icd_loader import upload_icd_to_supabase, load_kamus_icd, save_kamus_icd
from modules.master_data import (
    MASTER_TT_DEFAULT, MASTER_KELAS_DEFAULT, MASTER_DIHITUNG_BOR_DEFAULT,
    normalisasi_ruang, total_tt_dihitung, load_master_from_supabase,
)


def _dataframe_hash(df):
    values = pd.util.hash_pandas_object(df, index=True).values.tobytes()
    return hashlib.sha256(values).hexdigest()


@st.cache_data(show_spinner=False)
def _cached_track_perpindahan(df_clean, cache_key):
    return track_perpindahan(df_clean)


@st.cache_data(show_spinner=False)
def _cached_hitung_bor(df_long, master_tt, master_flags, periode_awal, periode_akhir):
    return hitung_bor(df_long, master_tt, master_flags,
                      periode_awal=periode_awal, periode_akhir=periode_akhir)


@st.cache_data(show_spinner=False)
def _cached_hitung_bor_harian(df_long, kapasitas_tt, periode_awal, periode_akhir, master_flags):
    return hitung_bor_harian(df_long, kapasitas_tt,
                             periode_awal=periode_awal, periode_akhir=periode_akhir,
                             master_dihitung_bor=master_flags)


@st.cache_data(show_spinner=False)
def _cached_statistics(df_long, cache_key):
    return hitung_statistik_dan_mortalitas(df_long)


@st.cache_data(show_spinner=False)
def _cached_rl31(df_long, cache_key, periode_tahun, periode_bulan):
    return hitung_rl_31(df_long, periode_tahun, periode_bulan)


@st.cache_data(show_spinner=False)
def _cached_rl4a(df_long, cache_key, kamus_icd):
    return hitung_rl_4a(df_long, kamus_icd=kamus_icd)


@st.cache_data(show_spinner=False)
def _cached_excel_bytes(frames, sheet_names, include_indexes):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for frame, sheet_name, include_index in zip(frames, sheet_names, include_indexes):
            frame.to_excel(writer, sheet_name=sheet_name, index=include_index)
    return buffer.getvalue()

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
supabase = None
if SUPABASE_AVAILABLE and create_client is not None:
    try:
        supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception as e:
        st.warning(f"Supabase tidak tersedia; app berjalan dalam mode lokal (data tidak tersimpan ke cloud). Detail: {e}")
else:
    st.warning("Library Supabase tidak tersedia; app berjalan dalam mode lokal (data tidak tersimpan ke cloud).")

st.title(" SIM-RM Helper")
st.caption("Asisten Laporan Rekam Medis — Upload, Olah, Laporkan")
st.markdown("---")

# Periode laporan — WAJIB dari user, jangan ditebak dari data
if "periode_awal" not in st.session_state:
    st.session_state.periode_awal = None
if "periode_akhir" not in st.session_state:
    st.session_state.periode_akhir = None
with st.container(border=True):
    st.write("**Periode Laporan (Wajib)**")
    _c1, _c2 = st.columns(2)
    _p_awal = _c1.date_input("Tanggal awal", value=st.session_state.periode_awal)
    _p_akhir = _c2.date_input("Tanggal akhir", value=st.session_state.periode_akhir)
    if _p_awal and _p_akhir:
        st.session_state.periode_awal = _p_awal
        st.session_state.periode_akhir = _p_akhir
    if not _p_awal or not _p_akhir:
        st.warning("Isi dulu Periode Laporan di atas, BOR / Laporan tidak akan dihitung sebelum periode diisi.")
    elif _p_akhir < _p_awal:
        st.error("Tanggal akhir harus >= tanggal awal.")

# ==========================================
# 2. INITIALIZE SESSION STATE
# ==========================================
if "df_mentah" not in st.session_state: st.session_state.df_mentah = None
if "df_clean" not in st.session_state: st.session_state.df_clean = None
if st.session_state.df_clean is not None and not st.session_state.get('df_clean_hash'):
    st.session_state.df_clean_hash = _dataframe_hash(st.session_state.df_clean)
if 'master_tt' not in st.session_state:
    st.session_state.master_tt = dict(MASTER_TT_DEFAULT)
if 'master_kelas' not in st.session_state:
    st.session_state.master_kelas = dict(MASTER_KELAS_DEFAULT)
if 'master_dihitung_bor' not in st.session_state:
    st.session_state.master_dihitung_bor = dict(MASTER_DIHITUNG_BOR_DEFAULT)

if 'master_tt_loaded' not in st.session_state:
    try:
        load_master_from_supabase(supabase)
    except Exception:
        pass
    st.session_state.master_tt_loaded = True

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
                    df_dash, error_dash = load_sheet_by_name(
                        file_bytes_dash, uploaded_dash.name, selected_sheet_dash
                    )
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
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                c1.write(f"**{ruang}**")
                st.session_state.master_tt[ruang] = c2.number_input(
                    f"TT {ruang}", min_value=0, value=int(tt),
                    label_visibility="collapsed", key=f"tt_{ruang}"
                )
                dihitung_bor = c3.checkbox(
                    "BOR", value=st.session_state.master_dihitung_bor.get(ruang, True),
                    key=f"dihitung_bor_{ruang}", help="Sertakan ruangan ini dalam perhitungan BOR"
                )
                st.session_state.master_dihitung_bor[ruang] = dihitung_bor
                if c4.button("🗑️", key=f"hapus_{ruang}", help="Hapus ruangan"):
                    del st.session_state.master_tt[ruang]
                    st.session_state.master_kelas.pop(ruang, None)
                    st.session_state.master_dihitung_bor.pop(ruang, None)
                    st.rerun()

            st.markdown("---")
            if st.button("💾 Simpan Master TT"):
                data_tt = [
                    {
                        'ruangan': r,
                        'jumlah_tt': tt,
                        'dihitung_bor': st.session_state.master_dihitung_bor.get(r, True),
                        'kelas': st.session_state.master_kelas.get(r, ''),
                    }
                    for r, tt in st.session_state.master_tt.items()
                ]
                try:
                    supabase.table('master_tt').upsert(data_tt, on_conflict='ruangan').execute()
                    st.success('Master TT tersimpan di database!')
                except Exception as e:
                    st.warning(f'Gagal menyimpan Master TT ke Supabase: {e}')
    with st.expander("️ Master Kelas Kamar", expanded=False):
        opsi_kelas = ['VIP', '1', '2', '3', 'HCU', 'ICU', 'NICU', 'PICU', 'Perina', 'Isolasi Normal', 'Isolasi-ICU', 'Transit IGD']
        for nama_ruangan in st.session_state.master_tt:
            kolom_nama_ruangan, kolom_pilih_kelas = st.columns([2, 3])
            kolom_nama_ruangan.write(nama_ruangan)
            nama_lower = nama_ruangan.lower()
            if 'isolasi-icu' in nama_lower:
                kelas_default = 'Isolasi-ICU'
            elif 'hcu' in nama_lower:
                kelas_default = 'HCU'
            elif 'nicu' in nama_lower:
                kelas_default = 'NICU'
            elif 'picu' in nama_lower:
                kelas_default = 'PICU'
            elif 'icu' in nama_lower:
                kelas_default = 'ICU'
            elif 'perina' in nama_lower:
                kelas_default = 'Perina'
            elif 'sakinah' in nama_lower:
                kelas_default = 'Isolasi Normal'
            elif 'firdaus' in nama_lower:
                kelas_default = 'VIP'
            elif 'ar rahmah' in nama_lower:
                kelas_default = '1'
            elif 'safa' in nama_lower:
                kelas_default = '2'
            elif 'marwah' in nama_lower:
                kelas_default = '3'
            elif 'transit' in nama_lower:
                kelas_default = 'Transit IGD'
            else:
                kelas_default = '1'
            kelas_saat_ini = st.session_state.master_kelas.get(nama_ruangan, kelas_default)
            index_kelas = opsi_kelas.index(kelas_saat_ini) if kelas_saat_ini in opsi_kelas else opsi_kelas.index(kelas_default)
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
                            total = upload_icd_to_supabase(uploaded_icd.getvalue(), supabase)
                            st.success(f"✅ {total} kode ICD-10 berhasil di-import!")
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
                    st.session_state.df_clean_hash = _dataframe_hash(st.session_state.df_clean)
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
                df, error = load_sheet_by_name(file_bytes, uploaded.name, selected_sheet)
                
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
                                f_df, f_err = load_sheet_by_name(
                                    f_bytes, file_upload.name, f_sheets[0]
                                )
                                if f_err:
                                    return {}

                                c_rm = next((c for c in f_df.columns if 'rm' in str(c).lower()), None)
                                c_tgl = next((c for c in f_df.columns if ('masuk' if mode == 'prev' else 'keluar') in str(c).lower()), None)

                                res_dict = {}
                                if c_rm and c_tgl:
                                    rms = f_df[c_rm].map(
                                        lambda value: str(value).replace('.0', '').strip()
                                        if pd.notna(value) else ''
                                    )
                                    dates = pd.to_datetime(f_df[c_tgl], errors='coerce')
                                    valid = dates.notna() & ~rms.isin(['', 'None', 'nan'])
                                    res_dict = dict(zip(rms.loc[valid], dates.loc[valid]))
                                return res_dict
                            except Exception:
                                return {}

                        if uploaded_prev:
                            dict_prev = ambil_data_tambahan(uploaded_prev, mode="prev")
                        if uploaded_next:
                            dict_next = ambil_data_tambahan(uploaded_next, mode="next")
                        # ---------------------------------

                        mapping_dict = {
                            'map_nama': map_nama, 'map_jk': map_jk, 'map_rm': map_rm,
                            'map_kamar': map_kamar, 'map_masuk': map_masuk,
                            'map_keluar': map_keluar, 'map_status': map_status,
                            'map_kelas': map_kelas, 'map_diag': map_diag,
                            'map_dokter': map_dokter,
                        }
                        df_clean = clean_dataframe_vectorized(
                            df, mapping_dict, st.session_state.master_kelas,
                            dict_prev=dict_prev, dict_next=dict_next,
                        )
                        st.session_state.df_clean = df_clean
                        st.session_state.df_clean_hash = _dataframe_hash(df_clean)
                        
                        # Otomatis simpan ke Supabase (riwayat_upload)
                        with st.spinner("Menyimpan riwayat upload..."):
                            try:
                                data_json = df_clean.to_json(orient='records', date_format='iso')
                                supabase.table('riwayat_upload').insert({'nama_file': uploaded.name, 'data_json': data_json}).execute()
                                st.success(f"✅ Berhasil memproses {len(df_clean)} baris data dan menyimpannya ke database!")
                            except Exception as e:
                                st.warning(f"Data diproses, tapi gagal simpan ke database: {e}")
                        st.rerun()

    if st.session_state.df_clean is not None:
        with st.container(border=True):
            st.subheader("✅ Preview Data Bersih")
            st.dataframe(st.session_state.df_clean, use_container_width=True)
            if st.button("Siapkan Excel Data Bersih", key="prepare_clean_excel"):
                st.session_state.clean_excel_bytes = _cached_excel_bytes(
                    (st.session_state.df_clean,), ('Data Bersih',), (False,)
                )
                st.session_state.clean_excel_hash = st.session_state.df_clean_hash
            if st.session_state.get('clean_excel_hash') == st.session_state.df_clean_hash:
                st.download_button(
                    "⬇️ Download Data Bersih",
                    data=st.session_state.clean_excel_bytes,
                    file_name="Data_Bersih.xlsx",
                )

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
            df_long = _cached_track_perpindahan(
                st.session_state.df_clean, st.session_state.df_clean_hash
            )
            st.dataframe(df_long, use_container_width=True)

# --- TAB: BOR ---
with tab3:
    st.subheader(" BOR & Indikator")
    if st.session_state.df_clean is None:
        st.info("Silakan upload dan proses data terlebih dahulu.")
    elif st.session_state.periode_awal is None or st.session_state.periode_akhir is None:
        st.warning("Isi dulu Periode Laporan di atas sebelum menghitung BOR.")
    elif st.session_state.periode_akhir < st.session_state.periode_awal:
        st.error("Tanggal akhir harus >= tanggal awal.")
    else:
        with st.container(border=True):
            df_long = _cached_track_perpindahan(
                st.session_state.df_clean, st.session_state.df_clean_hash
            )
            if 'ruang' in df_long.columns:
                df_long['ruang'] = df_long['ruang'].map(normalisasi_ruang)
            master_dihitung_bor_bor = {
                normalisasi_ruang(ruang): value
                for ruang, value in st.session_state.master_dihitung_bor.items()
            }
            df_bor = _cached_hitung_bor(
                df_long, st.session_state.master_tt, master_dihitung_bor_bor,
                st.session_state.periode_awal, st.session_state.periode_akhir,
            )
            
            if not df_bor.empty:
                total = df_bor.iloc[-1]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("BOR RS", f"{total['BOR (%)']}%")
                c2.metric("ALOS", f"{total['ALOS (hari)']} hari")
                c3.metric("TOI", f"{total['TOI (hari)']} hari")
                c4.metric("BTO", f"{total['BTO (kali)']} kali")
                st.markdown("---")
                st.dataframe(df_bor, use_container_width=True, hide_index=True)

            st.subheader(" BOR Harian RS")
            total_tt_aktif = total_tt_dihitung(
                st.session_state.master_tt, st.session_state.master_dihitung_bor
            )
            df_harian = _cached_hitung_bor_harian(
                df_long, total_tt_aktif,
                st.session_state.periode_awal, st.session_state.periode_akhir,
                master_dihitung_bor_bor,
            )
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
    elif st.session_state.periode_awal is None or st.session_state.periode_akhir is None:
        st.warning("Isi dulu Periode Laporan di atas sebelum menghitung laporan.")
    elif st.session_state.periode_akhir < st.session_state.periode_awal:
        st.error("Tanggal akhir harus >= tanggal awal.")
    else:
        df_long = _cached_track_perpindahan(
            st.session_state.df_clean, st.session_state.df_clean_hash
        )
        
        with st.expander(" Laporan Statistik & Mortalitas", expanded=False):
            status_counts, mortalitas_df = _cached_statistics(df_long, st.session_state.df_clean_hash)
            st.dataframe(status_counts, use_container_width=True)
            st.dataframe(mortalitas_df, use_container_width=True)
            if st.button("Siapkan Excel Statistik & Mortalitas", key="prepare_statistik_mortalitas"):
                st.session_state.stat_mortalitas_excel = _cached_excel_bytes(
                    (status_counts, mortalitas_df), ('Statistik', 'Mortalitas'), (False, False)
                )
                st.session_state.stat_mortalitas_excel_hash = st.session_state.df_clean_hash
            if st.session_state.get('stat_mortalitas_excel_hash') == st.session_state.df_clean_hash:
                st.download_button(
                    "⬇️ Download Statistik & Mortalitas (Excel)",
                    data=st.session_state.stat_mortalitas_excel,
                    file_name="Statistik_Mortalitas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_statistik_mortalitas",
                )
            
        with st.expander(" RL 3.1 — Kegiatan Ranap", expanded=False):
            _periode_awal = st.session_state.get('periode_awal')
            _periode_tahun = _periode_awal.year if _periode_awal else None
            _periode_bulan = _periode_awal.month if _periode_awal else None
            df_rl31 = _cached_rl31(
                df_long, st.session_state.df_clean_hash, _periode_tahun, _periode_bulan
            )
            st.dataframe(df_rl31, use_container_width=True)
            if st.button("Siapkan Excel RL 3.1", key="prepare_rl31"):
                st.session_state.rl31_excel = _cached_excel_bytes(
                    (df_rl31,), ('RL 3.1',), (False,)
                )
                st.session_state.rl31_excel_hash = st.session_state.df_clean_hash
            if st.session_state.get('rl31_excel_hash') == st.session_state.df_clean_hash:
                st.download_button(
                    "⬇️ Download RL 3.1 (Excel)",
                    data=st.session_state.rl31_excel,
                    file_name="RL_3.1.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_rl31",
                )
            
        with st.expander(" RL 4a — Morbiditas Rawat Inap & ICD-10", expanded=False):
            if 'kamus_icd' not in st.session_state:
                st.session_state.kamus_icd = load_kamus_icd(supabase)
            kamus = st.session_state.kamus_icd
            df_rl4a = _cached_rl4a(df_long, st.session_state.df_clean_hash, kamus)

            st.markdown("**Pemetaan Kode ICD-10 (Bisa langsung diedit di tabel)**")
            st.info("Silakan ketik/pilih kode ICD-10 langsung di kolom terakhir. Lalu klik tombol Simpan di bawah.")

            if 'Kode ICD-10' not in df_rl4a.columns:
                df_rl4a['Kode ICD-10'] = ""

            # Tampilkan tabel interaktif
            edited_df = st.data_editor(
                df_rl4a,
                column_config={
                    "Kode ICD-10": st.column_config.TextColumn(
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
                df_simpan = edited_df[edited_df['Kode ICD-10'].astype(str).str.strip() != ""]

                berhasil = 0
                for idx, row in df_simpan.iterrows():
                    diag = row['Diagnosa']
                    kode = row['Kode ICD-10']
                    try:
                        save_kamus_icd(supabase, diag, kode)
                        st.session_state.kamus_icd[str(diag).strip()] = str(kode).strip()
                        berhasil += 1
                    except Exception:
                        pass

                st.success(f"✅ {berhasil} pemetaan ICD-10 berhasil disimpan ke database!")
                st.rerun()

        with st.expander('Jumlah Penyakit Terbanyak', expanded=False):
            st.write('Rekapitulasi jumlah pasien per diagnosa, diurutkan dari terbanyak ke tersedikit.')
            rekap_penyakit = hitung_rekap_penyakit(df_long)
            if not rekap_penyakit.empty:
                rekap_penyakit = rekap_penyakit.rename(columns={
                    'jumlah_episode': 'Jumlah Pasien / Jumlah Episode',
                    'jumlah_pasien_unik': 'Jumlah Pasien Unik',
                    'persentase': 'Persentase',
                })
                rekap_penyakit['Persentase'] = rekap_penyakit['Persentase'].map(lambda nilai: f'{nilai:.2f}%')
                rekap_penyakit.index = rekap_penyakit.index + 1
                rekap_penyakit.index.name = 'No'

                total_pasien = rekap_penyakit['Jumlah Pasien / Jumlah Episode'].sum()

                c1, c2, c3 = st.columns(3)
                c1.metric('Total Diagnosa Unik', len(rekap_penyakit))
                c2.metric('Total Pasien', total_pasien)
                c3.metric('Diagnosa Terbanyak', rekap_penyakit.iloc[0]['diagnosa'] if len(rekap_penyakit) > 0 else '-')

                top_n = st.slider('Tampilkan Top N', min_value=1, max_value=min(100, len(rekap_penyakit)), value=min(20, len(rekap_penyakit)), key='slider_penyakit')
                st.dataframe(rekap_penyakit.head(top_n), use_container_width=True)

                st.markdown('**10 Penyakit Terbanyak**')
                top10 = rekap_penyakit.head(10).set_index('diagnosa')['Jumlah Pasien / Jumlah Episode']
                st.bar_chart(top10)

                if st.button('Siapkan Excel Rekap Penyakit', key='prepare_penyakit_excel'):
                    st.session_state.penyakit_excel = _cached_excel_bytes(
                        (rekap_penyakit, rekap_penyakit.head(10)),
                        ('Semua Penyakit', 'Top 10'), (True, True),
                    )
                    st.session_state.penyakit_excel_hash = st.session_state.df_clean_hash
                if st.session_state.get('penyakit_excel_hash') == st.session_state.df_clean_hash:
                    st.download_button(
                        'Download Rekap Penyakit (Excel)',
                        data=st.session_state.penyakit_excel,
                        file_name='Rekap_Penyakit_Terbanyak.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        key='dl_penyakit'
                    )
            else:
                st.warning('Belum ada diagnosa yang dapat direkap.')
        with st.expander(" Rekap Pasien per DPJP (Dokter)", expanded=False):
            st.write("Rekapitulasi jumlah pasien yang ditangani oleh masing-masing dokter.")

            rekap_dpjp = hitung_rekap_dpjp(df_long)
            if not rekap_dpjp.empty:
                st.dataframe(rekap_dpjp, use_container_width=True, hide_index=True)

                if st.button("Siapkan Excel Rekap DPJP", key="prepare_dpjp_excel"):
                    st.session_state.dpjp_excel = _cached_excel_bytes(
                        (rekap_dpjp,), ('Rekap DPJP',), (False,)
                    )
                    st.session_state.dpjp_excel_hash = st.session_state.df_clean_hash
                if st.session_state.get('dpjp_excel_hash') == st.session_state.df_clean_hash:
                    st.download_button(
                        label="⬇️ Download Rekap DPJP (Excel)",
                        data=st.session_state.dpjp_excel,
                        file_name="Rekap_Pasien_DPJP.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_dpjp"
                    )
            else:
                st.warning("Kolom dokter tidak ditemukan atau belum ada dokter untuk direkap. Pastikan sudah di-map di Tab Upload.")
