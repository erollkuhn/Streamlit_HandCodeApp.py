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
    # Load dataset robustly
    # ----------------------------
    try:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        else:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, engine="python", sep=None, encoding="utf-8")
    except Exception as e:
        st.error(f"Could not read file: {e}")
        st.stop()

    # ----------------------------
    # Add missing columns
    # ----------------------------
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
    df = df.sort_values(by=["type_order"]).reset_index(drop=True)

    # ----------------------------
    # Save path for progress
    # ----------------------------
    save_path = "classified_responses.csv"

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
    # Session state for current row
    # ----------------------------
    if "current_index" not in st.session_state:
        first_unclassified = df[df["category"] == ""].index.min()
        st.session_state.current_index = first_unclassified if pd.notna(first_unclassified) else None

    # ----------------------------
    # Progress
    # ----------------------------
    unclassified = df[df["category"] == ""]
    total = df.shape[0]
    done = total - len(unclassified)
    st.write(f"Progress: {done} / {total} responses classified")

    # ----------------------------
    # Show current response
    # ----------------------------
    if st.session_state.current_index is not None and st.session_state.current_index in df.index:
        row = df.loc[st.session_state.current_index]

        st.markdown(f"### {'✅ Positive' if row['type'] == 'positive' else '❌ Negative'} Response")
        st.info(f"**Response text:** {row['value']}")

        if row["type"] == "positive":
            choices = positive_cats + special_cats + ["Not actually positive"]
        else:
            choices = negative_cats + special_cats + ["Not actually negative"]

        # Use a form to safely handle submission
        with st.form(key=f"form_{st.session_state.current_index}"):
            choice = st.radio("Select category:", choices, index=None, key=f"choice_{st.session_state.current_index}")
            submit = st.form_submit_button("Save and continue")

        if submit:
            df.loc[st.session_state.current_index, "category"] = choice
            df.loc[st.session_state.current_index, "coder"] = coder
            df.to_csv(save_path, index=False)

            # Move to next unclassified row
            next_unclassified = df[df["category"] == ""].index.min()
            if pd.notna(next_unclassified):
                st.session_state.current_index = next_unclassified
            else:
                st.session_state.current_index = None

    else:
        st.success("All responses classified! 🎉")
        st.download_button(
            "Download final CSV",
            df.drop(columns=["type_order"]).to_csv(index=False),
            "classified_responses.csv",
            mime="text/csv"
        )
