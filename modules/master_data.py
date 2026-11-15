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
