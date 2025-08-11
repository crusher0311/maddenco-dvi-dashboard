# MaddenCo DVI Dashboard

A Streamlit-based dashboard for managing and visualizing MaddenCo DVI (Digital Vehicle Inspection) data. This app allows users to upload CSV/Excel files containing DVI data, store it in a MySQL database, and generate interactive dashboards with metrics, charts, and PDF reports. It includes user authentication (login/register), role-based access (Admin/User), and data filtering by organization, location, date, and advisor.

Key features:
- Upload and process DVI data files.
- Secure user management with hashed passwords.
- Interactive dashboard with Plotly charts (advisor performance, weekly trends).
- Export filtered data as CSV or PDF reports (using ReportLab).
- Persistent sessions via encrypted cookies.

This project is built with Streamlit, Pandas, SQLAlchemy (for MySQL integration), and other libraries.

## Prerequisites

- **Python**: Version 3.8 or higher (tested on 3.12).
- **MySQL Server**: A running MySQL database server (e.g., via XAMPP, Docker, or a hosted service like AWS RDS). Ensure it's accessible and has the necessary privileges.
- **Git**: To clone the repository.

## Installation

Follow these steps to set up and run the project on your local device.

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/maddenco-dvi-dashboard.git  # Replace with your repo URL
cd maddenco-dvi-dashboard
```

### 2. Install Dependencies
The project uses Python libraries listed in `requirements.txt`. I've reviewed and updated it to include missing dependencies (e.g., for database connections, cookie management, and MySQL interactions).

Updated `requirements.txt` contents (copy this into your file):
```
streamlit
pandas
plotly
kaleido
python-dateutil
reportlab
openpyxl
xlrd
numpy
streamlit-cookies-manager
sqlalchemy
pymysql
mysql-connector-python
```

Install them using pip:
```bash
pip install -r requirements.txt
```

**Notes on dependencies**:
- `streamlit`: Core framework for the web app.
- `pandas`, `numpy`: Data processing and analysis.
- `plotly`, `kaleido`: Interactive charts and image exports.
- `reportlab`: PDF report generation.
- `openpyxl`, `xlrd`: Excel file reading.
- `python-dateutil`: Date parsing utilities.
- `streamlit-cookies-manager`: Persistent login sessions (encrypted cookies).
- `sqlalchemy`, `pymysql`: MySQL database integration via SQLAlchemy.
- `mysql-connector-python`: Direct MySQL connections (used in `create_admin_mysql.py`).

If you encounter issues (e.g., platform-specific), ensure your Python environment is set up correctly (e.g., via virtualenv).

### 3. Set Up MySQL Database
- Start your MySQL server (e.g., via XAMPP control panel).
- Create a new database named `maddenco_dvi` (or edit `config.py` to match your database name).
  ```sql
  CREATE DATABASE maddenco_dvi;
  ```
- The app will automatically create the required tables (`uploads`, `data_rows`, `users`) on first run via `init_db()` in `db.py`.

### 4. Configure Database Credentials
Edit `config.py` with your MySQL details:
```python
# config.py

# MySQL Database Configuration
DB_HOST = "localhost"  # e.g., "localhost" or "127.0.0.1"
DB_PORT = 3306         # Default MySQL port
DB_USER = "root"       # Your MySQL username
DB_PASSWORD = ""       # Your MySQL password (leave empty if none, but set one for security)
DB_NAME = "maddenco_dvi"  # Database name
```

**Security Note**: Never commit `config.py` with real passwords to Git. Use environment variables or a `.env` file in production (e.g., via `python-dotenv` library, which you can add if needed).

### 5. Create Admin User
Run the script to create an initial admin user (username: "admin", password: "admin@1234"). This uses `mysql-connector-python` to insert directly into the database.
```bash
python create_admin_mysql.py
```
- Edit the script if you want to change the default credentials (e.g., username, password, org).
- After running, you'll see: "Admin user 'admin' created successfully."
- The password is hashed using SHA-256 for security.

### 6. Configure Cookie Secret (Important for Security)
In `app.py`, there's a hardcoded cookie password:
```python
COOKIE_PASSWORD = "please_change_this_to_a_long_secret_value_change_me"
```
- Change this to a strong, unique secret (at least 32 characters). It's used to encrypt login cookies.
- In production, load it from an environment variable.

### 7. Run the Application
Start the Streamlit app:
```bash
streamlit run app.py
```
- Open your browser at `http://localhost:8501` (default port).
- Log in with the admin credentials created in Step 5.

## Usage

### Login/Register
- **Login**: Use admin credentials or register a new user (with organization name).
- **Roles**:
  - **Admin**: Full access, can select any organization.
  - **User**: Limited to their organization's data.
- Profile: Update username/password or delete account via the "Open Profile" button.

### Upload Tab
- Upload CSV/Excel files with DVI data.
- Specify organization and store location.
- Preview data, process, and save to database (duplicates are skipped via unique hash).

### Dashboard Tab
- Filter by organization, locations, date range, and advisor.
- View metrics (hours presented/sold, per RO).
- Interactive charts: Advisor performance bar chart, weekly trends line chart.
- Export: CSV or PDF report (includes metrics, charts, and top rows).

## Troubleshooting

- **Database Connection Errors**: Check `config.py` credentials and ensure MySQL is running. Test with `mysql -u root -p`.
- **Missing Libraries**: Rerun `pip install -r requirements.txt`. If on Windows/Mac, ensure build tools are installed (e.g., for pymysql).
- **File Upload Issues**: Ensure files are valid CSV/Excel. Large files may need more memory.
- **PDF Generation Errors**: Verify `kaleido` and `reportlab` are installed correctly.
- **Cookie Issues**: If cookies fail to save, check browser permissions or the secret password.
- **Debugging**: Set `echo=True` in `get_engine()` in `db.py` to log SQL queries.

## Security Considerations
- **Passwords**: Hashed in the database, but use strong passwords. Avoid hardcoded secrets in production.
- **Cookies**: Encrypted, but change the `COOKIE_PASSWORD` and use HTTPS in production.
- **Database**: Restrict MySQL access (e.g., firewall). Don't expose to the internet without authentication.
- **Production Deployment**: Use a WSGI server (e.g., via `streamlit` with Nginx) or host on Streamlit Sharing/Heroku/AWS. Add SSL. Never commit sensitive files to Git—use `.gitignore` for `config.py`.

## Contributing
Fork the repo, make changes, and submit a pull request. Issues and suggestions welcome!

## License
MIT License (or specify your own).
