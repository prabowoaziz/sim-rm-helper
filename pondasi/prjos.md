# TUGAS CODEX: OVERHAUL TAMPILAN UI KE DESKTOP PROFESSIONAL

Halo Codex. Kita mau rombak total tampilan web `app.py` agar terlihat seperti aplikasi enterprise profesional (fokus Desktop). 

ATURAN KETAT:
1. JANGAN ubah logika pemrosesan data (loader, cleaner, bor, dll).
2. JANGAN kurangi fitur apa pun.
3. GANTI `st.tabs` menjadi `st.sidebar.radio` untuk navigasi menu.
4. Pasang CSS kustom yang gua kasih di bawah ini.

---

## LANGKAH 1: Ganti Navigasi ke Sidebar
Hapus semua deklarasi `tab1, tab2, ... = st.tabs(...)`.
Ganti strukturnya menjadi:
```python
with st.sidebar:
    st.markdown("<h2 style='color:#0ea5e9; font-weight:700;'>🏥 SIM-RM Helper</h2>", unsafe_allow_html=True)
    menu = st.radio("Navigasi", ["🏠 Dashboard", "📤 Upload Data", "🔁 Perpindahan Kamar", "🏥 BOR & Indikator", "📊 Laporan RL & Akreditasi", "⚙️ Master Data"])

if menu == "🏠 Dashboard":
    # isi dashboard
elif menu == "📤 Upload Data":
    # isi upload
# dst untuk semua menu
LANGKAH 2: Pasang CSS Profesional
Tempel kode CSS ini tepat setelah st.set_page_config:

python
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f4f6f8; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; padding-top: 20px; }
    [data-testid="stSidebar"] .stRadio > div { gap: 4px; }
    [data-testid="stSidebar"] .stRadio label { padding: 12px 16px; border-radius: 10px; font-weight: 600; color: #64748b; width: 100%; transition: all 0.2s; }
    [data-testid="stSidebar"] .stRadio label:hover { background-color: #f8fafc; color: #1e293b; }
    [data-testid="stSidebar"] .stRadio div[aria-checked="true"] label { background-color: #e0f2fe; color: #0284c7; }

    /* Container Card (Kotak Putih) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0 !important;
        border-radius: 16px;
        padding: 24px !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);
        margin-bottom: 24px;
    }
    
    /* Metrics */
    div[data-testid="stMetric"] { background-color: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid #0ea5e9; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02); }
    div[data-testid="stMetric"] label { color: #64748b; font-weight: 600; font-size: 14px; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #1e293b; font-weight: 700; font-size: 32px; }
    
    /* Tombol */
    .stButton > button { background-color: #0ea5e9; color: white; border-radius: 10px; border: none; padding: 12px 24px; font-weight: 600; font-size: 15px; width: 100%; transition: all 0.2s; }
    .stButton > button:hover { background-color: #0284c7; box-shadow: 0 4px 12px rgba(14,165,233,0.3); color: white; }
    
    .stDownloadButton > button { background-color: #10b981; color: white; border-radius: 10px; border: none; font-weight: 600; padding: 10px 20px; transition: all 0.2s; }
    .stDownloadButton > button:hover { background-color: #059669; color: white; }

    /* Tabel & Expander */
    [data-testid="stDataFrame"] { border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; }
    .streamlit-expanderHeader { font-weight: 600; color: #1e293b; background-color: #f8fafc; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)
LANGKAH 3: Bungkus Konten dengan Container
Di dalam setiap kondisi if menu == ..., bungkus kontennya dengan with st.container(border=True): agar tampilannya berbentuk kotak/card putih sesuai desain CSS.

(Catatan: Pastikan import modul dan inisialisasi st.session_state tetap ada di atas).