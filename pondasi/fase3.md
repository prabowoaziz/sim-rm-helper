# 📘 FASE 3 - PART 1: Master Tempat Tidur

**Tujuan:** Membuat UI untuk menyimpan jumlah Tempat Tidur (TT) per ruangan, sebagai dasar perhitungan BOR.

---

## 🤖 PERINTAH UNTUK CODEX (Backend/Logic)

Copy-paste teks di bawah ini ke Codex:

```text
Halo Codex. Kita masuk ke Fase 3: Master Tempat Tidur. Tolong kerjakan instruksi ini.

Tugas 1: Buat file baru bernama `modules/master_data.py`.
Isi dengan fungsi untuk menangani master TT menggunakan `st.session_state` (sementara, belum ke database Supabase):

import streamlit as st

def init_master_tt():
    if "master_tt" not in st.session_state:
        # Default data TT (bisa diubah user di UI)
        st.session_state.master_tt = {
            "HCU": 6,
            "ICU": 4,
            "NICU": 3,
            "PICU": 2,
            "Ar Rahmah-1": 10,
            "Marwah-1": 8,
            "Kenanga": 10
        }

def update_master_tt(ruang, jumlah):
    if "master_tt" not in st.session_state:
        init_master_tt()
    st.session_state.master_tt[ruang] = int(jumlah)

Tugas 2: Update file `app.py`.
Tambahkan Tab baru di bagian atas (sebelum `tab1, tab2...`): `tab_master, tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Master Data", "📤 Upload", "🔁 Mutasi", "🏥 BOR", "📊 Laporan"])`.

Tugas 3: Isi UI untuk `tab_master`:
- Panggil `init_master_tt()`.
- Tampilkan `st.subheader("⚙️ Master Tempat Tidur (TT)")`.
- Tampilkan `st.info("Silakan atur jumlah tempat tidur per ruangan.")`.
- Loop melalui `st.session_state.master_tt`. Tampilkan `st.number_input` untuk tiap ruangan (minimal 0).
- Tambahkan fitur tambah ruangan baru: `st.text_input` untuk nama ruang baru, dan `st.button("Tambah Ruangan")`.
- Jika tombol simpan diklik, update `st.session_state.master_tt` dan `st.success("Master TT berhasil diperbarui!")`.

Tugas 4: Sesuaikan index tab yang lain. Karena tab_master ditambah di depan, `tab1` (Upload) sekarang index ke-2, dst. Pastikan isi kode di dalamnya tetap jalan.

Aturan:
- Jangan ubah CSS/tema.
- Setelah selesai, update ke GitHub.