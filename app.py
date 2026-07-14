import streamlit as st
import pandas as pd
from datetime import datetime, date
import database as db
from holidays import SG_HOLIDAYS

st.set_page_config(page_title="Canopy Leave System", layout="wide")

APP_PASSWORD = "canopy2026"

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Canopy Leave Management")
    pwd = st.text_input("Enter App Password", type="password")
    if st.button("Unlock"):
        if pwd == APP_PASSWORD:
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
            st.success(f"Welcome {user['full_name']}!")
            st.rerun()
        else:
            st.error("Invalid credentials")

if not st.session_state.user:
    login_user()
    st.stop()

user = st.session_state.user
st.sidebar.title(f"👤 {user['full_name']} ({user['role']})")
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

page = st.sidebar.radio("Menu", ["Dashboard", "Apply Leave", "My Applications", "Manage Users" if user['role'] == 'admin' else None, "Monthly Calendar" if user['role'] == 'admin' else None, "Pending Approvals" if user['role'] == 'admin' else None, "Audit Log" if user['role'] == 'admin' else None])

conn = db.get_db()

if page == "Dashboard":
    st.title(f"Welcome, {user['full_name']}")
    st.subheader("Your Leave Balance")
    entitlements = pd.read_sql("SELECT leave_type, entitlement_days, taken_days FROM leave_entitlements WHERE user_id=?", conn, params=(user['id'],))
    if not entitlements.empty:
        entitlements['remaining'] = entitlements['entitlement_days'] - entitlements['taken_days']
        st.dataframe(entitlements.style.format({"entitlement_days": "{:.1f}", "taken_days": "{:.1f}", "remaining": "{:.1f}"}))
    else:
        st.warning("No entitlements set yet. Contact Admin.")

elif page == "Apply Leave":
    st.title("Apply for Leave")
    leave_type = st.selectbox("Leave Type", ["AL", "MC", "CCL", "UL", "Reservist"])
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")
    half_day = st.checkbox("Half Day")
    reason = st.text_area("Reason")
    if st.button("Submit Application"):
        days = 0.5 if half_day else ((end_date - start_date).days + 1)
        conn.execute("INSERT INTO leave_applications (user_id, leave_type, start_date, end_date, days, half_day, reason, status) VALUES (?,?,?,?,?,?,?,?)",
                     (user['id'], leave_type, str(start_date), str(end_date), days, half_day, reason, "pending"))
        conn.commit()
        db.log_audit(user['username'], "Leave Applied", user['full_name'], f"{leave_type} ({days} days)")
        st.success("Application submitted for approval!")

# Other pages (Manage Users, Calendar, Approvals, Audit Log) remain the same as previous

st.sidebar.info("Individual Balance View Active")