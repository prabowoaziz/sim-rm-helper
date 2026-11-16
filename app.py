import streamlit as st
import pandas as pd
import io
import json
from supabase import create_client, Client

from modules.loader import get_sheet_names, load_sheet_by_name
from modules.cleaner import clean_nama, split_jk_umur, parse_kamar, clean_kelas
from modules.tracker import track_perpindahan
from modules.bor_calculator import hitung_bor, hitung_bor_harian, hitung_rata_rata_bor
from modules.reporter import hitung_statistik_dan_mortalitas, hitung_rl_31, hitung_rl_4a

st.set_page_config(page_title="SIM-RM Helper", page_icon="🏥", layout="wide")

# --- CSS TAMPILAN ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f4f6f8; }
    
    /* Perbesar & Pertebal Teks Tab */
    .stTabs [data-baseweb="tab"] {
        font-size: 18px !important;
        font-weight: 800 !important;
        color: #1e293b !important;
        padding: 10px 20px !important;
    }
    .stTabs [aria-selected="true"] {
        color: #0ea5e9 !important;
        border-bottom: 4px solid #0ea5e9 !important;
    }
    
    /* Tombol & Card */
    .stButton > button {
        background-color: #0ea5e9; color: white; border-radius: 8px;
        border: none; padding: 10px 20px; font-weight: 600; width: 100%;
    }
    .stButton > button:hover { background-color: #0284c7; color: white; }
    .stDownloadButton > button {
        background-color: #10b981; color: white; border-radius: 8px;
        border: none; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- INIT SUPABASE & STATE ---
try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
except Exception as e:
    st.error(f"Gagal koneksi Supabase: {e}")

if "df_mentah" not in st.session_state: st.session_state.df_mentah = None
if "df_clean" not in st.session_state: st.session_state.df_clean = None
if "master_tt" not in st.session_state: st.session_state.master_tt = {"HCU": 6, "ICU": 4, "NICU": 3, "PICU": 2, "Ar Rahmah-1": 10, "Marwah-1": 8, "Kenanga": 10}
if "master_kelas" not in st.session_state: st.session_state.master_kelas = {}

st.title("🏥 SIM-RM Helper")
st.caption("Asisten Laporan Rekam Medis")
st.markdown("---")

# --- TABS URUTAN BARU ---
tab_dash, tab1, tab2, tab3, tab4, tab_master = st.tabs([
    "🏠 Dashboard", "📤 Upload", "🔁 Mutasi", "🏥 BOR", "📊 Laporan", "⚙️ Master Data"
])

# --- TAB DASHBOARD ---
with tab_dash:
    with st.container(border=True):
        uploaded_dash = st.file_uploader("Upload data di sini", type=["xlsx", "xls"], key="uploader_dash")
        if uploaded_dash:
            st.session_state.df_mentah = uploaded_dash
            st.success("File diterima. Lanjut ke Tab Upload.")
    if st.session_state.df_clean is not None:
        df = st.session_state.df_clean
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Pasien", len(df))
        if 'jenis_kelamin' in df.columns:
            c2.metric("L", len(df[df['jenis_kelamin'] == 'L']))
            c3.metric("P", len(df[df['jenis_kelamin'] == 'P']))
        if 'umur_tahun' in df.columns:
            c4.metric("Rerata Umur", f"{df['umur_tahun'].mean():.1f} thn")
    else:
        st.info("Belum ada data.")

# --- TAB UPLOAD ---
with tab1:
    st.subheader("Upload & Pemetaan")
    with st.container(border=True):
        uploaded = st.file_uploader("Pilih Excel", type=["xlsx", "xls"])
        if uploaded:
            file_bytes = uploaded.read()
            sheets = get_sheet_names(file_bytes, uploaded.name)
            if sheets:
                sheet = st.selectbox("Pilih Sheet", sheets)
                df, err = load_sheet_by_name(file_bytes, sheet)
                if err: st.error(err)
                else:
                    st.session_state.df_mentah = df
                    st.success("File berhasil dibaca!")
                    
                    # PREVIEW DATA MENTAH (YANG TADI HILANG)
                    with st.expander("👁️ Preview Data Mentah (20 Baris)", expanded=False):
                        st.dataframe(df.head(20), use_container_width=True)
                    
                    st.markdown("### Pemetaan Kolom")
                    opts = ["—"] + list(df.columns)
                    c1, c2 = st.columns(2)
                    with c1:
                        m_nama = st.selectbox("Nama", opts)
                        m_jk = st.selectbox("JK/Umur", opts)
                        m_rm = st.selectbox("No RM", opts)
                        m_kamar = st.selectbox("Kamar", opts)
                    with c2:
                        m_masuk = st.selectbox("Tgl Masuk", opts)
                        m_keluar = st.selectbox("Tgl Keluar", opts)
                        m_status = st.selectbox("Status", opts)
                        m_kelas = st.selectbox("Kelas", opts)
                        
                    if st.button("🚀 Proses Data"):
                        data_bersih = []
                        for _, row in df.iterrows():
                            raw_nama = row[m_nama] if m_nama != "—" else ""
                            raw_jk = row[m_jk] if m_jk != "—" else ""
                            nama = clean_nama(raw_nama)
                            jk, umur = split_jk_umur(f"{raw_nama} {raw_jk}")
                            k_kamar, ruang, klr = parse_kamar(row[m_kamar] if m_kamar != "—" else "")
                            
                            data_bersih.append({
                                "no_rm": str(row[m_rm]).replace('.0','') if m_rm != "—" else None,
                                "nama": nama, "jenis_kelamin": jk, "umur_tahun": umur,
                                "kode_kamar": k_kamar, "ruang": ruang, "kelas": klr,
                                "tgl_masuk": pd.to_datetime(row[m_masuk], errors='coerce') if m_masuk != "—" else pd.NaT,
                                "tgl_keluar": pd.to_datetime(row[m_keluar], errors='coerce') if m_keluar != "—" else pd.NaT,
                                "status_pulang": row[m_status] if m_status != "—" else None,
                                "kelas_jaminan": clean_kelas(row[m_kelas]) if m_kelas != "—" else "Tidak Diketahui"
                            })
                        df_clean = pd.DataFrame(data_bersih).dropna(subset=['nama', 'no_rm'])
                        st.session_state.df_clean = df_clean
                        st.success(f"Berhasil proses {len(df_clean)} baris!")

    if st.session_state.df_clean is not None:
        with st.container(border=True):
            st.subheader("Preview Data Bersih")
            st.dataframe(st.session_state.df_clean, use_container_width=True)
            
            # DOWNLOAD MULTI-SHEET
            buf_multi = io.BytesIO()
            with pd.ExcelWriter(buf_multi, engine='openpyxl') as w:
                st.session_state.df_clean.to_excel(w, sheet_name="Semua_Data", index=False)
                # Looping per ruangan (sederhana)
                for ruang in st.session_state.df_clean['ruang'].dropna().unique():
                    df_r = st.session_state.df_clean[st.session_state.df_clean['ruang'] == ruang]
                    df_r.to_excel(w, sheet_name=str(ruang)[:31], index=False)
            st.download_button("⬇️ Download Semua (1 File Banyak Sheet)", data=buf_multi.getvalue(), file_name="Data_Per_Ruangan.xlsx")

# --- TAB MUTASI ---
with tab2:
    st.subheader("🔁 Mutasi Perpindahan")
    if st.session_state.df_clean is not None:
        df_long = track_perpindahan(st.session_state.df_clean)
        st.dataframe(df_long, use_container_width=True)

# --- TAB BOR ---
with tab3:
    st.subheader("🏥 BOR & Indikator")
    if st.session_state.df_clean is not None:
        df_long = track_perpindahan(st.session_state.df_clean)
        df_bor = hitung_bor(df_long, st.session_state.master_tt)
        if not df_bor.empty:
            total = df_bor.iloc[-1]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("BOR", f"{total['BOR (%)']}%")
            c2.metric("ALOS", f"{total['ALOS (hari)']} hr")
            c3.metric("TOI", f"{total['TOI (hari)']} hr")
            c4.metric("BTO", f"{total['BTO (kali)']}x")
            st.dataframe(df_bor, use_container_width=True)
            
        # BOR HARIAN RPA/RPM
        st.markdown("### BOR RPA/RPM")
        df_harian = hitung_bor_harian(df_long, kapasitas_tt=35)
        if not df_harian.empty:
            st.metric("Rerata BOR Harian", f"{hitung_rata_rata_bor(df_harian)}%")
            st.line_chart(df_harian.set_index('tanggal')['bor_persen'])
            st.dataframe(df_harian)

# --- TAB LAPORAN ---
with tab4:
    st.subheader("📊 Laporan RL & Akreditasi")
    if st.session_state.df_clean is not None:
        df_long = track_perpindahan(st.session_state.df_clean)
        
        with st.expander("Statistik & Mortalitas", expanded=False):
            s_df, m_df = hitung_statistik_dan_mortalitas(df_long)
            st.dataframe(s_df); st.dataframe(m_df)
            
        with st.expander("RL 3.1 (Kegiatan Ranap)", expanded=False):
            rl31 = hitung_rl_31(df_long)
            st.dataframe(rl31)
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as w: rl31.to_excel(w, index=False)
            st.download_button("⬇️ Download RL 3.1", data=buf.getvalue(), file_name="RL_3.1.xlsx")

        with st.expander("RL 4a (Morbiditas)", expanded=False):
            rl4a = hitung_rl_4a(df_long)
            st.dataframe(rl4a)
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as w: rl4a.to_excel(w, index=False)
            st.download_button("⬇️ Download RL 4a", data=buf.getvalue(), file_name="RL_4a.xlsx")

# --- TAB MASTER DATA ---
with tab_master:
    with st.expander("🛏️ Master Tempat Tidur (TT)", expanded=False):
        for ruang, tt in list(st.session_state.master_tt.items()):
            c1, c2 = st.columns([3,1])
            c1.write(f"**{ruang}**")
            st.session_state.master_tt[ruang] = c2.number_input(f"TT", min_value=0, value=tt, label_visibility="collapsed", key=f"tt_{ruang}")
            
    with st.expander("🏷️ Master Kelas Kamar", expanded=False):
        for ruang in st.session_state.master_tt.keys():
            c1, c2 = st.columns([3,1])
            c1.write(f"**{ruang}**")
            opsi_kelas = ["VIP", "1", "2", "3", "Khusus"]
            idx_awal = opsi_kelas.index(st.session_state.master_kelas.get(ruang, "3")) if st.session_state.master_kelas.get(ruang, "3") in opsi_kelas else 0
            st.session_state.master_kelas[ruang] = c2.selectbox(f"Kelas", opsi_kelas, index=idx_awal, label_visibility="collapsed", key=f"kls_{ruang}")
        if st.button("💾 Simpan Master Kelas"):
            st.success("Master Kelas disimpan.")

    with st.expander("🏥 Master ICD-10", expanded=False):
        st.info("Fitur Import ICD-10 (Butuh koneksi Supabase).")
