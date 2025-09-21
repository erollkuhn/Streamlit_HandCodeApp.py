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
placeholder = "-- Select a category --"

# ----------------------------
# Helper: build stable key for a row
# ----------------------------
def build_key_series(df):
    # Ensure item is a string without trailing .0 if it was numeric
    item_str = df["item"].astype(str).str.replace(r"\.0$", "", regex=True)
    return df["ResponseId"].astype(str).str.strip() + "||" + df["type"].astype(str).str.strip() + "||" + item_str.str.strip()

# ----------------------------
# Streamlit UI
# ----------------------------
st.title("Immigration Response Classifier")

coder = st.text_input("Enter your coder ID (e.g., initials):").strip()

uploaded_file = st.file_uploader("Upload dataset (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file and coder:

    # ----------------------------
    # Load master dataset robustly
    # ----------------------------
    try:
        if uploaded_file.name.lower().endswith(".xlsx"):
            df_master = pd.read_excel(uploaded_file)
        else:
            uploaded_file.seek(0)
            df_master = pd.read_csv(uploaded_file, engine="python", sep=None, encoding="utf-8")
    except Exception as e:
        st.error(f"Could not read file: {e}")
        st.stop()

    # ----------------------------
    # Ensure expected columns exist
    # ----------------------------
    for col in ["ResponseId", "type", "item", "value"]:
        if col not in df_master.columns:
            st.error(f"Uploaded file missing required column: {col}")
            st.stop()

    # Add needed columns if missing on master (we won't overwrite master labels)
    if "category" not in df_master.columns:
        df_master["category"] = ""
    if "coder" not in df_master.columns:
        df_master["coder"] = ""

    # Keep only rows with a response
    df_master = df_master[df_master["value"].notna()].reset_index(drop=True)

    # ----------------------------
    # Sort all positives first, then negatives (ignore respondent ordering)
    # ----------------------------
    type_order = {"positive": 0, "negative": 1}
    df_master["type_order"] = df_master["type"].map(type_order)
    df_master = df_master.sort_values(by=["type_order"]).reset_index(drop=True)
    df_master.drop(columns=["type_order"], inplace=True)

    # Build stable row keys
    df_master["_key"] = build_key_series(df_master)

    # ----------------------------
    # Coder-specific save file
    # ----------------------------
    safe_coder = "".join(ch for ch in coder if ch.isalnum() or ch in ("_", "-")).strip()
    coder_save_path = f"classified_responses_{safe_coder}.csv"

    if os.path.exists(coder_save_path):
        try:
            coder_saved = pd.read_csv(coder_save_path, dtype=str)
        except Exception:
            coder_saved = pd.read_csv(coder_save_path, engine="python", sep=None, encoding="utf-8", dtype=str)
        # normalize columns
        for c in ["ResponseId", "type", "item", "category", "coder"]:
            if c not in coder_saved.columns:
                coder_saved[c] = ""
        coder_saved["_key"] = build_key_series(coder_saved.assign(value=""))  # value dummy for key build
        # consider only coder rows with non-empty category as done
        coder_done_keys = set(coder_saved.loc[coder_saved["category"].astype(str).str.strip() != "", "_key"])
    else:
        coder_saved = pd.DataFrame(columns=["ResponseId", "type", "item", "category", "coder", "_key"])
        coder_done_keys = set()

    # ----------------------------
    # Determine next row for this coder
    # ----------------------------
    all_keys = list(df_master["_key"])
    # find first index in master where key not in coder_done_keys
    next_idx_series = df_master[~df_master["_key"].isin(coder_done_keys)].index
    next_index = int(next_idx_series.min()) if not next_idx_series.empty else None

    # Store current index per coder in session_state
    state_key = f"current_index_{safe_coder}"
    if state_key not in st.session_state:
        st.session_state[state_key] = next_index

    # Recompute progress numbers
    done = len(coder_done_keys)
    total = df_master.shape[0]
    st.write(f"Progress for **{coder}**: {done} / {total} responses coded")

    # Always allow coder to download their current progress (if any)
    if not coder_saved.empty:
        st.download_button(
            "Download your current progress",
            coder_saved.to_csv(index=False),
            f"classified_responses_{safe_coder}_progress.csv",
            mime="text/csv"
        )

    # ----------------------------
    # Show current response (if any)
    # ----------------------------
    cur = st.session_state.get(state_key, None)
    if cur is not None and cur in df_master.index:
        row = df_master.loc[cur]
        st.markdown(f"### {'✅ Positive' if str(row['type']).lower()=='positive' else '❌ Negative'} Response")
        st.info(f"**Response text:** {row['value']}")

        # Choose options for this row's type
        if str(row["type"]).lower() == "positive":
            choices = [placeholder] + positive_cats + special_cats + ["Not actually positive"]
        else:
            choices = [placeholder] + negative_cats + special_cats + ["Not actually negative"]

        # Use a form (prevents weird rerun behavior)
        with st.form(key=f"form_{safe_coder}_{cur}"):
            choice = st.radio("Select category:", choices, key=f"choice_{safe_coder}_{cur}")
            submit = st.form_submit_button("Save and continue")

        if submit:
            if choice == placeholder:
                st.warning("Please select a category before continuing.")
            else:
                # Update coder_saved: update row if exists else append
                this_key = row["_key"]
                # build row dict to save
                row_to_save = {
                    "ResponseId": row["ResponseId"],
                    "type": row["type"],
                    "item": row["item"],
                    "category": choice,
                    "coder": coder,
                    "_key": this_key
                }

                if not coder_saved.empty and this_key in set(coder_saved["_key"]):
                    # update existing entry
                    coder_saved.loc[coder_saved["_key"] == this_key, ["category", "coder"]] = [choice, coder]
                else:
                    # append new entry
                    coder_saved = pd.concat([coder_saved, pd.DataFrame([row_to_save])], ignore_index=True)

                # Save coder-specific CSV
                coder_saved.to_csv(coder_save_path, index=False)

                # recompute keys done and next index
                coder_done_keys = set(coder_saved.loc[coder_saved["category"].astype(str).str.strip() != "", "_key"])
                next_idx_series = df_master[~df_master["_key"].isin(coder_done_keys)].index
                next_index = int(next_idx_series.min()) if not next_idx_series.empty else None
                st.session_state[state_key] = next_index

                # let Streamlit rerun and show next response automatically
                st.rerun()

    else:
        st.success(f"All responses for **{coder}** are classified (or no available rows). 🎉")
        # allow download final coder CSV (if exists)
        if os.path.exists(coder_save_path):
            st.download_button(
                "Download your final CSV",
                pd.read_csv(coder_save_path).to_csv(index=False),
                f"classified_responses_{safe_coder}.csv",
                mime="text/csv"
            )
        else:
            st.info("No saved classifications yet for this coder.")
