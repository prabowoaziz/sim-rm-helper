Halo Codex. Kita masuk ke tahap Finalisasi. Ada 2 tugas besar: menyimpan Master Data ke Supabase dan mempercantik UI. 

Tugas 1: Integrasi Supabase (Simpan Master Data)
1. Di `app.py`, tambahkan inisialisasi Supabase menggunakan `st.secrets["supabase"]["url"]` dan `st.secrets["supabase"]["key"]`.
2. Di Tab "⚙️ Master Data", ubah logika penyimpanan. Jangan hanya simpan di `st.session_state`. 
   - Saat tombol "Simpan Master TT" atau "Simpan Master Kelas" diklik, lakukan `upsert` ke tabel Supabase bernama `master_ruangan` (berisi kolom: `nama_ruangan`, `jumlah_tt`, `kelas`).
   - Saat aplikasi pertama kali dimuat, tarik data dari tabel `master_ruangan` tersebut untuk mengisi `st.session_state.master_tt` dan `master_kelas`.

Tugas 2: Percantik UI dengan CSS Kustom
Di bagian paling atas `app.py` (setelah `st.set_page_config`), tambahkan fungsi CSS kustom ini PERSIS SEPERTI INI. JANGAN UBAH SATU HURUF PUN:

st.markdown("""
<style>
    /* Font & Background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Sembunyikan menu Streamlit bawaan */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Percantik Card Metrics */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border-top: 4px solid #0ea5e9;
    }
    div[data-testid="stMetric"] label {
        color: #64748b;
        font-weight: 600;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #0f172a;
        font-weight: 700;
    }

    /* Percantik Tombol */
    .stButton > button {
        background-color: #0ea5e9;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.2s ease;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #0284c7;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);
    }

    /* Percantik Tab */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #ffffff;
        padding: 8px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e0f2fe !important;
        color: #0284c7 !important;
    }
</style>
""", unsafe_allow_html=True)

Tugas 3: Ganti Judul Utama
Di `app.py`, ganti judul "SIM-RM Helper" menjadi bentuk HTML seperti ini:
st.markdown("<h1 style='text-align: center; color: #0f172a;'>🏥 SIM-RM Helper</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 16px;'>Asisten Laporan Rekam Medis — Upload, Olah, Laporkan</p>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

Aturan: Jangan ubah logika pemrosesan data. Setelah selesai, update ke GitHub.