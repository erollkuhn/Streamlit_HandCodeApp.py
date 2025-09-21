import streamlit as st
import pandas as pd
import os

# Structured categories
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

special_cats = ["Other", "Unclassifiable"]


st.title("Immigration Response Classifier")

# Coder ID
coder = st.text_input("Enter your coder ID (e.g., initials):")

# Upload file
uploaded_file = st.file_uploader("Upload dataset (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file and coder:
    try:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        else:
            try:
                df = pd.read_csv(uploaded_file)
            except Exception:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=None, engine="python", encoding="latin1")
    except Exception as e:
        st.error(f"Could not read file: {e}")
        st.stop()

    # Add missing columns
    if "category" not in df.columns:
        df["category"] = ""
    if "coder" not in df.columns:
        df["coder"] = ""

    # Save file path
    save_path = "classified_responses.csv"

    if os.path.exists(save_path):
        saved = pd.read_csv(save_path)
        if len(saved) == len(df):
            df = saved

    # Keep only rows with a response
    df = df[df["value"].notna()]

    # Sort so positives come before negatives
    type_order = {"positive": 0, "negative": 1}
    df = df.sort_values(by=["ResponseId", df["type"].map(type_order), "item"]).reset_index(drop=True)

    # Filter unclassified
    unclassified = df[df["category"] == ""]
    total = df.shape[0]
    done = total - unclassified.shape[0]

    st.write(f"Progress: {done} / {total} responses classified")

    if not unclassified.empty:
        row = unclassified.iloc[0]
        st.write(f"**ResponseId:** {row['ResponseId']} | **Type:** {row['type']} | **Item:** {row['item']}")
        st.info(f"**Response:** {row['value']}")

        if row["type"] == "positive":
            choices = positive_cats + special_cats + ["Not actually positive"]
        else:
            choices = negative_cats + special_cats + ["Not actually negative"]

        choice = st.radio("Select category:", choices)

        if st.button("Save and continue"):
            df.loc[row.name, "category"] = choice
            df.loc[row.name, "coder"] = coder
            df.to_csv(save_path, index=False)
            st.experimental_rerun()
    else:
        st.success("All responses classified! 🎉")
        st.download_button("Download final CSV", df.to_csv(index=False), "classified_responses.csv")
