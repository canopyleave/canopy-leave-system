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

page = st.sidebar.radio("Menu", ["Dashboard", "Apply Leave", "My Applications", "Manage Entitlements" if user['role'] == 'admin' else None, "Audit Log" if user['role'] == 'admin' else None])

if page == "Dashboard":
    st.title("Leave Dashboard")
    conn = db.get_db()
    entitlements = pd.read_sql("SELECT leave_type, entitlement_days, taken_days FROM leave_entitlements WHERE user_id=?", conn, params=(user['id'],))
    if not entitlements.empty:
        entitlements['remaining'] = entitlements['entitlement_days'] - entitlements['taken_days']
        st.dataframe(entitlements)
    else:
        st.warning("No entitlements set. Admin please set them.")

elif page == "Apply Leave":
    st.title("Apply for Leave")
    leave_type = st.selectbox("Leave Type", ["AL", "MC", "CCL", "UL", "Reservist"])
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")
    half_day = st.checkbox("Half Day")
    reason = st.text_area("Reason")
    if st.button("Submit Application"):
        days = 0.5 if half_day else ((end_date - start_date).days + 1)
        # Simple insert
        conn = db.get_db()
        conn.execute("INSERT INTO leave_applications (user_id, leave_type, start_date, end_date, days, half_day, reason, status) VALUES (?,?,?,?,?,?,?,?)",
                     (user['id'], leave_type, start_date, end_date, days, half_day, reason, "pending"))
        conn.commit()
        db.log_audit(user['username'], "Applied Leave", user['full_name'], f"{leave_type} ({days} days)")
        st.success("Application submitted for approval!")

elif page == "Manage Entitlements" and user['role'] == 'admin':
    st.title("Manage Entitlements")
    conn = db.get_db()
    users = pd.read_sql("SELECT id, full_name FROM users", conn)
    selected_name = st.selectbox("Select Employee", users['full_name'])
    user_id = users[users['full_name'] == selected_name]['id'].iloc[0]
    for lt in ["AL", "MC", "CCL", "UL", "Reservist"]:
        days = st.number_input(f"{lt} Entitlement", value=14.0, step=0.5)
        if st.button(f"Save {lt}", key=lt):
            # Simple update or insert
            conn.execute("INSERT OR REPLACE INTO leave_entitlements (user_id, year, leave_type, entitlement_days) VALUES (?,?,?,?)",
                         (user_id, date.today().year, lt, days))
            conn.commit()
            db.log_audit(user['username'], "Updated Entitlement", selected_name, f"{lt} = {days}")
            st.success(f"Saved for {selected_name}")

elif page == "Audit Log" and user['role'] == 'admin':
    st.title("Audit Log")
    conn = db.get_db()
    logs = pd.read_sql("SELECT * FROM audit_log ORDER BY timestamp DESC", conn)
    st.dataframe(logs)

st.sidebar.success("System Ready - Next: Approval Workflow & Reports")