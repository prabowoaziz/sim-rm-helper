import streamlit as st
import pandas as pd
import io

# Import modul internal
from modules.loader import get_sheet_names, load_sheet_by_name
from modules.cleaner import clean_nama, split_jk_umur, parse_kamar, clean_kelas
from modules.tracker import track_perpindahan
from modules.bor_calculator import hitung_bor
from modules.reporter import hitung_statistik_dan_mortalitas, hitung_rl_31, hitung_rl_4a

# ==========================================
# 1. KONFIGURASI HALAMAN & CSS (PAKSA SIDEBAR)
# ==========================================
st.set_page_config(
    page_title="SIM-RM Helper",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f4f6f8; }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* PAKSA SIDEBAR MUNCUL */
    [data-testid="stSidebar"] {
        display: block !important;
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
        box-shadow: 2px 0 10px rgba(0,0,0,0.03);
        min-width: 280px !important;
        padding-top: 20px;
    }
    
    /* Styling Radio Button di Sidebar */
    [data-testid="stSidebar"] .stRadio > div { gap: 4px; }
    [data-testid="stSidebar"] .stRadio label {
        padding: 12px 16px; border-radius: 10px; font-weight: 600;
        color: #64748b; width: 100%; transition: all 0.2s; cursor: pointer;
    }
    [data-testid="stSidebar"] .stRadio label:hover { background-color: #f8fafc; color: #1e293b; }
    [data-testid="stSidebar"] .stRadio div[aria-checked="true"] label {
        background-color: #e0f2fe; color: #0284c7;
    }

    /* Container Card (Kotak Putih) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff; border: 1px solid #e2e8f0 !important;
        border-radius: 16px; padding: 24px !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02); margin-bottom: 24px;
    }
    
    /* Metrics */
    div[data-testid="stMetric"] {
        background-color: #ffffff; border: 1px solid #e2e8f0;
        border-top: 4px solid #0ea5e9; padding: 20px; border-radius: 12px;
    }
    
    /* Tombol Biru */
    .stButton > button {
        background-color: #0ea5e9; color: white; border-radius: 10px;
        border: none; padding: 12px 24px; font-weight: 600; width: 100%;
    }
    .stButton > button:hover { background-color: #0284c7; color: white; }
    
    /* Tombol Hijau (Download) */
    .stDownloadButton > button {
        background-color: #10b981; color: white; border-radius: 10px;
        border: none; font-weight: 600; padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. INITIALIZE SESSION STATE
# ==========================================
if "df_mentah" not in st.session_state: st.session_state.df_mentah = None
if "df_clean" not in st.session_state: st.session_state.df_clean = None
if "master_tt" not in st.session_state: st.session_state.master_tt = {"HCU": 6, "ICU": 4, "NICU": 3, "PICU": 2, "Ar Rahmah-1": 10, "Marwah-1": 8, "Kenanga": 10}

# ==========================================
# 3. SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color:#0ea5e9; font-weight:700; margin-bottom:20px;'>🏥 SIM-RM Helper</h2>", unsafe_allow_html=True)
    menu = st.radio(
        "Navigasi Menu",
        ["🏠 Dashboard", "📤 Upload Data", "🔁 Perpindahan Kamar", "🏥 BOR & Indikator", "📊 Laporan RL & Akreditasi", "⚙️ Master Data"]
    )
    st.markdown("---")
    st.caption("© 2026 SIM-RM Helper.")

# ==========================================
# 4. KONTEN SETIAP MENU
# ==========================================

# --- MENU: DASHBOARD ---
if menu == "🏠 Dashboard":
    st.title("🏠 Dashboard")
    st.caption("Ringkasan operasional Rekam Medis")
    
    with st.container(border=True):
        st.subheader("Unggah Cepat")
        uploaded_dash = st.file_uploader("Unggah data SIMRS di sini", type=["xlsx", "xls"], key="uploader_dash")
        if uploaded_dash:
            st.info("File diterima. Silakan buka menu '📤 Upload Data' di kiri untuk proses pemetaan.")

    if st.session_state.df_clean is not None:
        df = st.session_state.df_clean
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Pasien", len(df))
        if 'jenis_kelamin' in df.columns:
            col2.metric("Laki-laki", len(df[df['jenis_kelamin'] == 'L']))
            col3.metric("Perempuan", len(df[df['jenis_kelamin'] == 'P']))
        if 'umur_tahun' in df.columns:
            col4.metric("Rata-rata Umur", f"{df['umur_tahun'].mean():.1f} thn")
        
        with st.container(border=True):
            st.subheader("Distribusi Status Pulang")
            if 'status_pulang' in df.columns:
                st.bar_chart(df['status_pulang'].value_counts())
    else:
        st.info("Belum ada data. Silakan unggah melalui menu Upload Data.")

# --- MENU: UPLOAD DATA ---
elif menu == "📤 Upload Data":
    st.title("📤 Upload Data SIMRS")
    st.caption("Unggah file Excel mentah, lakukan pemetaan, lalu proses data.")
    
    with st.container(border=True):
        uploaded = st.file_uploader("Pilih file Excel", type=["xlsx", "xls"])
        if uploaded:
            file_bytes = uploaded.read()
            sheet_names = get_sheet_names(file_bytes, uploaded.name)
            
            if sheet_names:
                selected_sheet = st.selectbox("📑 Pilih Sheet:", sheet_names) if len(sheet_names) > 1 else sheet_names[0]
                df, error = load_sheet_by_name(file_bytes, selected_sheet)
                
                if error:
                    st.error(f"❌ Error: {error}")
                else:
                    st.success(f"✅ File dimuat: **{uploaded.name}** (Sheet: `{selected_sheet}`)")
                    st.session_state.df_mentah = df
                    
                    st.markdown("---")
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
                    
                    if st.button("🚀 Proses Data Pasien"):
                        data_bersih = []
                        for idx, row in df.iterrows():
                            raw_nama = row[map_nama] if map_nama != "— Pilih kolom —" else ""
                            raw_jk = row[map_jk] if map_jk != "— Pilih kolom —" else ""
                            
                            nama_bersih = clean_nama(raw_nama)
                            jk, umur = split_jk_umur(f"{raw_nama} {raw_jk}")
                            kode_kamar, ruang, kelas_kamar = parse_kamar(row[map_kamar] if map_kamar != "— Pilih kolom —" else "")
                            
                            data_bersih.append({
                                "no_rm": str(row[map_rm]).replace('.0','') if map_rm != "— Pilih kolom —" else None,
                                "nama": nama_bersih,
                                "jenis_kelamin": jk,
                                "umur_tahun": umur,
                                "kode_kamar": kode_kamar,
                                "ruang": ruang,
                                "tgl_masuk": pd.to_datetime(row[map_masuk], errors='coerce') if map_masuk != "— Pilih kolom —" else pd.NaT,
                                "tgl_keluar": pd.to_datetime(row[map_keluar], errors='coerce') if map_keluar != "— Pilih kolom —" else pd.NaT,
                                "status_pulang": row[map_status] if map_status != "— Pilih kolom —" else None,
                                "kelas_jaminan": clean_kelas(row[map_kelas]) if map_kelas != "— Pilih kolom —" else "Tidak Diketahui"
                            })
                        
                        df_clean = pd.DataFrame(data_bersih).dropna(subset=['nama', 'no_rm'])
                        st.session_state.df_clean = df_clean
                        st.success(f"✅ Berhasil memproses {len(df_clean)} baris data!")

    if st.session_state.df_clean is not None:
        with st.container(border=True):
            st.subheader("✅ Preview Data Bersih")
            st.dataframe(st.session_state.df_clean, use_container_width=True)
            
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                st.session_state.df_clean.to_excel(writer, index=False)
            st.download_button("⬇️ Download Data Bersih (Excel)", data=buf.getvalue(), file_name="Data_Bersih.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- MENU: PERPINDAHAN KAMAR ---
elif menu == "🔁 Perpindahan Kamar":
    st.title("🔁 Track Perpindahan Kamar")
    if st.session_state.df_clean is None:
        st.info("Silakan upload dan proses data di menu Upload Data terlebih dahulu.")
    else:
        with st.container(border=True):
            df_long = track_perpindahan(st.session_state.df_clean)
            st.dataframe(df_long, use_container_width=True)

# --- MENU: BOR & INDIKATOR ---
elif menu == "🏥 BOR & Indikator":
    st.title("🏥 BOR & Indikator")
    if st.session_state.df_clean is None:
        st.info("Silakan upload dan proses data di menu Upload Data terlebih dahulu.")
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

# --- MENU: LAPORAN ---
elif menu == "📊 Laporan RL & Akreditasi":
    st.title("📊 Laporan RL & Akreditasi")
    if st.session_state.df_clean is None:
        st.info("Silakan upload dan proses data di menu Upload Data terlebih dahulu.")
    else:
        df_long = track_perpindahan(st.session_state.df_clean)
        
        with st.expander("📈 Laporan Statistik & Mortalitas", expanded=False):
            status_counts, mortalitas_df = hitung_statistik_dan_mortalitas(df_long)
            st.dataframe(status_counts, use_container_width=True)
            st.dataframe(mortalitas_df, use_container_width=True)
            
        with st.expander("📋 RL 3.1 — Kegiatan Ranap", expanded=False):
            df_rl31 = hitung_rl_31(df_long)
            st.dataframe(df_rl31, use_container_width=True)
            
        with st.expander("📋 RL 4a — Morbiditas Rawat Inap", expanded=False):
            df_rl4a = hitung_rl_4a(df_long)
            st.dataframe(df_rl4a, use_container_width=True)

# --- MENU: MASTER DATA ---
elif menu == "⚙️ Master Data":
    st.title("⚙️ Master Data")
    
    with st.container(border=True):
        st.subheader("🛏️ Master Tempat Tidur (TT)")
        for ruang, tt in list(st.session_state.master_tt.items()):
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{ruang}**")
            st.session_state.master_tt[ruang] = col2.number_input(f"TT {ruang}", min_value=0, value=tt, label_visibility="collapsed")
        if st.button("💾 Simpan Master TT"):
            st.success("Master TT berhasil disimpan.")

    with st.container(border=True):
        st.subheader("🏥 Master ICD-10")
        st.info("Fitur import kamus ICD-10 tersedia di sini.")
