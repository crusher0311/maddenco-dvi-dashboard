import hashlib
import mysql.connector

# ==== DB CONFIG ====
DB_HOST = "localhost"     # Change if needed
DB_USER = "root"          # Your MySQL username
DB_PASS = ""              # Your MySQL password
DB_NAME = "maddenco_dvi"  # The database your app uses

# ==== ADMIN CREDENTIALS ====
username = "admin"
password_plain = "admin@1234"
role = "Admin"
org = "all"

# ==== HASH PASSWORD ====
hashed_password = hashlib.sha256(password_plain.encode()).hexdigest()

# ==== CONNECT TO MYSQL ====
conn = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASS,
    database=DB_NAME
)
cursor = conn.cursor()

# ==== INSERT ADMIN USER ====
insert_query = """
    INSERT INTO users (username, password, role, org)
    VALUES (%s, %s, %s, %s)
"""
cursor.execute(insert_query, (username, hashed_password, role, org))
conn.commit()

print(f"Admin user '{username}' created successfully.")

# ==== CLEANUP ====
cursor.close()
conn.close()