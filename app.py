import streamlit as st
import pandas as pd
import os

# ----------------------------
# Structured categories
# ----------------------------
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

# ----------------------------
# Streamlit UI
# ----------------------------
st.title("Immigration Response Classifier")

coder = st.text_input("Enter your coder ID (e.g., initials):")

uploaded_file = st.file_uploader("Upload dataset (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file and coder:

    # ----------------------------
    # Load dataset
    # ----------------------------
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

    # Keep only rows with a response
    df = df[df["value"].notna()].reset_index(drop=True)

    # ----------------------------
    # Sort all positives first, then negatives
    # ----------------------------
    type_order = {"positive": 0, "negative": 1}
    df["type_order"] = df["type"].map(type_order)
    df = df.sort_values(by=["type_order"]).reset_index(drop=True)

    # ----------------------------
    # Coder-specific save path
    # ----------------------------
    save_path = f"classified_responses_{coder}.csv"

    if os.path.exists(save_path):
        saved = pd.read_csv(save_path)
        if "category" not in saved.columns:
            saved["category"] = ""
        saved["category"] = saved["category"].fillna("")
        saved["coder"] = saved.get("coder", "")

        df = df.merge(
            saved[["ResponseId", "type", "item", "category", "coder"]],
            on=["ResponseId", "type", "item"],
            how="left",
            suffixes=("", "_saved")
        )
        df["category"] = df["category_saved"].combine_first(df["category"])
        df["coder"] = df["coder_saved"].combine_first(df["coder"])
        df = df.drop(columns=["category_saved", "coder_saved"])

    # ----------------------------
    # Session state for coder-specific index
    # ----------------------------
    state_key = f"current_index_{coder}"
    if state_key not in st.session_state:
        # resume where coder left off
        already_done = df[df["coder"] == coder].shape[0]
        st.session_state[state_key] = already_done

    # Filter unclassified rows for this coder
    unclassified = df[(df["category"] == "") | (df["coder"] == coder and df["category"] != "")].reset_index(drop=True)
    total = df.shape[0]
    done = df[df["coder"] == coder]["category"].notna().sum()

    st.write(f"Progress for {coder}: {done} / {total} responses classified")

    # ----------------------------
    # S
