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
    # Sort positives first, then negatives
    # ----------------------------
    type_order = {"positive": 0, "negative": 1}
    df["type_order"] = df["type"].map(type_order)
    df = df.sort_values(by=["ResponseId", "type_order", "item"]).reset_index(drop=True)

    # ----------------------------
    # Save path
    # ----------------------------
    save_path = "classified_responses.csv"
    if os.path.exists(save_path):
        saved = pd.read_csv(save_path)
        if len(saved) == len(df):
            df = saved

    # ----------------------------
    # Session state for current row
    # ----------------------------
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0

    # Filter unclassified rows
    unclassified = df[df["category"] == ""].reset_index(drop=True)
    total = df.shape[0]
    done = total - len(unclassified)

    st.write(f"Progress: {done} / {total} responses classified")

    # ----------------------------
    # Show current response
    # ----------------------------
    if not unclassified.empty and st.session_state.current_index < len(unclassified):
        row = unclassified.iloc[st.session_state.current_index]
        st.write(f"**ResponseId:** {row['ResponseId']} | **Type:** {row['type']} | **Item:** {row['item']}")
        st.info(f"**Response:** {row['value']}")

        # Select categories based on type
        if row["type"] == "positive":
            choices = positive_cats + special_cats + ["Not actually positive"]
        else:
            choices = negative_cats + special_cats + ["Not actually negative"]

        choice = st.radio("Select category:", choices, key=f"choice_{st.session_state.current_index}")

        if st.button("Save and continue"):
            # Save coding
            df.loc[row.name, "category"] = choice
            df.loc[row.name, "coder"] = coder
            df.to_csv(save_path, index=False)
            # Advance to next response
            st.session_state.current_index += 1

    else:
        st.success("All responses classified! 🎉")
        st.download_button(
            "Download final CSV",
            df.drop(columns=["type_order"]).to_csv(index=False),
            "classified_responses.csv",
            mime="text/csv"
        )
