import streamlit as st
import pandas as pd
from datetime import datetime, date
import database as db

st.set_page_config(page_title="Canopy Leave System", layout="wide")

# App Password
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Canopy Leave Management")
    pwd = st.text_input("Enter App Password", type="password")
    if st.button("Unlock"):
        if pwd == "canopy2026":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Wrong password")
    st.stop()

db.init_db()

# Login Session
if 'user' not in st.session_state:
    st.session_state.user = None

def login_user():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        conn = db.get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
        if user:
            st.session_state.user = dict(user)
            st.success(f"Welcome {user['full_name']}!")
            st.rerun()
        else:
            st.error("Invalid credentials")

if not st.session_state.user:
    login_user()
    st.stop()

user = st.session_state.user
st.sidebar.title(f"👤 {user['full_name']}")
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# Navigation
page = st.sidebar.radio("Menu", ["Dashboard", "Apply Leave", "My Applications", "Audit Log" if user['role'] == 'admin' else None, "Manage Entitlements" if user['role'] == 'admin' else None])

if page == "Dashboard":
    st.title("Leave Dashboard")
    st.write("Welcome! Your leave balances and pending requests will appear here.")
    st.info("Full dashboard with balances coming in next update.")

elif page == "Manage Entitlements" and user['role'] == 'admin':
    st.title("Manage User Entitlements")
    conn = db.get_db()
    users_df = pd.read_sql("SELECT id, full_name FROM users", conn)
    selected_name = st.selectbox("Select Employee", users_df['full_name'])
    user_id = users_df[users_df['full_name'] == selected_name]['id'].iloc[0]
    
    leave_types = ["AL", "MC", "CCL", "UL", "Reservist"]
    for lt in leave_types:
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**{lt}**")
        with col2:
            new_days = st.number_input(f"Entitlement for {lt}", value=14.0, step=0.5, key=lt)
            if st.button(f"Update {lt}", key=f"btn_{lt}"):
                db.log_audit(user['username'], "Update Entitlement", selected_name, f"{lt} → {new_days} days")
                st.success(f"{lt} updated for {selected_name}")
    
elif page == "Audit Log" and user['role'] == 'admin':
    st.title("Audit Log")
    conn = db.get_db()
    logs = pd.read_sql("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 50", conn)
    st.dataframe(logs)
    if st.button("Export to Excel"):
        logs.to_excel("audit_log.xlsx", index=False)
        st.success("Exported!")

st.sidebar.info("System v1.0 • Audit Logging Active")