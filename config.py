# config.py
# Unified configuration for MaddenCo DVI (MySQL via SQLAlchemy + PyMySQL)
# Backward-compatible: exposes both SQLALCHEMY_DATABASE_URI and DB_* fields.

import os
from sqlalchemy.engine import URL
from sqlalchemy.engine.url import make_url  # for parsing DATABASE_URL

# Prefer a single DATABASE_URL (e.g., for RDS / containers)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Use provided URL as-is (ensure special chars like '@' are URL-encoded)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL

    # --- Backward compatibility: populate DB_* so older code doesn't break ---
    try:
        _parsed = make_url(DATABASE_URL)
        DB_USER = _parsed.username or ""
        DB_PASSWORD = _parsed.password or ""
        DB_HOST = _parsed.host or "localhost"
        DB_PORT = int(_parsed.port or 3306)
        DB_NAME = _parsed.database or "maddenco_dvi"
    except Exception:
        # Safe fallbacks if parsing fails
        DB_USER = ""
        DB_PASSWORD = ""
        DB_HOST = "localhost"
        DB_PORT = 3306
        DB_NAME = "maddenco_dvi"
else:
    # Fallback to individual env vars (safe with special chars)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "maddenco_dvi")

    SQLALCHEMY_DATABASE_URI = URL.create(
        "mysql+pymysql",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )

# SQLAlchemy engine options picked up by db.get_engine()
SQLALCHEMY_ENGINE_OPTIONS = {
    "connect_args": {
        "connect_timeout": 60,  # handle slow starts / network hiccups
    }
}
