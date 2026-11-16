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


def init_master_kelas():
    if "master_kelas" not in st.session_state:
        st.session_state.master_kelas = {
            "Ar Rahmah-1": "1",
            "Marwah-1": "2",
            "Kenanga": "3",
        }
    for ruang in st.session_state.get("master_tt", {}):
        st.session_state.master_kelas.setdefault(ruang, "1")


def update_master_kelas(ruang, kelas):
    if "master_kelas" not in st.session_state:
        init_master_kelas()
    st.session_state.master_kelas[ruang] = str(kelas)


def load_master_from_supabase(client):
    """Load room capacities and classes from the master_ruangan table."""
    response = client.table("master_ruangan").select(
        "nama_ruangan, jumlah_tt, kelas"
    ).execute()
    rows = response.data or []
    if not rows:
        return False

    st.session_state.master_tt = {
        row["nama_ruangan"]: int(row["jumlah_tt"] or 0)
        for row in rows
        if row.get("nama_ruangan")
    }
    st.session_state.master_kelas = {
        row["nama_ruangan"]: str(row["kelas"] or "1")
        for row in rows
        if row.get("nama_ruangan")
    }
    return True


def save_master_to_supabase(client):
    """Upsert all room capacities and classes into master_ruangan."""
    ruangan = sorted(set(st.session_state.master_tt) | set(st.session_state.master_kelas))
    rows = [
        {
            "nama_ruangan": nama,
            "jumlah_tt": int(st.session_state.master_tt.get(nama, 0)),
            "kelas": str(st.session_state.master_kelas.get(nama, "1")),
        }
        for nama in ruangan
    ]
    if rows:
        return client.table("master_ruangan").upsert(rows).execute()
    return None
