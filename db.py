"""
DB helpers for MaddenCo DVI Dashboard (MySQL).
Usage:
  from db import get_engine, init_db, insert_rows, query_filtered, get_uploads, delete_upload_rows,
                 save_user, get_user, delete_user, update_user
"""

import json
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
import config  # expects SQLALCHEMY_DATABASE_URI (string or URL) and optional SQLALCHEMY_ENGINE_OPTIONS (dict)

# Build SQLAlchemy engine from the unified URI in config.py
def get_engine() -> Engine:
    # Pick up optional engine options (e.g., connect_args / timeouts) if present
    engine_opts = getattr(config, "SQLALCHEMY_ENGINE_OPTIONS", {}) or {}
    # echo=False in production; set True for debugging queries
    return create_engine(config.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True, echo=False, **engine_opts)

def init_db():
    """Create uploads, data_rows, and users tables if they don't exist."""
    engine = get_engine()
    with engine.begin() as conn:
        # Uploads meta
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INT AUTO_INCREMENT PRIMARY KEY,
            filename VARCHAR(255),
            org VARCHAR(255),
            store_location VARCHAR(255),
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
        # Data rows: raw_payload TEXT (JSON string). Unique constraint to prevent duplicates.
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS data_rows (
            id INT AUTO_INCREMENT PRIMARY KEY,
            upload_id INT,
            invoice_no VARCHAR(255),
            advisor VARCHAR(255),
            advisor_canonical VARCHAR(255),
            invoice_date DATE,
            hours_presented DOUBLE DEFAULT 0,
            hours_sold DOUBLE DEFAULT 0,
            ro_id VARCHAR(255),
            row_hash VARCHAR(128),
            raw_payload LONGTEXT,
            org VARCHAR(255),
            location VARCHAR(255),
            FOREIGN KEY (upload_id) REFERENCES uploads(id) ON DELETE CASCADE,
            UNIQUE KEY uk_row_hash_org (row_hash, org)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
        # Users table for authentication
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            username VARCHAR(255) PRIMARY KEY,
            password VARCHAR(255) NOT NULL,
            role ENUM('Admin', 'User') NOT NULL,
            org VARCHAR(255),
            UNIQUE KEY uk_username (username)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
    return True

# Insert many rows (list of dicts). Returns (inserted, skipped, errors)
def insert_rows(rows, filename=None, org=None, store_location=None):
    """
    rows: list of dicts with keys:
      invoice_no, advisor, advisor_canonical, invoice_date (ISO str or None),
      hours_presented (float), hours_sold (float), ro_id, row_hash, raw_payload, org, location
    """
    engine = get_engine()
    inserted = 0
    skipped = 0
    errors = 0
    upload_id = None
    with engine.begin() as conn:
        # record upload
        conn.execute(
            text("INSERT INTO uploads (filename, org, store_location) VALUES (:fn, :org, :loc)"),
            {"fn": filename or "", "org": org or "", "loc": store_location or ""}
        )
        # get last insert id
        upload_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        # insert rows
        for r in rows:
            try:
                conn.execute(text("""
                    INSERT INTO data_rows
                    (upload_id, invoice_no, advisor, advisor_canonical, invoice_date,
                     hours_presented, hours_sold, ro_id, row_hash, raw_payload, org, location)
                    VALUES
                    (:upload_id, :invoice_no, :advisor, :advisor_canonical, :invoice_date,
                     :hours_presented, :hours_sold, :ro_id, :row_hash, :raw_payload, :org, :location)
                """), {
                    "upload_id": int(upload_id),
                    "invoice_no": r.get("invoice_no"),
                    "advisor": r.get("advisor"),
                    "advisor_canonical": r.get("advisor_canonical"),
                    "invoice_date": r.get("invoice_date"),
                    "hours_presented": r.get("hours_presented", 0),
                    "hours_sold": r.get("hours_sold", 0),
                    "ro_id": r.get("ro_id"),
                    "row_hash": r.get("row_hash"),
                    "raw_payload": json.dumps(r.get("raw_payload")) if not isinstance(r.get("raw_payload"), str) else r.get("raw_payload"),
                    "org": r.get("org") or org,
                    "location": r.get("location")
                })
                inserted += 1
            except SQLAlchemyError:
                # likely unique constraint violation -> skip
                skipped += 1
            except Exception:
                errors += 1
    return {"upload_id": upload_id, "inserted": inserted, "skipped": skipped, "errors": errors}

# Query filtered rows (returns pandas DataFrame from SQL)
def query_filtered(org=None, locations=None, start_date=None, end_date=None):
    import pandas as pd
    engine = get_engine()
    query = "SELECT * FROM data_rows WHERE 1=1"
    params = {}
    if org:
        query += " AND org = :org"
        params["org"] = org
    if locations:
        # locations is list
        placeholders = ",".join([f":loc{i}" for i in range(len(locations))])
        query += f" AND location IN ({placeholders})"
        for i, loc in enumerate(locations):
            params[f"loc{i}"] = loc
    if start_date:
        query += " AND invoice_date >= :start_date"
        params["start_date"] = start_date
    if end_date:
        query += " AND invoice_date <= :end_date"
        params["end_date"] = end_date
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params, parse_dates=["invoice_date"])
    return df

# Convenience: list distinct orgs and locations
def list_orgs():
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT DISTINCT org FROM uploads WHERE org IS NOT NULL AND org <> ''")).fetchall()
    return [r[0] for r in rows]

def list_locations(org=None):
    engine = get_engine()
    params = {}
    q = "SELECT DISTINCT location FROM data_rows WHERE location IS NOT NULL AND location <> ''"
    if org:
        q += " AND org = :org"
        params["org"] = org
    with engine.begin() as conn:
        rows = conn.execute(text(q), params).fetchall()
    return [r[0] for r in rows]

# Upload history & admin functions
def get_uploads(limit=200):
    import pandas as pd
    engine = get_engine()
    with engine.begin() as conn:
        df = pd.read_sql(
            text("SELECT id, filename, org, store_location, uploaded_at FROM uploads ORDER BY uploaded_at DESC LIMIT :lim"),
            conn,
            params={"lim": int(limit)},
            parse_dates=["uploaded_at"]
        )
    return df

def delete_upload(upload_id):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM uploads WHERE id = :id"), {"id": int(upload_id)})
    return True

def delete_upload_rows(upload_id):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM data_rows WHERE upload_id = :id"), {"id": int(upload_id)})
    return True

# User management functions
def save_user(username, password, role, org=None):
    """Save a new user with hashed password."""
    engine = get_engine()
    with engine.begin() as conn:
        try:
            conn.execute(
                text("INSERT INTO users (username, password, role, org) VALUES (:username, :password, :role, :org)"),
                {"username": username, "password": password, "role": role, "org": org}
            )
        except SQLAlchemyError as e:
            raise Exception(f"User registration failed: {str(e)}")

def get_user(username):
    """Retrieve user details by username."""
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT username, password, role, org FROM users WHERE username = :username"),
            {"username": username}
        ).fetchone()
        if row:
            return {"username": row[0], "password": row[1], "role": row[2], "org": row[3]}
        return None

def delete_user(username):
    """Delete a user by username."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM users WHERE username = :username"),
            {"username": username}
        )
    return True

def update_user(username, updates):
    """Update user details (e.g., password)."""
    engine = get_engine()
    with engine.begin() as conn:
        update_query = text("UPDATE users SET password = :password WHERE username = :username")
        conn.execute(update_query, {"username": username, "password": updates.get("password")})
    return True
