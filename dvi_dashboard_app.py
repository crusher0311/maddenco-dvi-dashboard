import streamlit as st
import pandas as pd

st.set_page_config(page_title="Autoflow + MaddenCo Dashboard", layout="wide")
st.title("📊 DVI Performance Dashboard")

# File upload
st.sidebar.header("Upload Files")
autoflow_file = st.sidebar.file_uploader("Upload Autoflow CSV", type=["csv"])
maddenco_file = st.sidebar.file_uploader("Upload MaddenCo Excel", type=["xlsx"])

if autoflow_file and maddenco_file:
    # Load Autoflow CSV
    autoflow_df = pd.read_csv(autoflow_file)
    autoflow_df["RO#"] = autoflow_df["RO#"].astype(str).str.strip()

    # Load MaddenCo Excel (real headers are in row 2)
    maddenco_df = pd.read_excel(maddenco_file, header=1)
    maddenco_df = maddenco_df[maddenco_df["Unnamed: 1"] == "Invoice"]  # Only Invoice rows
    maddenco_df = maddenco_df.rename(columns={
        "Unnamed: 0": "Invoice #",
        "Unnamed: 16": "Invoice Total"
    })
    maddenco_df["Invoice #"] = maddenco_df["Invoice #"].astype(str)
    maddenco_df["RO#"] = maddenco_df["Invoice #"].str[-len(autoflow_df["RO#"].iloc[0]):]

    # Merge on RO#
    merged_df = pd.merge(autoflow_df, maddenco_df, on="RO#", how="left")
    merged_df["Invoice Total"] = pd.to_numeric(merged_df["Invoice Total"], errors='coerce')

    # Define DVI Sent
    merged_df["DVI Sent"] = merged_df.apply(
        lambda row: "Y" if row["Sent"] == "✓" and (row["Sent via Text"] != "--" or row["Sent via Email"] != "--") else "N",
        axis=1
    )

    # Define DVI Status Category
    merged_df["Status Category"] = merged_df.apply(
        lambda row: (
            "Viewed" if row["Customer Viewed"] != "--" else
            "Sent Not Viewed" if row["DVI Sent"] == "Y" else
            "Not Sent"
        ),
        axis=1
    )

    # --- Summary Metrics ---
    summary = merged_df.groupby("Status Category")["Invoice Total"].agg(["count", "mean"]).reset_index()
    summary = summary.rename(columns={"count": "RO Count", "mean": "Average Ticket"})

    st.subheader("Summary Metrics")
    col1, col2, col3 = st.columns(3)
    for idx, row in summary.iterrows():
        with [col1, col2, col3][idx % 3]:
            st.metric(label=row["Status Category"], value=f"${row['Average Ticket']:.2f}", delta=int(row["RO Count"]))

    # --- Completion & Engagement Funnel ---
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

    # --- RO Table ---
    st.subheader("All Matched ROs")
    st.dataframe(merged_df[[
        "RO#", "Status Category", "Invoice Total", "Customer", "Vehicle", "Customer Viewed", "Sent"
    ]])
else:
    st.info("Please upload both Autoflow and MaddenCo files to begin.")
