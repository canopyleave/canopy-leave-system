import sqlite3
import json
from datetime import datetime

def get_db():
    conn = sqlite3.connect('leaves.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            join_date TEXT,
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS leave_entitlements (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            year INTEGER,
            leave_type TEXT,
            entitlement_days REAL DEFAULT 0,
            taken_days REAL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS leave_applications (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            leave_type TEXT,
            start_date TEXT,
            end_date TEXT,
            days REAL,
            half_day TEXT,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            approved_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            actor TEXT,
            action TEXT,
            target_user TEXT,
            details TEXT
        );
    ''')
    
    # Seed basic users
    users = [
        ("admin1", "adminpass123", "Admin One", "admin", "2020-01-01"),
        ("tan_eu_keat", "pass123", "Tan Eu Keat", "user", "2023-01-01"),
    ]
    for u in users:
        conn.execute("INSERT OR IGNORE INTO users (username, password, full_name, role, join_date) VALUES (?,?,?,?,?)", u)
    
    conn.commit()
    conn.close()

def log_audit(actor, action, target_user, details):
    conn = get_db()
    conn.execute("""
        INSERT INTO audit_log (timestamp, actor, action, target_user, details)
        VALUES (?,?,?,?,?)
    """, (datetime.now().isoformat(), actor, action, target_user, str(details)))
    conn.commit()
    conn.close()