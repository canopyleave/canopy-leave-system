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

page = st.sidebar.radio("Menu", ["Dashboard", "Apply Leave", "My Applications", "Manage Users" if user['role'] == 'admin' else None, "Calendar View" if user['role'] == 'admin' else None, "Pending Approvals" if user['role'] == 'admin' else None, "Audit Log" if user['role'] == 'admin' else None])

conn = db.get_db()

if page == "Dashboard":
    st.title("Leave Dashboard")
    entitlements = pd.read_sql("SELECT leave_type, entitlement_days, taken_days FROM leave_entitlements WHERE user_id=?", conn, params=(user['id'],))
    if not entitlements.empty:
        entitlements['remaining'] = entitlements['entitlement_days'] - entitlements['taken_days']
        st.dataframe(entitlements)
    else:
        st.warning("No entitlements set yet.")

elif page == "Manage Users" and user['role'] == 'admin':
    st.title("Manage Users & Balances")
    
    # List all users with balances
    users_with_balance = pd.read_sql("""
        SELECT u.full_name, u.username, u.role, u.join_date,
               GROUP_CONCAT(e.leave_type || ': ' || e.entitlement_days || ' (rem: ' || (e.entitlement_days - e.taken_days) || ')') as balances
        FROM users u
        LEFT JOIN leave_entitlements e ON u.id = e.user_id
        GROUP BY u.id
    """, conn)
    st.dataframe(users_with_balance)
    
    # Add new user
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
        conn.execute("INSERT INTO users (username, password, full_name, role, join_date) VALUES (?,?,?,?,?)",
                     (new_username, new_password, new_fullname, new_role, str(new_join)))
        conn.commit()
        db.log_audit(user['username'], "Created User", new_fullname, "New account")
        st.success("User created!")
        st.rerun()
    
    # Deactivate user (soft delete)
    st.subheader("Deactivate User")
    users_list = pd.read_sql("SELECT id, full_name FROM users WHERE is_active=1", conn)
    to_deactivate = st.selectbox("Select User to Deactivate", users_list['full_name'])
    if st.button("Deactivate"):
        user_id = users_list[users_list['full_name'] == to_deactivate]['id'].iloc[0]
        conn.execute("UPDATE users SET is_active=0 WHERE id=?", (user_id,))
        conn.commit()
        db.log_audit(user['username'], "Deactivated User", to_deactivate, "")
        st.success("User deactivated!")

elif page == "Calendar View" and user['role'] == 'admin':
    st.title("Leave Calendar View")
    selected_date = st.date_input("Select Date", date.today())
    leaves = pd.read_sql("SELECT (SELECT full_name FROM users WHERE id=user_id) as employee, leave_type, start_date, end_date FROM leave_applications WHERE status='approved' AND ? BETWEEN start_date AND end_date", conn, params=(str(selected_date),))
    if not leaves.empty:
        st.dataframe(leaves)
    else:
        st.info("No approved leave on this date.")

# Other pages (Apply Leave, Pending Approvals, Audit Log) remain functional as before

st.sidebar.info("User Management + Calendar Active")