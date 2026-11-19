Halo Codex. Kita mau melakukan OVERHAUL TAMPILAN DESKTOP menjadi versi "Professional UI". 

Tugas 1: Ganti `st.tabs` menjadi Sidebar Navigation
- Hapus deklarasi tab (tab1, tab2, dll).
- Gunakan `st.sidebar.radio` untuk menu:
  menu = st.sidebar.radio("Navigasi", ["🏠 Dashboard", "📤 Upload Data", "🔁 Perpindahan Kamar", "🏥 BOR & Indikator", "📊 Laporan RL & Akreditasi", "⚙️ Master Data"])
- Ubah struktur logika `with tab1:` menjadi `if menu == "📤 Upload Data":`, dst. Pastikan logika di dalam setiap menu tidak ada yang hilang.

Tugas 2: Tambahkan CSS Kustom di `app.py`
Copy-paste kode CSS ini PERSIS di bawah `st.set_page_config` (gunakan `st.markdown` dengan `unsafe_allow_html=True`):

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Background & Font */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f4f6f8; }
    
    /* Sembunyikan elemen bawaan Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
        padding-top: 20px;
    }
    [data-testid="stSidebar"] .stRadio > div {
        gap: 8px;
    }
    [data-testid="stSidebar"] .stRadio label {
        padding: 12px 20px;
        border-radius: 10px;
        font-weight: 600;
        color: #64748b;
        transition: all 0.2s;
        cursor: pointer;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background-color: #f8fafc;
        color: #1e293b;
    }

    /* Card Container untuk konten */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0 !important;
        border-radius: 16px;
        padding: 24px !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);
    }
    
    /* Card Metrics */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-top: 4px solid #0ea5e9;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);
    }
    
    /* Tombol Primary */
    .stButton > button {
        background-color: #0ea5e9;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 15px;
        transition: all 0.2s;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #0284c7;
        box-shadow: 0 4px 12px rgba(14,165,233,0.3);
    }

    /* Tombol Download (Hijau) */
    .stDownloadButton > button {
        background-color: #10b981;
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: 600;
    }
    .stDownloadButton > button:hover {
        background-color: #059669;
    }

    /* Tabel Streamlit */
    [data-testid="stDataFrame"] {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

Tugas 3: Bungkus Konten dengan Container
- Di setiap menu (if menu == ...), bungkus konten utamanya menggunakan `st.container(border=True)` agar tampilannya seperti Card putih (sesuai desain CSS di atas).
- Kecualikan bagian yang memang butuh lebar penuh (seperti chart di Dashboard).

Aturan:
- JANGAN ngubah logika pemrosesan data.
- JANGAN ngurangi fitur apapun.
- Setelah selesai, push ke GitHub.
