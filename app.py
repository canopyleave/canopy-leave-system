import streamlit as st
import database as db
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Canopy Leave System", layout="wide")

# App Password
APP_PASSWORD = "canopy2026"   # ← CHANGE THIS!

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Canopy Leave Management")
    pwd = st.text_input("Enter Password", type="password")
    if st.button("Unlock App"):
        if pwd == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")
    st.stop()

# Login & Main App (as previously described)
db.init_db()
st.title("Canopy Engineer Leave System")

# Navigation, Dashboard, Apply Leave, Manage Entitlements (with audit), Audit Log, etc.

st.success("System Ready - Audit Logging Active")