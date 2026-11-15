import streamlit as st
import pandas as pd
import io
import json
from supabase import create_client, Client

from modules.loader import get_sheet_names, load_sheet_by_name
from modules.cleaner import clean_nama, split_jk_umur, parse_kamar, clean_kelas
from modules.tracker import track_perpindahan
from modules.bor_calculator import hitung_bor
from modules.reporter import hitung_statistik_dan_mortalitas, hitung_rl_31, hitung_rl_4a

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="SIM-RM Helper", page_icon="", layout="wide")

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

# ==========================================
# 3. TABS
# ==========================================
tab_dash, tab_master, tab1, tab2, tab3, tab4 = st.tabs([
    " Dashboard", "⚙️ Master Data", " Upload", " Mutasi", " BOR", " Laporan"
])

# --- TAB: DASHBOARD ---
with tab_dash:
    st.subheader("Ringkasan Operasional RS")
    
    with st.container(border=True):
        st.write("**Unggah Cepat**")
        uploaded_dash = st.file_uploader("Upload data di sini", type=["xlsx", "xls"], key="uploader_dash")
        if uploaded_dash:
            st.info("File diterima. Silakan ke tab Upload untuk memproses.")

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
    st.subheader("⚙️ Master Tempat Tidur (TT)")
    with st.container(border=True):
        for ruang, tt in list(st.session_state.master_tt.items()):
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{ruang}**")
            st.session_state.master_tt[ruang] = col2.number_input(f"TT {ruang}", min_value=0, value=tt, label_visibility="collapsed", key=f"tt_{ruang}")
        if st.button(" Simpan Master TT"):
            st.success("Master TT disimpan.")

    st.subheader(" Master ICD-10")
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
                    
                    if st.button(" Proses Data Pasien"):
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
            
        with st.expander(" RL 3.1 — Kegiatan Ranap", expanded=False):
            df_rl31 = hitung_rl_31(df_long)
            st.dataframe(df_rl31, use_container_width=True)
            
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
