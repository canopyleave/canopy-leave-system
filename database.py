import sqlite3
import json
from datetime import datetime

def get_db():
    conn = sqlite3.connect('leaves.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript(''' ... (full schema as before) ''')
    # Seed users and log example
    conn.commit()
    conn.close()

def log_audit(actor, action, target, details):
    conn = get_db()
    conn.execute("INSERT INTO audit_log (timestamp, actor, action, target_user, details) VALUES (?,?,?,?,?)",
                 (datetime.now().isoformat(), actor, action, target, str(details)))
    conn.commit()
    conn.close()