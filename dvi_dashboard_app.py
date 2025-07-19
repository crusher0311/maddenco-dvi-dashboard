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

    # Summary Table
    summary = merged_df.groupby("Status Category")["Invoice Total"].agg(["count", "mean"]).reset_index()
    summary = summary.rename(columns={"count": "RO Count", "mean": "Average Ticket"})

    st.subheader("Summary Metrics")
    col1, col2, col3 = st.columns(3)
    for idx, row in summary.iterrows():
        with [col1, col2, col3][idx % 3]:
            st.metric(label=row["Status Category"], value=f"${row['Average Ticket']:.2f}", delta=int(row["RO Count"]))

    st.subheader("All Matched ROs")
    st.dataframe(merged_df[["RO#", "Status Category", "Invoice Total", "Customer", "Vehicle", "Customer Viewed", "Sent"]])
else:
    st.info("Please upload both Autoflow and MaddenCo files to begin.")
