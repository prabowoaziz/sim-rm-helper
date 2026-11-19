import re

import streamlit as st


# Satu sumber master TT kanonis, 100 tempat tidur.
MASTER_TT_DEFAULT = {
    'HCU': 3, 'ICU': 3, 'NICU': 3, 'PICU': 1, 'Isolasi-ICU': 3,
    'Perina Level 2': 5, 'Perina Level 1 Room': 0,
    'Sakinah-1': 2, 'Sakinah-2': 5,
    'Firdaus-1': 1, 'Firdaus-2': 1,
    **{f'Ar Rahmah-{i}': 2 for i in range(1, 16)},
    'Safa-1': 2, 'Safa-2': 2, 'Safa-3': 3,
    **{f'Marwah-{i}': 4 for i in range(1, 10)},
    'Transit IGD': 0,
}

MASTER_KELAS_DEFAULT = {
    'HCU': 'HCU', 'ICU': 'ICU', 'NICU': 'NICU', 'PICU': 'PICU', 'Isolasi-ICU': 'Isolasi-ICU',
    'Perina Level 2': 'Perina', 'Perina Level 1 Room': 'Perina',
    'Sakinah-1': 'Isolasi Normal', 'Sakinah-2': 'Isolasi Normal',
    'Firdaus-1': 'VIP', 'Firdaus-2': 'VIP',
    **{f'Ar Rahmah-{i}': '1' for i in range(1, 16)},
    'Safa-1': '2', 'Safa-2': '2', 'Safa-3': '2',
    **{f'Marwah-{i}': '3' for i in range(1, 10)},
    'Transit IGD': 'Transit IGD',
}

MASTER_DIHITUNG_BOR_DEFAULT = {
    'Perina Level 1 Room': False,
    'Transit IGD': False,
}


def normalisasi_ruang(nama):
    """Normalisasi variasi nama ruangan ke nama kanonis master."""
    if nama is None:
        return None
    s = str(nama).strip()
    if not s:
        return s
    low = ' '.join(s.lower().replace('_', ' ').replace('-', ' ').split())
    if low in ('perina level 1', 'perina level 1 room', 'perina l1', 'perina 1'):
        return 'Perina Level 1 Room'
    if low in ('perina level 2', 'perina l2', 'perina 2'):
        return 'Perina Level 2'
    if low in ('transit igd', 'tig', 'transit'):
        return 'Transit IGD'
    match = re.match(r'^(ar rahmah|safa|marwah|sakinah|firdaus)\s*(\d+)$', low, re.I)
    if match:
        base = {
            'ar rahmah': 'Ar Rahmah', 'safa': 'Safa', 'marwah': 'Marwah',
            'sakinah': 'Sakinah', 'firdaus': 'Firdaus',
        }[match.group(1).lower()]
        return f"{base}-{int(match.group(2))}"
    if s in MASTER_TT_DEFAULT:
        return s
    return s


def get_master_tt():
    return dict(st.session_state.get('master_tt', MASTER_TT_DEFAULT))


def get_master_kelas():
    return dict(st.session_state.get('master_kelas', MASTER_KELAS_DEFAULT))


def get_master_dihitung_bor():
    state = st.session_state.get('master_dihitung_bor', {})
    result = {ruang: True for ruang in get_master_tt()}
    result.update(state)
    for ruang, dihitung in MASTER_DIHITUNG_BOR_DEFAULT.items():
        if ruang not in state:
            result[ruang] = dihitung
    return result


def total_tt_dihitung(master_tt=None, master_dihitung_bor=None):
    """Jumlah TT yang dihitung BOR setelah menerapkan flag pada nama kanonis."""
    tt = master_tt if master_tt is not None else get_master_tt()
    flags = master_dihitung_bor if master_dihitung_bor is not None else get_master_dihitung_bor()
    normalized_flags = {normalisasi_ruang(k): v for k, v in flags.items()}
    return sum(
        int(jumlah or 0)
        for ruang, jumlah in tt.items()
        if normalized_flags.get(normalisasi_ruang(ruang), True)
    )


def init_master_tt():
    if 'master_tt' not in st.session_state:
        st.session_state.master_tt = dict(MASTER_TT_DEFAULT)
    if 'master_kelas' not in st.session_state:
        st.session_state.master_kelas = dict(MASTER_KELAS_DEFAULT)
    if 'master_dihitung_bor' not in st.session_state:
        st.session_state.master_dihitung_bor = dict(MASTER_DIHITUNG_BOR_DEFAULT)


def update_master_tt(ruang, jumlah):
    if 'master_tt' not in st.session_state:
        init_master_tt()
    st.session_state.master_tt[normalisasi_ruang(ruang) or ruang] = int(jumlah)


def init_master_kelas():
    if 'master_kelas' not in st.session_state:
        st.session_state.master_kelas = dict(MASTER_KELAS_DEFAULT)
    for ruang in st.session_state.get('master_tt', {}):
        canonical = normalisasi_ruang(ruang) or ruang
        st.session_state.master_kelas.setdefault(canonical, MASTER_KELAS_DEFAULT.get(canonical, '1'))


def update_master_kelas(ruang, kelas):
    if 'master_kelas' not in st.session_state:
        init_master_kelas()
    st.session_state.master_kelas[normalisasi_ruang(ruang) or ruang] = str(kelas)


def load_master_from_supabase(client):
    """Load master dari tabel master_tt; jika kosong, biarkan default lokal."""
    try:
        response = client.table('master_tt').select('*').execute()
    except Exception:
        return False
    rows = response.data or []
    if not rows:
        return False
    tt, kelas, dihitung = {}, {}, {}
    for row in rows:
        nama_asli = row.get('ruangan')
        nama = normalisasi_ruang(nama_asli) or nama_asli
        if not nama:
            continue
        tt[nama] = int(row.get('jumlah_tt') or 0)
        kelas[nama] = str(row.get('kelas') or MASTER_KELAS_DEFAULT.get(nama, '1'))
        value = row.get('dihitung_bor')
        dihitung[nama] = bool(value) if value is not None else MASTER_DIHITUNG_BOR_DEFAULT.get(nama, True)
    if not tt:
        return False
    for ruang, value in MASTER_DIHITUNG_BOR_DEFAULT.items():
        dihitung.setdefault(ruang, value)
    st.session_state.master_tt = tt
    st.session_state.master_kelas = kelas
    st.session_state.master_dihitung_bor = dihitung
    return True


def save_master_to_supabase(client):
    """Simpan master ke tabel master_tt dengan nama ruangan kanonis."""
    tt = {normalisasi_ruang(k) or k: v for k, v in st.session_state.master_tt.items()}
    kelas = {normalisasi_ruang(k) or k: v for k, v in st.session_state.master_kelas.items()}
    flags = {normalisasi_ruang(k) or k: v for k, v in st.session_state.master_dihitung_bor.items()}
    rooms = sorted(set(tt) | set(kelas))
    rows = [
        {
            'ruangan': room,
            'jumlah_tt': int(tt.get(room, 0)),
            'kelas': str(kelas.get(room, MASTER_KELAS_DEFAULT.get(room, '1'))),
            'dihitung_bor': bool(flags.get(room, MASTER_DIHITUNG_BOR_DEFAULT.get(room, True))),
        }
        for room in rooms
    ]
    if rows:
        return client.table('master_tt').upsert(rows, on_conflict='ruangan').execute()
    return None
