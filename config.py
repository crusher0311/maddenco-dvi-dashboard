# config.py
import os

# Prefer a single DATABASE_URL (e.g., from RDS)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
else:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "maddenco_dvi")
    DB_SSL = os.getenv("DB_SSL", "False").lower() in ("true", "1", "yes")

    SQLALCHEMY_DATABASE_URI = URL.create(
        "mysql+pymysql",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )

# SQLAlchemy configuration
SQLALCHEMY_ENGINE_OPTIONS = {
    'connect_args': {
        'connect_timeout': 60  # Increased timeout to handle network delays
    }
}

