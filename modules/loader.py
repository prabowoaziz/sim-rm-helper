import pandas as pd
import streamlit as st

@st.cache_data(show_spinner=False)
def get_sheet_names(file_bytes, file_name):
    if file_name.endswith(('.xlsx', '.xls')):
        try:
            xls = pd.ExcelFile(file_bytes)
            return xls.sheet_names
        except Exception as e:
            return [f"ERROR: {str(e)}"]
    return ["Sheet1"]

@st.cache_data(show_spinner=False)
def load_data(file_bytes, file_name, sheet_name=None):
    try:
        if file_name.endswith('.csv'):
            df = pd.read_csv(file_bytes)
        else:
            df = pd.read_excel(file_bytes, sheet_name=sheet_name, header=0)
        return df, None
    except Exception as e:
        return None, str(e)
