Halo Codex. Tolong GANTI SELURUH ISI file `modules/cleaner.py` dan ubah bagian pemrosesan di `app.py` PERSIS SEPERTI KODE DI BAWAH INI. Jangan ubah satu huruf pun, cukup copy-paste.

=== GANTI SELURUH ISI modules/cleaner.py DENGAN INI ===

import pandas as pd
import re

def clean_nama(val):
    if pd.isna(val): return None
    s = str(val).strip()
    # Buang format (XX Th), (XX Bl), (XX Hr) di akhir
    s = re.sub(r'\s*\(\d+\s*(Th|Bl|Hr|th|bl|hr)\)\s*$', '', s, flags=re.IGNORECASE)
    # Buang gelar di belakang koma (misal: , AN atau , NY)
    s = re.sub(r',\s*(AN|An|an|TN|Tn|tn|NY|Ny|ny|NN|Nn|nn|BY|By|by)\s*$', '', s)
    # Buang pipa jika ada
    s = s.replace('|', '').strip()
    # Buang spasi ganda
    s = re.sub(r'\s+', ' ', s)
    return s.upper().strip()

def split_jk_umur(val):
    if pd.isna(val): return None, None
    s = str(val).strip()
    
    # Cari pola umur di dalam kurung (misal: 56 Th, 2 Bl, 0 Hr)
    m_umur = re.search(r'\((\d+)\s*(Th|Bl|Hr|th|bl|hr)?\)', s, flags=re.IGNORECASE)
    umur_tahun = None
    if m_umur:
        angka = int(m_umur.group(1))
        satuan = (m_umur.group(2) or 'Th').lower()
        if satuan == 'bl':
            umur_tahun = round(angka / 12, 2)
        elif satuan == 'hr':
            umur_tahun = round(angka / 365, 2)
        else:
            umur_tahun = float(angka)
            
    # Cari Jenis Kelamin (AN, TN, NY, NN, BY)
    jk = None
    if re.search(r'\b(AN|TN)\b', s, flags=re.IGNORECASE):
        jk = 'L'
    elif re.search(r'\b(NY|NN)\b', s, flags=re.IGNORECASE):
        jk = 'P'
    
    return jk, umur_tahun

def parse_kamar(val):
    if pd.isna(val): return None, None, None
    s = str(val).strip()
    # Pisahkan berdasarkan spasi pertama
    parts = s.split(' ', 1)
    kode = parts[0]
    ruang = parts[1] if len(parts) > 1 else None
    
    # Ambil kelas dari kode (misal KEN-2-B1 -> 2)
    tokens = kode.split('-')
    kelas = tokens[1] if len(tokens) > 1 else None
    return kode, ruang, kelas

def clean_kelas(val):
    if pd.isna(val): return "Tidak Diketahui"
    s = str(val).strip().upper()
    if s in ['VIP', '1', '2', '3']:
        return s
    return "Tidak Diketahui"

=== UPDATE app.py PADA BAGIAN KLIK "PROSES DATA" ===

Tolong cari bagian `if st.button("🚀 Proses Data"):` atau logika saat tombol proses diklik di `app.py`. GANTI logika pemrosesan di dalamnya dengan kode ini:

    if st.button("🚀 Proses Data"):
        with st.spinner("Membersihkan data..."):
            # Ambil dataframe mentah
            df_temp = st.session_state.df_mentah.copy()
            
            # Siapkan list untuk menampung baris bersih
            data_bersih = []
            
            for idx, row in df_temp.iterrows():
                # 1. Ambil nilai mentah berdasarkan mapping user (asumsikan variabel map_nama, map_jk_umur, map_rm, map_kamar, map_masuk, map_keluar, map_kelas sudah ada dari selectbox)
                raw_nama = row[map_nama] if pd.notna(row[map_nama]) else ""
                raw_jk_umur = row[map_jk_umur] if map_jk_umur != "— Pilih kolom —" and pd.notna(row[map_jk_umur]) else ""
                
                # Jika user memilih untuk pakai kolom Nama yang nyampur, gabungkan
                teks_gabungan = str(raw_nama) + " " + str(raw_jk_umur)
                
                # 2. Bersihkan
                nama_bersih = clean_nama(raw_nama)
                jk, umur = split_jk_umur(teks_gabungan)
                
                # Jika JK kosong, coba ambil dari raw_nama
                if jk is None and umur is None:
                    jk, umur = split_jk_umur(raw_nama)
                
                # 3. Parse Kamar
                raw_kamar = row[map_kamar] if pd.notna(row[map_kamar]) else ""
                kode_kamar, ruang, kelas_kamar = parse_kamar(raw_kamar)
                
                # 4. Tanggal
                tgl_m = pd.to_datetime(row[map_masuk], errors='coerce')
                tgl_k = pd.to_datetime(row[map_keluar], errors='coerce') if map_keluar != "— Pilih kolom —" else pd.NaT
                
                # 5. Kelas
                raw_kelas = row[map_kelas] if map_kelas != "— Pilih kolom —" and pd.notna(row[map_kelas]) else kelas_kamar
                
                # Simpan ke list
                data_bersih.append({
                    "no_rm": str(row[map_rm]).strip() if pd.notna(row[map_rm]) else None,
                    "nama": nama_bersih,
                    "jenis_kelamin": jk,
                    "umur_tahun": umur,
                    "kode_kamar": kode_kamar,
                    "ruang": ruang,
                    "kelas": clean_kelas(raw_kelas),
                    "tgl_masuk": tgl_m,
                    "tgl_keluar": tgl_k,
                    "status_pulang": row.get('status_pulang', None)
                })
            
            # Buat DataFrame hasil
            df_clean = pd.DataFrame(data_bersih)
            
            # Hapus baris yang tidak punya nama atau no_rm (baris kosong)
            df_clean = df_clean.dropna(subset=['nama', 'no_rm'])
            
            # Simpan ke session state
            st.session_state.df_clean = df_clean
            st.success("✅ Data berhasil dibersihkan!")
            st.dataframe(df_clean, use_container_width=True)

Jangan ubah bagian lain di app.py. Jika variabel nama selectbox di kode lu berbeda (misal `kolom_nama` bukan `map_nama`), tolong sesuaikan variabel pemanggilannya agar tidak error. Setelah selesai, push ke GitHub.