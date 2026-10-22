import os
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pathguard.db")

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'citizen' CHECK(role IN ('citizen','admin')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        location_name TEXT DEFAULT '',
        latitude REAL NOT NULL CHECK(latitude BETWEEN -90 AND 90),
        longitude REAL NOT NULL CHECK(longitude BETWEEN -180 AND 180),
        image_filename TEXT,
        risk_score INTEGER NOT NULL DEFAULT 0 CHECK(risk_score BETWEEN 0 AND 100),
        status TEXT NOT NULL DEFAULT 'Submitted',
        resolution_note TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE RESTRICT
    );
    CREATE TABLE IF NOT EXISTS report_support (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(report_id, user_id),
        FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS report_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        actor_user_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        note TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE,
        FOREIGN KEY(actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
    );
    CREATE TABLE IF NOT EXISTS authority_profiles (
        user_id INTEGER PRIMARY KEY,
        center_lat REAL NOT NULL CHECK(center_lat BETWEEN -90 AND 90),
        center_lon REAL NOT NULL CHECK(center_lon BETWEEN -180 AND 180),
        radius_km REAL NOT NULL CHECK(radius_km > 0 AND radius_km <= 500),
        is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS authority_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_user_id INTEGER NOT NULL,
        target_user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(actor_user_id) REFERENCES users(id) ON DELETE RESTRICT,
        FOREIGN KEY(target_user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
    CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at);
    """)
    db.commit()
    db.close()

def seed_admin():
    # For local demo only. Change these credentials immediately for any shared deployment.
    email = os.environ.get("PATHGUARD_ADMIN_EMAIL", "admin@pathguard.local")
    password = os.environ.get("PATHGUARD_ADMIN_PASSWORD", "AdminDemo123!")
    db = get_db()
    exists = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if not exists:
        db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'admin')",
                   ("PathGuard Admin", email, generate_password_hash(password)))
        db.commit()
    db.close()
