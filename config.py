# config.py

# MySQL Database Configuration
DB_HOST = "ncr1.int3rnet.net"
DB_PORT = 3306
DB_USER = "elitein1_maddencodvi"
DB_PASSWORD = "hellotimepaass"
DB_NAME = "elitein1_maddencodvi"
DB_SSL = False  # SSL disabled since no certificates are available

# SQLAlchemy configuration
SQLALCHEMY_ENGINE_OPTIONS = {
    'connect_args': {
        'connect_timeout': 60  # Increased timeout to handle network delays
    }
}

# SQLAlchemy database URI
SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
