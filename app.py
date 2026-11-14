import streamlit as st
from modules.loader import get_sheet_names, load_data

st.set_page_config(
    page_title="SIM-RM Helper",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    h1 {
        color: #0ea5e9;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏥 SIM-RM Helper")
st.caption("Asisten Laporan Rekam Medis — Upload, Olah, Laporkan")
st.markdown("---")

if "df_mentah" not in st.session_state:
    st.session_state.df_mentah = None

tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload", "🔁 Mutasi", "🏥 BOR", "📊 Laporan"])

with tab1:
    st.subheader("📤 Upload Data Mentah")
    st.info("💡 Silakan upload file Excel/CSV hasil tarikan sistem SIMRS.")

    uploaded = st.file_uploader("Pilih file", type=["xlsx", "xls", "csv"], label_visibility="collapsed")

    if uploaded:
        file_bytes = uploaded.read()
        sheet_names = get_sheet_names(file_bytes, uploaded.name)

        if not sheet_names:
            st.error("❌ Gagal membaca file. Pastikan format file tidak corrupt.")
        elif sheet_names[0].startswith("ERROR:"):
            st.error(f"❌ Detail Error: {sheet_names[0]}")
        else:
            selected_sheet = sheet_names[0]
            if len(sheet_names) > 1:
                st.write("---")
                selected_sheet = st.selectbox("📑 Pilih Sheet yang mau diolah:", sheet_names)

            with st.spinner("Membaca data..."):
                df, error = load_data(file_bytes, uploaded.name, selected_sheet)

            if error:
                st.error(f"❌ Error saat membaca data: {error}")
            else:
                st.session_state.df_mentah = df
                st.success(f"✅ Berhasil membaca **{uploaded.name}** (Sheet: `{selected_sheet}`)")

                st.write("")
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Baris", f"{df.shape[0]:,}")
                col2.metric("Total Kolom", df.shape[1])
                col3.metric("Status", "Siap Diproses")

                st.write("")
                pv1, pv2 = st.tabs(["📋 Preview Data (5 Baris)", "🔍 Daftar Kolom"])

                with pv1:
                    st.dataframe(df.head(), use_container_width=True)

                with pv2:
                    kolom_df = {"No": range(1, len(df.columns)+1), "Nama Kolom": list(df.columns)}
                    st.dataframe(kolom_df, use_container_width=True, hide_index=True)
    else:
        st.write("")
        st.info("Belum ada file yang di-upload.")

with tab2:
    st.subheader("🔁 Track Perpindahan Kamar")
    st.write("Fitur dalam pengembangan.")

with tab3:
    st.subheader("🏥 BOR & Indikator")
    st.write("Fitur dalam pengembangan.")

with tab4:
    st.subheader("📊 Laporan RL & Akreditasi")
    st.write("Fitur dalam pengembangan.")
