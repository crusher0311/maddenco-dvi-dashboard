import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

st.set_page_config(page_title="Autoflow + MaddenCo Dashboard", layout="wide")
st.title("📊 DVI Performance Dashboard")

# --- SQLite Setup ---
conn = sqlite3.connect("dvi_data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS dvi_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location TEXT,
    ro_number TEXT,
    status_category TEXT,
    invoice_total REAL,
    customer TEXT,
    vehicle TEXT,
    customer_viewed TEXT,
    sent TEXT,
    upload_date TEXT
)
""")
conn.commit()

# --- Sidebar Upload & Location ---
st.sidebar.header("Upload Files")

autoflow_file = st.sidebar.file_uploader("Upload Autoflow CSV", type=["csv"])
maddenco_file = st.sidebar.file_uploader("Upload MaddenCo Excel", type=["xlsx"])

store_options = sorted([
    "108 - Decatur/IL", "112 - Havana/IL", "118 - Lincoln/IL",
    "119 - Litchfield/IL", "122 - Mattoon/IL", "124 - Mt Zion/IL",
    "138 - Washington/IL", "142 - Lawrenceville/IL", "215 - McCordsville/IN",
    "Other (Manual Entry)"
])

location = None
if autoflow_file and maddenco_file:
    selected_option = st.sidebar.selectbox("Select Store Location for This Upload", ["-- Select a Store --"] + store_options)

    if selected_option == "-- Select a Store --":
        st.sidebar.warning("Please select a store location to continue.")
    elif selected_option == "Other (Manual Entry)":
        manual_entry = st.sidebar.text_input("Enter custom store ID and name (e.g., 301 - Springfield/IL)")
        if manual_entry:
            location = manual_entry
        else:
            st.sidebar.warning("Please enter a location.")
    else:
        location = selected_option

# --- Dev Tool to Clear Database ---
with st.sidebar.expander("⚠️ Dev Tools"):
    if st.button("Clear all uploaded data from database"):
        cursor.execute("DELETE FROM dvi_reports")
        conn.commit()
        st.warning("All records have been deleted from the database.")

# --- File Processing ---
if autoflow_file and maddenco_file and location:
    store_id = location.split(" - ")[0].strip()

    autoflow_df = pd.read_csv(autoflow_file)
    autoflow_df["RO#"] = autoflow_df["RO#"].astype(str).str.strip()

    maddenco_df = pd.read_excel(maddenco_file, header=1)
    maddenco_df = maddenco_df[maddenco_df["Unnamed: 1"] == "Invoice"]
    maddenco_df = maddenco_df.rename(columns={
        "Unnamed: 0": "Invoice #",
        "Unnamed: 16": "Invoice Total"
    })
    maddenco_df["Invoice #"] = maddenco_df["Invoice #"].astype(str)
    maddenco_df["RO#"] = maddenco_df["Invoice #"].str[-len(autoflow_df["RO#"].iloc[0]):]

    merged_df = pd.merge(autoflow_df, maddenco_df, on="RO#", how="left")
    merged_df["Invoice Total"] = pd.to_numeric(merged_df["Invoice Total"], errors='coerce')

    merged_df["DVI Sent"] = merged_df.apply(
        lambda row: "Y" if row["Sent"] == "✓" and (row["Sent via Text"] != "--" or row["Sent via Email"] != "--") else "N",
        axis=1
    )

    merged_df["Status Category"] = merged_df.apply(
        lambda row: (
            "Viewed" if row["Customer Viewed"] != "--" else
            "Sent Not Viewed" if row["DVI Sent"] == "Y" else
            "Not Sent"
        ),
        axis=1
    )

    try:
        rows_to_insert = merged_df[["RO#", "Status Category", "Invoice Total", "Customer", "Vehicle", "Customer Viewed", "Sent"]]
        for _, row in rows_to_insert.iterrows():
            cursor.execute("""
                INSERT INTO dvi_reports (
                    location, ro_number, status_category, invoice_total,
                    customer, vehicle, customer_viewed, sent, upload_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                store_id,
                str(row["RO#"]),
                row["Status Category"],
                row["Invoice Total"],
                row["Customer"],
                row["Vehicle"],
                row["Customer Viewed"],
                row["Sent"]
            ))
        conn.commit()
        st.success(f"✅ Uploaded data saved to database under location: {location}")
    except Exception as e:
        st.error(f"❌ Failed to insert data: {e}")

    summary = merged_df.groupby("Status Category")["Invoice Total"].agg(["count", "mean"]).reset_index()
    summary = summary.rename(columns={"count": "RO Count", "mean": "Average Ticket"})

    st.subheader("Summary Metrics")
    col1, col2, col3 = st.columns(3)
    for idx, row in summary.iterrows():
        with [col1, col2, col3][idx % 3]:
            st.metric(label=row["Status Category"], value=f"${row['Average Ticket']:.2f}", delta=int(row["RO Count"]))

    total_invoices = maddenco_df["Invoice #"].nunique()
    matched_invoices = merged_df["Invoice #"].notna().sum()
    dvi_completion_pct = (matched_invoices / total_invoices) * 100 if total_invoices > 0 else 0

    dvi_completed = merged_df[merged_df["Invoice #"].notna()]
    dvi_sent = dvi_completed[dvi_completed["DVI Sent"] == "Y"]
    sent_pct = (len(dvi_sent) / len(dvi_completed)) * 100 if len(dvi_completed) > 0 else 0

    dvi_viewed = dvi_sent[dvi_sent["Customer Viewed"] != "--"]
    viewed_pct = (len(dvi_viewed) / len(dvi_sent)) * 100 if len(dvi_sent) > 0 else 0

    st.subheader("DVI Completion & Engagement Metrics")
    c1, c2, c3 = st.columns(3)
    c1.metric("DVI Completion %", f"{dvi_completion_pct:.1f}%", f"{matched_invoices}/{total_invoices} invoices")
    c2.metric("DVI Sent %", f"{sent_pct:.1f}%", f"{len(dvi_sent)}/{len(dvi_completed)} completed")
    c3.metric("DVI Viewed %", f"{viewed_pct:.1f}%", f"{len(dvi_viewed)}/{len(dvi_sent)} sent")

    st.subheader("All Matched ROs")
    st.dataframe(merged_df[[
        "RO#", "Status Category", "Invoice Total", "Customer", "Vehicle", "Customer Viewed", "Sent"
    ]])
else:
    st.info("Please upload both files and select a store location to begin.")

# --- View Stored Reports ---
st.header("📍 View Stored Reports by Location")

cursor.execute("SELECT DISTINCT location FROM dvi_reports ORDER BY location ASC")
locations = [row[0] for row in cursor.fetchall()]

if locations:
    selected_loc = st.selectbox("Select a location to view stored data", locations)

    st.markdown("### 📅 Filter by Upload Date")
    date_range = st.date_input(
        "Select date range",
        value=[datetime.today() - timedelta(days=30), datetime.today()]
    )

    start_date = date_range[0].strftime("%Y-%m-%d")
    end_date = date_range[1].strftime("%Y-%m-%d")

    df = pd.read_sql_query("""
        SELECT * FROM dvi_reports
        WHERE location = ? AND DATE(upload_date) BETWEEN ? AND ?
    """, conn, params=(selected_loc, start_date, end_date))

    if not df.empty:
        summary = df.groupby("status_category")["invoice_total"].agg(["count", "mean"]).reset_index()
        summary = summary.rename(columns={"count": "RO Count", "mean": "Average Ticket"})

        st.subheader(f"📊 Summary Metrics for {selected_loc}")
        col1, col2, col3 = st.columns(3)
        for idx, row in summary.iterrows():
            with [col1, col2, col3][idx % 3]:
                st.metric(label=row["status_category"], value=f"${row['Average Ticket']:.2f}", delta=int(row["RO Count"]))

        total_invoices = df["ro_number"].nunique()
        completed = df[df["status_category"].isin(["Viewed", "Sent Not Viewed"])]
        sent = completed[completed["sent"] == "✓"]
        viewed = sent[sent["customer_viewed"] != "--"]

        st.subheader("📈 DVI Completion & Engagement Metrics")
        c1, c2, c3 = st.columns(3)
        c1.metric("DVI Completion %", f"{(len(completed) / total_invoices) * 100:.1f}%", f"{len(completed)}/{total_invoices} invoices")
        c2.metric("DVI Sent %", f"{(len(sent) / len(completed)) * 100:.1f}%", f"{len(sent)}/{len(completed)} completed")
        c3.metric("DVI Viewed %", f"{(len(viewed) / len(sent)) * 100:.1f}%", f"{len(viewed)}/{len(sent)} sent")

        st.subheader("📋 Stored RO Table")
        st.dataframe(df[[
            "ro_number", "status_category", "invoice_total", "customer", "vehicle", "customer_viewed", "sent", "upload_date"
        ]])
    else:
        st.warning(f"No records found for {selected_loc} in selected date range.")
else:
    st.info("No stored data yet. Upload files to begin saving to the database.")
