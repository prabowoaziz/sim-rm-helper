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
