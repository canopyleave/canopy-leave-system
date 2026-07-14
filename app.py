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

page = st.sidebar.radio("Menu", ["Dashboard", "Apply Leave", "My Applications", "Pending Approvals" if user['role'] == 'admin' else None, "Manage Entitlements" if user['role'] == 'admin' else None, "Audit Log" if user['role'] == 'admin' else None])

conn = db.get_db()

if page == "Dashboard":
    st.title("Leave Dashboard")
    entitlements = pd.read_sql("SELECT leave_type, entitlement_days, taken_days FROM leave_entitlements WHERE user_id=?", conn, params=(user['id'],))
    if not entitlements.empty:
        entitlements['remaining'] = entitlements['entitlement_days'] - entitlements['taken_days']
        st.dataframe(entitlements)
    else:
        st.warning("Admin: Set entitlements first.")

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
        st.success("Application submitted!")

elif page == "Pending Approvals" and user['role'] == 'admin':
    st.title("Pending Leave Approvals")
    pending = pd.read_sql("SELECT id, (SELECT full_name FROM users WHERE id=user_id) as employee, leave_type, start_date, days, reason FROM leave_applications WHERE status='pending'", conn)
    if not pending.empty:
        st.dataframe(pending)
        app_id = st.number_input("Application ID", min_value=1, step=1)
        action = st.selectbox("Action", ["Approve", "Reject"])
        if st.button("Process"):
            new_status = "approved" if action == "Approve" else "rejected"
            conn.execute("UPDATE leave_applications SET status=? WHERE id=?", (new_status, app_id))
            if new_status == "approved":
                # Update taken days (simple)
                app = conn.execute("SELECT user_id, leave_type, days FROM leave_applications WHERE id=?", (app_id,)).fetchone()
                conn.execute("UPDATE leave_entitlements SET taken_days = taken_days + ? WHERE user_id=? AND leave_type=?", (app['days'], app['user_id'], app['leave_type']))
            conn.commit()
            db.log_audit(user['username'], f"Leave {action}d", "System", f"ID {app_id}")
            st.success(f"Application {action}d!")
    else:
        st.info("No pending applications.")

elif page == "Manage Entitlements" and user['role'] == 'admin':
    st.title("Manage Entitlements")
    users = pd.read_sql("SELECT id, full_name FROM users", conn)
    selected_name = st.selectbox("Employee", users['full_name'])
    user_id = users[users['full_name'] == selected_name]['id'].iloc[0]
    for lt in ["AL", "MC", "CCL", "UL", "Reservist"]:
        days = st.number_input(f"{lt} Entitlement", value=14.0, step=0.5)
        if st.button(f"Save {lt}", key=lt):
            conn.execute("INSERT OR REPLACE INTO leave_entitlements (user_id, year, leave_type, entitlement_days, taken_days) VALUES (?,?,?,?,0)",
                         (user_id, date.today().year, lt, days))
            conn.commit()
            db.log_audit(user['username'], "Entitlement Updated", selected_name, f"{lt} = {days}")
            st.success("Saved!")

elif page == "Audit Log" and user['role'] == 'admin':
    st.title("Audit Log")
    logs = pd.read_sql("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 100", conn)
    st.dataframe(logs)
    if st.button("Export Audit Log"):
        logs.to_excel("audit_log.xlsx", index=False)
        st.success("Exported!")

st.sidebar.info("Full System Ready - Deployed with All Features")