# app.py
import streamlit as st
import pandas as pd
import hashlib
import json
from datetime import datetime, date
from dateutil import parser as dateparse
import re
import io
import plotly.express as px
import plotly.io as pio
from io import BytesIO

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table as RLTable,
    TableStyle, Image as RLImage, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# your DB helpers (unchanged)
from db import init_db, insert_rows, query_filtered, list_orgs, list_locations, save_user, get_user, delete_user, update_user

# Cookie manager for persistent login
# pip install streamlit-cookies-manager
from streamlit_cookies_manager import EncryptedCookieManager

# === Streamlit config ===
st.set_page_config(page_title="MaddenCo DVI Dashboard", layout="wide")

# -----------------------------
# Cookie manager setup
# -----------------------------
# CHANGE THIS to a secure secret in production. Keep it private.
COOKIE_PASSWORD = "please_change_this_to_a_long_secret_value_change_me"

cookies = EncryptedCookieManager(
    prefix="maddenco_dvi_dashboard",
    password=COOKIE_PASSWORD
)

# Wait for cookies to be ready before continuing.
if not cookies.ready():
    # stop execution until cookie manager initialises (it will be ready on next run)
    st.stop()

# -----------------------------
# Session state initialization
# -----------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'role' not in st.session_state:
    st.session_state['role'] = None
if 'user_org' not in st.session_state:
    st.session_state['user_org'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'show_profile' not in st.session_state:
    st.session_state['show_profile'] = False

# -----------------------------
# Restore session from cookies (if present)
# -----------------------------
try:
    if not st.session_state['logged_in']:
        if cookies.get('logged_in') == 'True':
            st.session_state['logged_in'] = True
            st.session_state['username'] = cookies.get('username') or None
            st.session_state['role'] = cookies.get('role') or None
            st.session_state['user_org'] = cookies.get('user_org') or None
except Exception:
    # ignore cookie read errors
    pass

# Helpers to manage login cookies
def save_login_to_cookies(username: str, role: str, user_org: str):
    cookies['logged_in'] = 'True'
    cookies['username'] = username or ""
    cookies['role'] = role or ""
    cookies['user_org'] = user_org or ""
    try:
        cookies.save()
    except Exception as e:
        st.warning(f"Warning: failed to save cookies: {e}")

def clear_login_cookies():
    cookies['logged_in'] = ''
    cookies['username'] = ''
    cookies['role'] = ''
    cookies['user_org'] = ''
    try:
        cookies.save()
    except Exception:
        pass

# --- Initialize DB schema ---
try:
    init_db()
except Exception as e:
    st.error(f"DB init error: {e}")

# -------------------------
# Authentication - Login/Register
# -------------------------

if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = get_user(username)
            if user and user['password'] == hashlib.sha256(password.encode()).hexdigest():
                st.session_state['logged_in'] = True
                st.session_state['role'] = user['role']
                st.session_state['user_org'] = user['org'] if user['role'] == "User" else None
                st.session_state['username'] = username
                save_login_to_cookies(username, st.session_state['role'], st.session_state['user_org'])
                st.rerun()
            else:
                st.error("Invalid credentials")
    with tab2:
        st.subheader("Register")
        new_username = st.text_input("New Username (3-100 characters)")
        new_password = st.text_input("New Password", type="password")
        org_name = st.text_input("Organization Name")
        if st.button("Register"):
            if (3 <= len(new_username) <= 100 and new_password and org_name):
                hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
                if not get_user(new_username):
                    save_user(new_username, hashed_password, "User", org_name)
                    st.success("Registration successful! Please log in.")
                else:
                    st.error("Username already exists.")
            else:
                st.error("Username must be 3-100 characters and all fields are required.")
    st.stop()

# Logout button (top-right area with columns — no sidebar)
if st.session_state['logged_in']:
    col1, col2, col3 = st.columns([8, 1, 1])
    with col1:
        st.empty()
    with col2:
        st.empty()
    with col3:
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.session_state['role'] = None
            st.session_state['user_org'] = None
            st.session_state['username'] = None
            clear_login_cookies()
            st.rerun()

# Profile Overlay
if st.session_state['logged_in']:
    if st.button("Open Profile"):
        st.session_state['show_profile'] = True

    if st.session_state['show_profile']:
        with st.expander("Profile", expanded=True):
            current_user = get_user(st.session_state['username'])
            if current_user:
                st.write(f"Current Username: {current_user['username']}")
                st.write(f"Role: {current_user['role']}")
                if current_user['role'] == "User":
                    st.write(f"Organization: {current_user['org']}")
                
                new_username = st.text_input("New Username (3-100 characters)", value=current_user['username'])
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm New Password", type="password")
                
                if st.button("Update Profile"):
                    if (3 <= len(new_username) <= 100 and ((not new_password and not confirm_password) or (new_password == confirm_password and new_password))):
                        if new_username != current_user['username'] and get_user(new_username):
                            st.error("Username already exists.")
                        else:
                            updates = {}
                            if new_password:
                                updates['password'] = hashlib.sha256(new_password.encode()).hexdigest()
                            if new_username != current_user['username']:
                                delete_user(current_user['username'])
                                save_user(new_username, updates.get('password', current_user['password']), current_user['role'], current_user['org'] if current_user['role'] == "User" else None)
                                st.session_state['username'] = new_username
                                # update cookies as well
                                save_login_to_cookies(st.session_state['username'], st.session_state['role'], st.session_state['user_org'])
                            elif updates:
                                update_user(current_user['username'], updates)
                            st.success("Profile updated!")
                            st.session_state['show_profile'] = False
                            st.rerun()
                    else:
                        st.error("Username must be 3-100 characters, and passwords must match if provided.")

                if st.button("Delete Account"):
                    delete_user(current_user['username'])
                    st.session_state['logged_in'] = False
                    st.session_state['role'] = None
                    st.session_state['user_org'] = None
                    st.session_state['username'] = None
                    st.session_state['show_profile'] = False
                    clear_login_cookies()
                    st.rerun()

        if st.button("Close Profile"):
            st.session_state['show_profile'] = False
            st.rerun()

# ----------------- Helper Functions -----------------
def normalize_advisor(name: str) -> str:
    if not isinstance(name, str):
        return ""
    s = name.strip()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'^(mr\.|mrs\.|ms\.|advisor)\s+', '', s, flags=re.I)
    return s.title()

def try_parse_date(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (datetime, date, pd.Timestamp)):
        return v.date().isoformat()
    try:
        dt = dateparse.parse(str(v), fuzzy=True, dayfirst=False)
        if 1900 <= dt.year <= 2100:
            return dt.date().isoformat()
    except Exception:
        return None
    return None

def safe_float(v):
    try:
        if pd.isna(v):
            return 0.0
        return float(v)
    except Exception:
        return 0.0

def make_row_hash(invoice_no, advisor_canonical, invoice_date, org):
    key = f"{invoice_no}|{advisor_canonical}|{invoice_date}|{org}"
    return hashlib.sha256(key.encode()).hexdigest()

def user_allowed_org_in_value(user_org: str, value: str) -> bool:
    """Return True if user_org is contained in value (case-insensitive)."""
    if user_org is None:
        return False
    try:
        return user_org.strip().lower() in (value or "").lower()
    except Exception:
        return False

# ----------------- Page Navigation -----------------
tab1, tab2 = st.tabs(["Upload", "Dashboard"])

with tab1:
    st.header("📤 Upload MaddenCo DVI Data")
    # If the logged-in user is a 'User', auto-fill org_input and disable editing
    if st.session_state['role'] == "User" and st.session_state['user_org']:
        org_input = st.text_input("Organization (org)", value=st.session_state['user_org'])
    else:
        org_input = st.text_input("Organization (org)", value="DefaultOrg")
    store_location_input = st.text_input("Default Store Location (optional)", value="")
    uploaded_file = st.file_uploader("Upload CSV / Excel file", type=["csv", "xlsx", "xls"])
    st.markdown("---")
    st.write("Upload preview → then click **Process & Save** in main pane.")

    if uploaded_file is not None:
        st.subheader("File preview (first 50 rows)")
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded_file, dtype=object)
            else:
                df = pd.read_excel(uploaded_file, dtype=object)
        except Exception as e:
            st.error(f"Failed to read file: {e}")
            st.stop()

        st.dataframe(df.head(50))

        cols_lower = [c.lower() for c in df.columns]

        def find_col_like(keys):
            for k in keys:
                for i, c in enumerate(cols_lower):
                    if k in c:
                        return df.columns[i]
            return None

        detected = {
            "invoice_no": find_col_like(["invoice", "inv #", "invoice #", "invoice_no"]),
            "invoice_date": find_col_like(["invoice date", "inv date", "date", "invoice_date"]),
            "advisor": find_col_like(["advisor", "technician", "rep", "sales"]),
            "hours_presented": find_col_like(["hours presented", "presented", "hours_p", "hours_presented"]),
            "hours_sold": find_col_like(["hours sold", "sold", "hours_s", "hours_sold"]),
            "ro_id": find_col_like(["ro", "ro #", "repair order", "order #", "ro_id"]),
            "location": find_col_like(["location", "store", "branch", "org"])
        }

        st.subheader("Detected column mapping (edit if needed)")
        mapping = {}
        for k, v in detected.items():
            mapping[k] = st.text_input(k, value=str(v) if v else "")

        if st.button("Process & Save"):
            # --- Upload permission logic ---
            # Admin can upload anything.
            # User: every org value in the CSV (or the org_input if CSV doesn't have an org column) must contain user's org string.
            user_role = st.session_state.get('role')
            user_org = st.session_state.get('user_org')

            # If user is 'User', we will enforce contains-check.
            if user_role == "User" and user_org:
                # If the CSV has an 'org' column, ensure that ALL rows contain user's org (case-insensitive, substring match).
                csv_has_org_col = False
                # check mapping first
                org_col_name = mapping.get("location") or mapping.get("location")  # keep mapping key used earlier for 'location' detected as org
                # Try to find a column called 'org' (variants)
                for col in df.columns:
                    if col.lower() == "org" or "org" in col.lower() or "organization" in col.lower():
                        csv_has_org_col = True
                        org_col_name = col
                        break

                # If CSV has org column, validate its values contain user_org
                if csv_has_org_col and org_col_name in df.columns:
                    # Rows that do NOT contain the user_org in the org field (case-insensitive)
                    invalid_mask = ~df[org_col_name].astype(str).str.lower().str.contains(user_org.strip().lower(), na=False)
                    if invalid_mask.any():
                        st.error(f"Upload denied: CSV 'org' column contains rows that do not match your organization '{user_org}'.\n\n"
                                 "Allowed uploads must have the user's org name contained in the org field (case-insensitive).")
                        st.stop()
                else:
                    # No org column in CSV; fallback to the org_input field user provided in UI.
                    # Ensure provided org_input contains user's org.
                    if not user_allowed_org_in_value(user_org, org_input):
                        st.error(f"Upload denied: provided Organization '{org_input}' does not contain your org '{user_org}'.")
                        st.stop()
            # If we reach here, upload permitted (either Admin or User passed contains checks)
            rows = []
            for idx, row in df.iterrows():
                try:
                    invoice_no = ""
                    if mapping["invoice_no"] and mapping["invoice_no"] in df.columns:
                        val = row[mapping["invoice_no"]]
                        invoice_no = "" if pd.isna(val) else str(val).strip()
                    else:
                        for c in df.columns:
                            if "invoice" in c.lower():
                                val = row[c]
                                invoice_no = "" if pd.isna(val) else str(val).strip()
                                break

                    advisor_raw = ""
                    if mapping["advisor"] and mapping["advisor"] in df.columns:
                        val = row[mapping["advisor"]]
                        advisor_raw = "" if pd.isna(val) else str(val).strip()
                    else:
                        for c in df.columns:
                            if "advisor" in c.lower() or "technician" in c.lower():
                                val = row[c]
                                advisor_raw = "" if pd.isna(val) else str(val).strip()
                                break
                    advisor_canonical = normalize_advisor(advisor_raw)

                    invoice_date = None
                    if mapping["invoice_date"] and mapping["invoice_date"] in df.columns:
                        invoice_date = try_parse_date(row[mapping["invoice_date"]])
                    if not invoice_date:
                        for c in df.columns:
                            parsed = try_parse_date(row[c])
                            if parsed:
                                invoice_date = parsed
                                break

                    hours_presented = 0.0
                    if mapping["hours_presented"] and mapping["hours_presented"] in df.columns:
                        hours_presented = safe_float(row[mapping["hours_presented"]])
                    else:
                        for c in df.columns:
                            if "present" in c.lower() or "hours" in c.lower():
                                try:
                                    val = float(row[c])
                                    hours_presented = val
                                    break
                                except Exception:
                                    pass

                    hours_sold = 0.0
                    if mapping["hours_sold"] and mapping["hours_sold"] in df.columns:
                        hours_sold = safe_float(row[mapping["hours_sold"]])
                    else:
                        for c in df.columns:
                            if "sold" in c.lower():
                                try:
                                    val = float(row[c])
                                    hours_sold = val
                                    break
                                except Exception:
                                    pass

                    ro_id = ""
                    if mapping["ro_id"] and mapping["ro_id"] in df.columns:
                        ro_id = "" if pd.isna(row[mapping["ro_id"]]) else str(row[mapping["ro_id"]]).strip()

                    location = store_location_input or ""
                    # Determine org field value for the row:
                    row_org_val = ""
                    # prefer detected org column if present
                    detected_org_col = None
                    for col in df.columns:
                        if col.lower() == "org" or "org" in col.lower() or "organization" in col.lower():
                            detected_org_col = col
                            break
                    if detected_org_col:
                        row_org_val = "" if pd.isna(row[detected_org_col]) else str(row[detected_org_col]).strip()
                    else:
                        # fallback to mapping["location"] if that's set
                        if mapping.get("location") and mapping["location"] in df.columns:
                            row_org_val = "" if pd.isna(row[mapping["location"]]) else str(row[mapping["location"]]).strip()
                        else:
                            row_org_val = org_input or ""

                    org_val = row_org_val or org_input or location or "DefaultOrg"

                    row_hash = make_row_hash(invoice_no, advisor_canonical, invoice_date, org_val)

                    try:
                        raw_payload = json.dumps(row.to_dict(), default=str)
                    except Exception:
                        raw_payload = json.dumps({c: str(row[c]) for c in df.columns})

                    rows.append({
                        "invoice_no": invoice_no,
                        "advisor": advisor_raw,
                        "advisor_canonical": advisor_canonical,
                        "invoice_date": invoice_date,
                        "hours_presented": hours_presented,
                        "hours_sold": hours_sold,
                        "ro_id": ro_id,
                        "row_hash": row_hash,
                        "raw_payload": raw_payload,
                        "org": org_val,
                        "location": location
                    })
                except Exception as e:
                    st.error(f"Row {idx} parse error: {e}")

            res = insert_rows(rows, filename=uploaded_file.name, org=org_input, store_location=store_location_input)
            st.success(f"Inserted={res['inserted']}, Skipped={res['skipped']}, Errors={res['errors']}. Upload ID={res['upload_id']}")

with tab2:
    st.header("📊 Dashboard")
    # Admin can pick any org. Users should only see their own org; force sel_org to user's org for clarity.
    orgs = list_orgs()
    if st.session_state['role'] == "Admin":
        sel_org = st.selectbox("Organization", options=[""] + orgs, index=0)
        if sel_org == "":
            sel_org = st.text_input("Or enter org manually", value="DefaultOrg")
    else:
        # Non-admin -> show their org only (but allow manual override text box hidden for clarity)
        sel_org = st.session_state.get('user_org') or st.text_input("Or enter org manually", value="DefaultOrg")
        st.markdown(f"**Showing organization:** {sel_org}")

    # Locations: show all locations for selected org (admin) or for user's org (user)
    loc_options = list_locations(sel_org) if sel_org else []
    selected_locations = st.multiselect("Store location(s)", options=loc_options, default=loc_options[:3])
    manual_loc = st.text_input("Add manual locations (comma separated)", value="")
    if manual_loc:
        for x in manual_loc.split(","):
            v = x.strip()
            if v and v not in selected_locations:
                selected_locations.append(v)

    # Date range
    min_date = None
    max_date = None
    try:
        if st.session_state['role'] == "Admin":
            df_tmp = query_filtered() if not sel_org else query_filtered(org=sel_org)
        elif st.session_state['role'] == "User" and st.session_state['user_org']:
            # For users, pull rows for their org using contains logic:
            # We fetch all rows and will filter using pandas afterward because SQL 'LIKE' could be added if desired.
            df_tmp = query_filtered(org=st.session_state['user_org'])
        else:
            df_tmp = pd.DataFrame()
        if not df_tmp.empty:
            if df_tmp["invoice_date"].dtype == "O":
                df_tmp["invoice_date"] = pd.to_datetime(df_tmp["invoice_date"], errors="coerce")
            min_date = df_tmp["invoice_date"].min().date()
            max_date = df_tmp["invoice_date"].max().date()
    except Exception:
        min_date = date.today().replace(day=1)
        max_date = date.today()

    start_date = st.date_input("Start date", value=min_date)
    end_date = st.date_input("End date", value=max_date)
    advisor_filter = st.text_input("Filter advisor (partial name, optional)", value="")

    # Query filtered data using the DB helper (we still pass sel_org for admin; for user we pass their org)
    if st.session_state['role'] == "Admin":
        df_filtered = query_filtered(
            org=sel_org,
            locations=selected_locations if selected_locations else None,
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None
        )
    elif st.session_state['role'] == "User" and st.session_state['user_org']:
        # Query by user's org (DB-level filter), but apply contains-check for rows where org field may include branches.
        df_filtered = query_filtered(
            org=st.session_state['user_org'],
            locations=selected_locations if selected_locations else None,
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None
        )
        # Keep only rows where org column contains user's org (case-insensitive)
        if not df_filtered.empty:
            mask = df_filtered['org'].astype(str).str.lower().str.contains(st.session_state['user_org'].strip().lower(), na=False)
            df_filtered = df_filtered[mask]
    else:
        df_filtered = pd.DataFrame()

    if advisor_filter and not df_filtered.empty:
        df_filtered = df_filtered[df_filtered["advisor_canonical"].str.contains(advisor_filter, case=False, na=False)]

    st.write(f"Rows matching filters: **{len(df_filtered)}**")

    if df_filtered.empty:
        st.info("No rows found — widen filters.")
    else:
        df_filtered["hours_presented"] = pd.to_numeric(df_filtered["hours_presented"], errors="coerce").fillna(0)
        df_filtered["hours_sold"] = pd.to_numeric(df_filtered["hours_sold"], errors="coerce").fillna(0)

        total_presented = df_filtered["hours_presented"].sum()
        total_sold = df_filtered["hours_sold"].sum()
        total_ros = df_filtered["ro_id"].nunique() if "ro_id" in df_filtered.columns else len(df_filtered)
        hp_per_ro = (total_presented / total_ros) if total_ros else 0
        hs_per_ro = (total_sold / total_ros) if total_ros else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rows", len(df_filtered))
        c2.metric("Hours Presented", f"{total_presented:.2f}")
        c3.metric("Hours Sold", f"{total_sold:.2f}")
        c4.metric("Hours Presented / RO", f"{hp_per_ro:.2f}")

        st.markdown("### Advisor performance")
        df_filtered["advisor_canonical"] = df_filtered["advisor_canonical"].fillna("").apply(normalize_advisor)
        adv = df_filtered.groupby("advisor_canonical").agg(
            hours_presented=("hours_presented", "sum"),
            hours_sold=("hours_sold", "sum"),
            ros=("ro_id", pd.Series.nunique)
        ).reset_index().sort_values("hours_sold", ascending=False)
        adv["hp_per_ro"] = adv.apply(lambda r: r["hours_presented"] / r["ros"] if r["ros"] else 0, axis=1)
        adv["hs_per_ro"] = adv.apply(lambda r: r["hours_sold"] / r["ros"] if r["ros"] else 0, axis=1)

        fig = px.bar(
            adv.head(30).melt(id_vars="advisor_canonical", value_vars=["hours_presented", "hours_sold"]),
            x="advisor_canonical", y="value", color="variable", barmode="group",
            labels={"advisor_canonical": "Advisor", "value": "Hours"},
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Week-by-week breakdown")
        df_filtered["invoice_date"] = pd.to_datetime(df_filtered["invoice_date"], errors="coerce")
        df_filtered = df_filtered[~df_filtered["invoice_date"].isna()]
        df_filtered["week_start"] = df_filtered["invoice_date"].dt.to_period("W").apply(lambda r: r.start_time.date())
        weekly = df_filtered.groupby("week_start").agg(
            hours_presented=("hours_presented", "sum"),
            hours_sold=("hours_sold", "sum"),
            ros=("ro_id", pd.Series.nunique)
        ).reset_index().sort_values("week_start")
        weekly["hp_per_ro"] = weekly.apply(lambda r: r["hours_presented"] / r["ros"] if r["ros"] else 0, axis=1)
        weekly["hs_per_ro"] = weekly.apply(lambda r: r["hours_sold"] / r["ros"] if r["ros"] else 0, axis=1)
        st.dataframe(weekly)

        fig_week = px.line(
            weekly, x="week_start", y=["hours_presented", "hours_sold"], markers=True,
            labels={"week_start": "Week Start", "value": "Hours"},
        )
        st.plotly_chart(fig_week, use_container_width=True)

        csv_bytes = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button("Export filtered CSV", data=csv_bytes, file_name="dvi_filtered.csv", mime="text/csv")

        st.markdown("#### Export PDF Report")
        if st.button("Generate PDF Report (ReportLab)"):
            try:
                buf = io.BytesIO()
                doc = SimpleDocTemplate(buf, pagesize=A4,
                                        rightMargin=20, leftMargin=20,
                                        topMargin=20, bottomMargin=20)

                styles = getSampleStyleSheet()
                normal = styles["Normal"]
                title_style = styles["Title"]

                wrap_style = ParagraphStyle(
                    name='Wrap',
                    fontSize=7,
                    leading=9,
                    spaceAfter=2,
                    spaceBefore=2
                )

                elems = []

                elems.append(Paragraph("MaddenCo DVI Performance Report", title_style))
                elems.append(Spacer(1, 8))
                elems.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal))
                elems.append(Spacer(1, 12))

                filters_text = f"Organization: {sel_org or '—'} — Date range: {start_date} to {end_date}"
                if selected_locations:
                    filters_text += f" — Locations: {', '.join(selected_locations)}"
                if advisor_filter:
                    filters_text += f" — Advisor filter: {advisor_filter}"
                elems.append(Paragraph(filters_text, normal))
                elems.append(Spacer(1, 16))

                metrics_table = [
                    ["Metric", "Value"],
                    ["Rows", str(len(df_filtered))],
                    ["Hours Presented", f"{total_presented:.2f}"],
                    ["Hours Sold", f"{total_sold:.2f}"],
                    ["Hours Presented / RO", f"{hp_per_ro:.2f}"],
                    ["Hours Sold / RO", f"{hs_per_ro:.2f}"]
                ]
                mt = RLTable(metrics_table, colWidths=[240, 240])
                mt.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                    ('FONTSIZE', (0, 0), (-1, -1), 10)
                ]))
                elems.append(mt)
                elems.append(Spacer(1, 20))

                fig = px.bar(
                    adv.head(10).melt(id_vars="advisor_canonical", value_vars=["hours_presented", "hours_sold"]),
                    x="advisor_canonical", y="value", color="variable", barmode="group",
                    labels={"advisor_canonical": "Advisor", "value": "Hours"},
                )
                img_bytes = pio.to_image(fig, format="png", width=480, height=240, scale=2)
                img_buffer = BytesIO(img_bytes)
                elems.append(Paragraph("Advisor performance (Hours Presented & Hours Sold)", normal))
                elems.append(Spacer(1, 6))
                elems.append(RLImage(img_buffer, width=480, height=240))
                elems.append(Spacer(1, 20))

                fig_week = px.line(
                    weekly, x="week_start", y=["hours_presented", "hours_sold"], markers=True,
                    labels={"week_start": "Week Start", "value": "Hours"},
                )
                img_bytes = pio.to_image(fig_week, format="png", width=480, height=240, scale=2)
                img_buffer = BytesIO(img_bytes)
                elems.append(Paragraph("Weekly trend (Hours Presented vs Hours Sold)", normal))
                elems.append(Spacer(1, 6))
                elems.append(RLImage(img_buffer, width=480, height=240))
                elems.append(Spacer(1, 20))

                display_rows = df_filtered.head(200).copy().fillna("").astype(str)
                table_data = [display_rows.columns.tolist()]
                for _, row in display_rows.iterrows():
                    wrapped_row = []
                    for val in row:
                        wrapped_row.append(Paragraph(val, wrap_style))
                    table_data.append(wrapped_row)

                col_count = len(display_rows.columns)
                page_width = A4[0] - doc.leftMargin - doc.rightMargin
                min_col_width = 50
                max_col_width = 150
                col_width = max(min_col_width, min(page_width / col_count, max_col_width))

                data_table = RLTable(table_data, colWidths=[col_width] * col_count, repeatRows=1)
                data_table.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]))

                elems.append(Paragraph("Top rows (limited to 200)", styles["Heading3"]))
                elems.append(Spacer(1, 6))
                elems.append(data_table)

                doc.build(elems)

                buf.seek(0)
                pdf_bytes = buf.getvalue()

                st.download_button(
                    label="Download PDF Report (A4)",
                    data=pdf_bytes,
                    file_name=f"dvi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"Failed to generate PDF: {e}")
                st.exception(e)
