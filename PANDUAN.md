# 🤖 Perintah untuk Codex — SIM-RM Helper

Halo Codex. Gua mau lu bantu setup proyek **SIM-RM Helper** — web app Streamlit untuk pengolahan data rekam medis rumah sakit.

Ikuti perintah di bawah **satu per satu**, jangan lompat. Setiap selesai satu langkah, kabarin gua.

---

## 📁 Konteks Proyek

- **Lokasi:** `C:\Users\Hype GLK\Documents\Projects\sim-rm-helper`
- **Stack:** Streamlit + Pandas + OpenPyXL + Supabase
- **Python:** 3.15.2 (venv sudah aktif)
- **Repo:** https://github.com/prabowoaziz/sim-rm-helper
- **Status:** folder & file kosong sudah dibuat, tinggal diisi

Struktur folder saat ini:
```
sim-rm-helper/
├── app.py                 (kosong)
├── requirements.txt       (kosong)
├── .gitignore             (kosong)
├── README.md              (kosong)
├── .streamlit/
│   └── config.toml        (kosong)
└── modules/
    └── __init__.py        (kosong)
```

---

## ✅ PERINTAH 1 — Isi `requirements.txt`

Tulis file `requirements.txt` dengan isi persis:

```
streamlit>=1.40.0
pandas>=2.2.0
openpyxl>=3.1.0
supabase>=2.0.0
```

---

## ✅ PERINTAH 2 — Isi `.gitignore`

Tulis file `.gitignore` dengan isi persis:

```
venv/
__pycache__/
*.pyc
.env
.streamlit/secrets.toml
*.xlsx
*.xls
*.csv
data/
.DS_Store
```

---

## ✅ PERINTAH 3 — Isi `.streamlit/config.toml`

Tulis file `.streamlit/config.toml` dengan isi persis:

```toml
[theme]
primaryColor = "#0ea5e9"
backgroundColor = "#f4f6fa"
secondaryBackgroundColor = "#ffffff"
textColor = "#0f172a"
font = "sans serif"

[server]
maxUploadSize = 50
```

---

## ✅ PERINTAH 4 — Isi `app.py`

Tulis file `app.py` dengan isi persis:

```python
import streamlit as st

st.set_page_config(
    page_title="SIM-RM Helper",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏥 SIM-RM Helper")
st.caption("Asisten Laporan Rekam Medis — Upload, Olah, Laporkan")

st.markdown("---")

st.info("🚧 Aplikasi sedang dalam pengembangan. Fitur akan ditambahkan bertahap.")

tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload", "🔁 Mutasi", "🏥 BOR", "📊 Laporan"])

with tab1:
    st.subheader("📤 Upload Data Mentah")
    uploaded = st.file_uploader("Pilih file Excel", type=["xlsx", "xls", "csv"])
    if uploaded:
        st.success(f"File diterima: {uploaded.name}")

with tab2:
    st.subheader("🔁 Track Perpindahan Kamar")
    st.write("Fitur dalam pengembangan.")

with tab3:
    st.subheader("🏥 BOR & Indikator")
    st.write("Fitur dalam pengembangan.")

with tab4:
    st.subheader("📊 Laporan RL & Akreditasi")
    st.write("Fitur dalam pengembangan.")
```

---

## ✅ PERINTAH 5 — Isi `README.md`

Tulis file `README.md` dengan isi persis:

```markdown
# SIM-RM Helper

Web app untuk membantu pengolahan data rekam medis rumah sakit.

## Fitur
- Upload & cleaning data mentah
- Track perpindahan kamar pasien
- Hitung BOR, ALOS, TOI, BTO
- Laporan RL 1–5 & Akreditasi

## Tech Stack
- Streamlit (frontend + backend Python)
- Supabase (database + storage)
- Pandas (olah data)
```

---

## ✅ PERINTAH 6 — Install Dependensi

Setelah semua file diisi, jalankan di terminal VS Code:

```powershell
pip install -r requirements.txt
```

Tunggu sampai selesai. Kalau ada error, laporkan ke gua.

---

## ✅ PERINTAH 7 — Test Lokal

Setelah install selesai, jalankan:

```powershell
streamlit run app.py
```

Browser harusnya kebuka otomatis di `http://localhost:8501`.
Pastikan muncul:
- Judul "🏥 SIM-RM Helper"
- 4 tab: Upload, Mutasi, BOR, Laporan
- File uploader di tab Upload

Kalau berhasil, tutup dengan `Ctrl+C`. Laporkan hasilnya ke gua.

---

## ✅ PERINTAH 8 — Push ke GitHub

Kalau test lokal berhasil, jalankan berurutan:

```powershell
git add .
git commit -m "init: struktur awal SIM-RM Helper"
git branch -M main
git remote add origin https://github.com/prabowoaziz/sim-rm-helper.git
git push -u origin main
```

Kalau `git remote add` error "already exists", ganti dengan:

```powershell
git remote set-url origin https://github.com/prabowoaziz/sim-rm-helper.git
git push -u origin main
```

Laporkan output-nya ke gua.

---

## 🎯 Setelah Semua Selesai

Kabarin gua kalau:
1. Semua file udah terisi
2. `pip install` sukses
3. `streamlit run app.py` jalan
4. `git push` sukses

Nanti gua lanjut ke **Langkah 9: Deploy Streamlit Cloud** dan **Langkah 10: Setup Supabase**.

---

## ⚠️ Aturan Penting

- **Jangan** ubah struktur folder tanpa izin
- **Jangan** tambah dependensi di luar `requirements.txt` dulu
- **Jangan** commit file `.xlsx`, `.xls`, `.csv`, atau data pasien
- Kalau ada error, **screenshot + kirim ke gua**, jangan diakalin sendiri dulu
- Ikuti urutan **satu per satu**, jangan lompat

---

**Gua tunggu laporan lu setelah tiap langkah. 🚀**