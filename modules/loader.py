import pandas as pd
import streamlit as st
import io

@st.cache_data(show_spinner=False)
def get_sheet_names(file_bytes, file_name):
    if file_name.endswith(('.xlsx', '.xls')):
        try:
            # Bungkus bytes ke BytesIO
            file_obj = io.BytesIO(file_bytes)
            xls = pd.ExcelFile(file_obj)
            return xls.sheet_names
        except Exception as e:
            return [f"ERROR: {str(e)}"]
    return ["Sheet1"]

@st.cache_data(show_spinner=False)
def load_data(file_bytes, file_name, sheet_name=None):
    try:
        # Bungkus bytes ke BytesIO
        file_obj = io.BytesIO(file_bytes)
        
        if file_name.endswith('.csv'):
            df = pd.read_csv(file_obj)
        else:
            df = pd.read_excel(file_obj, sheet_name=sheet_name, header=0)
        return df, None
    except Exception as e:
        return None, str(e)
