codex "Tolong kerjakan semua tugas berikut secara berurutan. JANGAN sentuh file lain selain yang disebut.

=== TUGAS 1: Ganti total modules/master_tt.py ===

Ganti total isi file modules/master_tt.py dengan kode berikut:

import json
import os
import pandas as pd

TT_FILE = 'data/master_tt.json'

DEFAULT_TT = [
    ('HCU', 'HCU', 3, True),
    ('ICU', 'ICU', 3, True),
    ('NICU', 'NICU', 3, True),
    ('PICU', 'PICU', 1, True),
    ('Isolasi-ICU', 'Isolasi-ICU', 3, True),
    ('Perina Level 2', 'Perina', 5, True),
    ('Perina Level 1 Room', 'Perina', 0, False),
    ('Sakinah-1', 'Isolasi Normal', 2, True),
    ('Sakinah-2', 'Isolasi Normal', 5, True),
    ('Firdaus-1', 'VIP', 1, True),
    ('Firdaus-2', 'VIP', 1, True),
    *[(f'Ar Rahmah-{i}', 'Kelas 1', 2, True) for i in range(1, 16)],
    ('Safa-1', 'Kelas 2', 2, True),
    ('Safa-2', 'Kelas 2', 2, True),
    ('Safa-3', 'Kelas 2', 3, True),
    *[(f'Marwah-{i}', 'Kelas 3', 4, True) for i in range(1, 10)],
    ('Transit IGD', 'Transit IGD', 0, False),
]

def _ensure_dir():
    os.makedirs('data', exist_ok=True)

def load_master_tt() -> pd.DataFrame:
    _ensure_dir()
    if os.path.exists(TT_FILE):
        with open(TT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return pd.DataFrame(data)
    df = pd.DataFrame(DEFAULT_TT, columns=['ruangan', 'kelas', 'jumlah_tt', 'dihitung_bor'])
    save_master_tt(df)
    return df

def save_master_tt(df: pd.DataFrame):
    _ensure_dir()
    df.to_json(TT_FILE, orient='records', indent=2, force_ascii=False)

def total_tt_dihitung(df: pd.DataFrame) -> int:
    return int(df[df['dihitung_bor'] == True]['jumlah_tt'].sum())

=== TUGAS 2: Edit app.py, HANYA blok with tab5: ===

Di file app.py, cari blok yang dimulai 'with tab5:'. Ganti HANYA isi blok itu sampai sebelum 'with tab' berikutnya, dengan kode:

with tab5:
    st.subheader('⚙️ Master Tempat Tidur')
    st.caption('Edit jumlah TT, tambah ruangan, atau hapus. Data tersimpan otomatis.')

    df_tt = load_master_tt()

    edited = st.data_editor(
        df_tt,
        column_config={
            'ruangan': st.column_config.TextColumn('Ruangan', width='medium'),
            'kelas': st.column_config.TextColumn('Kelas', width='small'),
            'jumlah_tt': st.column_config.NumberColumn('TT', min_value=0, step=1, width='small'),
            'dihitung_bor': st.column_config.CheckboxColumn('Dihitung BOR?', width='small'),
        },
        use_container_width=True,
        num_rows='dynamic',
        key='master_tt_editor',
        hide_index=True,
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button('💾 Simpan', type='primary', use_container_width=True):
            save_master_tt(edited)
            st.success('✅ Tersimpan!')
            st.rerun()

    st.metric('Total TT (dihitung BOR)', total_tt_dihitung(edited))

JANGAN sentuh blok with tab1, tab2, tab3, tab4. JANGAN ganti seluruh app.py.

=== TUGAS 3: Cek import di app.py ===

Pastikan di bagian import app.py ada baris:
from modules.master_tt import load_master_tt, save_master_tt, total_tt_dihitung

Kalau belum ada, tambahkan di bagian import. Jangan ubah baris import lain.

=== TUGAS 4: Hapus master_tt.json lama dari repo dan gitignore ===

Jalankan perintah berikut di terminal:
rm -f data/master_tt.json
grep -qxF 'data/master_tt.json' .gitignore || echo 'data/master_tt.json' >> .gitignore
git rm --cached data/master_tt.json 2>/dev/null || true

=== TUGAS 5: Git commit dan push ===

Jalankan:
git add modules/master_tt.py app.py .gitignore
git commit -m 'fix: master TT persisten + default 100 TT + Ar Rahmah 1-15 + ignore json'
git push origin main

Kalau branch bukan main, cek dengan 'git branch --show-current' dan gunakan branch yang aktif.

=== SELESAI ===

Setelah semua selesai, tampilkan ringkasan file apa saja yang berubah dan hasil git push."