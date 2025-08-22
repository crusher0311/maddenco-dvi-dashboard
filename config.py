# config.py
# Unified configuration for MaddenCo DVI (MySQL via SQLAlchemy + PyMySQL)
# Works with either:
#   1) DATABASE_URL (preferred in prod), e.g.:
#        mysql+pymysql://user:pass@host:3306/maddenco_dvi
#        NOTE: If your password contains '@', encode it as %40 in DATABASE_URL.
#   2) Individual env vars for local dev:
#        DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

import os
from sqlalchemy.engine import URL

# Prefer a single DATABASE_URL (e.g., for RDS or Docker)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Use the URL as-is (assume caller URL-encoded any special characters)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
else:
    # Fallback to individual values (safe even with special chars)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "maddenco_dvi")

    # Build a safe URL; SQLAlchemy handles proper quoting/encoding
    SQLALCHEMY_DATABASE_URI = URL.create(
        "mysql+pymysql",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )

# Optional engine options (picked up by db.get_engine)
SQLALCHEMY_ENGINE_OPTIONS = {
    "connect_args": {
        "connect_timeout": 60,  # handle slow starts/network hiccups
    },
}

# --------
# Quick usage (PowerShell) for local dev:
#   Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
#   $env:DB_HOST="localhost"
#   $env:DB_PORT="3306"
#   $env:DB_USER="appuser"
#   $env:DB_PASSWORD="1qaz2wsx!QAZ@WSX"
#   $env:DB_NAME="maddenco_dvi"
#
# If you prefer a single URL (remember to encode '@' as %40):
#   $env:DATABASE_URL="mysql+pymysql://appuser:1qaz2wsx!QAZ%40WSX@localhost:3306/maddenco_dvi"
