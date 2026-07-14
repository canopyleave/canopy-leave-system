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
    st.title("Leave Dashboard")
    entitlements = pd.read_sql("SELECT leave_type, entitlement_days, taken_days FROM leave_entitlements WHERE user_id=?", conn, params=(user['id'],))
    if not entitlements.empty:
        entitlements['remaining'] = entitlements['entitlement_days'] - entitlements['taken_days']
        st.dataframe(entitlements)
    else:
        st.warning("Admin: Set your entitlements in Manage Users.")

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

elif page == "Manage Users" and user['role'] == 'admin':
    st.title("Manage Users & Balances")
    users_with_balance = pd.read_sql("""
        SELECT u.full_name, u.username, u.role,
               GROUP_CONCAT(e.leave_type || ': ' || e.entitlement_days || ' (rem: ' || COALESCE(e.entitlement_days - e.taken_days,0) || ')') as balances
        FROM users u LEFT JOIN leave_entitlements e ON u.id = e.user_id
        WHERE u.is_active=1 GROUP BY u.id
    """, conn)
    st.dataframe(users_with_balance)

    st.subheader("Add New User")
    col1, col2 = st.columns(2)
    with col1:
        new_username = st.text_input("Username")
        new_fullname = st.text_input("Full Name")
    with col2:
        new_password = st.text_input("Password", type="password")
        new_role = st.selectbox("Role", ["user", "admin"])
    new_join = st.date_input("Join Date", date.today())
    if st.button("Create User"):
        conn.execute("INSERT INTO users (username, password, full_name, role, join_date) VALUES (?,?,?,?,?)", (new_username, new_password, new_fullname, new_role, str(new_join)))
        conn.commit()
        db.log_audit(user['username'], "Created User", new_fullname, "")
        st.success("User created!")
        st.rerun()

elif page == "Monthly Calendar" and user['role'] == 'admin':
    st.title("Monthly Leave Calendar")
    selected_month = st.date_input("Select Month", date.today().replace(day=1))
    start_of_month = selected_month.replace(day=1)
    end_of_month = (start_of_month + pd.offsets.MonthEnd(0)).date()
    leaves = pd.read_sql("""
        SELECT (SELECT full_name FROM users WHERE id=user_id) as employee, leave_type, start_date, end_date 
        FROM leave_applications 
        WHERE status='approved' AND start_date <= ? AND end_date >= ?
    """, conn, params=(str(end_of_month), str(start_of_month)))
    if not leaves.empty:
        st.dataframe(leaves)
    else:
        st.info("No approved leave in this month.")

elif page == "Pending Approvals" and user['role'] == 'admin':
    st.title("Pending Approvals")
    pending = pd.read_sql("SELECT id, (SELECT full_name FROM users WHERE id=user_id) as employee, leave_type, start_date, days, reason FROM leave_applications WHERE status='pending'", conn)
    if not pending.empty:
        st.dataframe(pending)
        app_id = st.number_input("Application ID", min_value=1)
        action = st.selectbox("Action", ["Approve", "Reject"])
        if st.button("Process"):
            new_status = "approved" if action == "Approve" else "rejected"
            conn.execute("UPDATE leave_applications SET status=? WHERE id=?", (new_status, app_id))
            conn.commit()
            db.log_audit(user['username'], f"Leave {action}d", "System", f"ID {app_id}")
            st.success(f"Application {action}d!")
    else:
        st.info("No pending applications.")

elif page == "Audit Log" and user['role'] == 'admin':
    st.title("Audit Log")
    logs = pd.read_sql("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 100", conn)
    st.dataframe(logs)

st.sidebar.info("Multi-User Online Version Ready")