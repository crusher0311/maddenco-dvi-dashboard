# config.py
# Unified configuration for MaddenCo DVI (MySQL via SQLAlchemy + PyMySQL)

import os
from sqlalchemy.engine import URL  # <-- needed for URL.create

# Prefer a single DATABASE_URL (e.g., for RDS / containers)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Use the provided URL as-is (ensure special chars are URL-encoded in the password)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
else:
    # Fallback to individual env vars (safe for special characters)
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
