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
