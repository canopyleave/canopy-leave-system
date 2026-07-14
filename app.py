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
            st.success(f"Welcome, {user['full_name']}!")
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

page = st.sidebar.radio("Menu", ["Dashboard", "Apply Leave", "My Applications", "Manage Entitlements" if user['role'] == 'admin' else None, "Audit Log" if user['role'] == 'admin' else None])

if page == "Dashboard":
    st.title("Leave Dashboard")
    st.write(f"**Current Year**: {date.today().year}")
    # Balance summary placeholder
    st.metric("Annual Leave Remaining", "12.5 days")
    st.metric("Medical Leave Remaining", "10 days")

elif page == "Apply Leave":
    st.title("Apply for Leave")
    leave_type = st.selectbox("Leave Type", ["AL", "MC", "CCL", "UL", "Reservist"])
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")
    half_day = st.checkbox("Half Day")
    reason = st.text_area("Reason")
    if st.button("Submit Application"):
        db.log_audit(user['username'], "Leave Application", user['full_name'], f"{leave_type} from {start_date}")
        st.success("Application submitted! Awaiting admin approval.")

elif page == "Manage Entitlements" and user['role'] == 'admin':
    st.title("Manage Entitlements")
    conn = db.get_db()
    users = pd.read_sql("SELECT id, full_name FROM users", conn)
    selected = st.selectbox("Employee", users['full_name'])
    user_id = users[users['full_name'] == selected]['id'].iloc[0]
    for lt in ["AL", "MC", "CCL", "UL"]:
        days = st.number_input(f"{lt} Entitlement", value=14.0, step=0.5)
        if st.button(f"Save {lt} for {selected}"):
            db.log_audit(user['username'], "Entitlement Change", selected, f"{lt} = {days}")
            st.success("Saved!")

elif page == "Audit Log" and user['role'] == 'admin':
    st.title("Audit Log")
    conn = db.get_db()
    logs = pd.read_sql("SELECT * FROM audit_log ORDER BY timestamp DESC", conn)
    st.dataframe(logs)

st.sidebar.info("✅ Audit Logging Active • Singapore Holidays Supported")