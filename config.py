# config.py

# MySQL Database Configuration
DB_HOST = "35.185.209.55"
DB_PORT = 3306
DB_USER = "kbalvrmy_maddencodvi"
DB_PASSWORD = "hellotimepaass"
DB_NAME = "kbalvrmy_maddencodvi"
DB_SSL = False  # SSL disabled since no certificates are available

# SQLAlchemy configuration
SQLALCHEMY_ENGINE_OPTIONS = {
    'connect_args': {
        'connect_timeout': 60  # Increased timeout to handle network delays
    }
}

# SQLAlchemy database URI
SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


