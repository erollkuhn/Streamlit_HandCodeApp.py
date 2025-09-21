import streamlit as st
import pandas as pd
import os

# Categories
positive_cats = [
    "Brings highly skilled workers that will help British firms innovate",
    "Helps balance and support an aging population",
    "Enriches and diversifies British culture and society",
    "Provides needed staffing for certain sectors and public services",
    "Gives people an opportunity for a better life in the UK"
]

negative_cats = [
    "Takes jobs away from and decreases wages for British people",
    "Contributes to overcrowding and depletes limited resources",
    "Brings ideas and values that are incompatible with British culture",
    "Makes British communities less safe and less cohesive",
    "Puts pressure on public finances and services"
]

all_cats = positive_cats + negative_cats + ["Other / Unclassifiable"]

st.title("Immigration Response Classifier")

# Ask coder for their ID (saved with each row)
coder = st.text_input("Enter your coder ID (e.g., initials):")

import io

uploaded_file = st.file_uploader("Upload the dataset (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file and coder:
    try:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        else:
            # Try UTF-8 CSV first
            try:
                df = pd.read_csv(uploaded_file)
            except Exception:
                # Retry with automatic delimiter detection and encoding fallback
                uploaded_file.seek(0)  # reset file pointer
                df = pd.read_csv(uploaded_file, sep=None, engine="python", encoding="latin1")
    except Exception as e:
        st.error(f"Could not read file: {e}")
        st.stop()

    if "category" not in df.columns:
        df["category"] = ""
    if "coder" not in df.columns:
        df["coder"] = ""

    # Save progress in Streamlit’s cloud storage
    save_path = "classified_responses.csv"

    if os.path.exists(save_path):
        saved = pd.read_csv(save_path)
        if len(saved) == len(df):
            df = saved  # resume

    unclassified = df[df["value"].notna() & (df["category"] == "")]
    total = df[df["value"].notna()].shape[0]
    done = total - unclassified.shape[0]

    st.write(f"Progress: {done} / {total} responses classified")

    if not unclassified.empty:
        row = unclassified.iloc[0]
        st.write(f"**ResponseId:** {row['ResponseId']} | **Type:** {row['type']} | **Item:** {row['item']}")
        st.info(f"**Response:** {row['value']}")

        choice = st.radio("Select category:", all_cats)

        if st.button("Save and continue"):
            df.loc[row.name, "category"] = choice
            df.loc[row.name, "coder"] = coder
            df.to_csv(save_path, index=False)
            st.experimental_rerun()
    else:
        st.success("All responses classified! 🎉")
        st.download_button("Download final CSV", df.to_csv(index=False), "classified_responses.csv")
