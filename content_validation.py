#!/usr/bin/env python3
# exl_dashboard.py — Review, filter, validate, refine, and export outreach outputs
import os, json, re
import pandas as pd
import streamlit as st

from exl_ui import render_top_nav, auto_splash_on_first_load
auto_splash_on_first_load("Loading EXLlead.ai…", min_ms=20)
render_top_nav(active="EXL Lead.AI — Unified Dashboard")
# Optional: collapse sidebar to give the top nav more room (only call once per page)
# st.set_page_config(initial_sidebar_state="collapsed")

from exl_common import (
    migrate_db_schema, list_campaigns, DEFAULT_MODEL, DEFAULT_TEMP,
    get_conn, validate_and_refine, clean_note, ALLOWED_SOFT_CTAS
)

st.set_page_config(page_title="EXL Outreach — Dashboard", page_icon="📊", layout="wide")
st.title("EXL Outreach — Dashboard")

migrate_db_schema()

# ----- Sidebar: user + campaign/run pickers
with st.sidebar:
    st.header("User")
    user_id = st.text_input("Your email or name", value=os.getenv("USER","user@example.com"))

def list_runs(user_id: str, campaign_id: str=None) -> pd.DataFrame:
    conn = get_conn()
    if campaign_id:
        df = pd.read_sql_query(
            "SELECT * FROM runs WHERE user_id=? AND campaign_id=? ORDER BY datetime(created_at) DESC",
            conn, params=[user_id, campaign_id]
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM runs WHERE user_id=? ORDER BY datetime(created_at) DESC",
            conn, params=[user_id]
        )
    conn.close()
    return df

def get_run_outputs(run_id: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM outputs WHERE run_id=?", conn, params=[run_id])
    conn.close()
    return df

# ----- Pick campaign and run
st.subheader("Select data")
camps = list_campaigns(user_id)
if camps.empty:
    st.info("No campaigns yet. Create one in Step 1 (exl_campaign_builder.py).")
    st.stop()

camp_names = ["(All)"] + camps["name"].tolist()
camp_choice = st.selectbox("Campaign", camp_names, index=0)
camp_id = None if camp_choice == "(All)" else camps[camps["name"]==camp_choice].iloc[0]["id"]

runs = list_runs(user_id, campaign_id=camp_id)
if runs.empty:
    st.info("No runs yet. Compose in Step 3 (exl_outreach_composer.py).")
    st.stop()

st.markdown("#### Runs")
st.dataframe(runs[["campaign_name","id","created_at","count","model","temperature"]], use_container_width=True, height=200)

run_id = st.selectbox("Pick a run", options=runs["id"].tolist())

# ----- Load outputs
df = get_run_outputs(run_id)
if df.empty:
    st.warning("No outputs saved for this run yet.")
    st.stop()

# ----- Validation helpers
def starts_with_hi(note: str, first_name: str) -> bool:
    if not isinstance(note, str) or not first_name:
        return False
    return bool(re.match(rf"^\s*hi\s+{re.escape(first_name)}\b", flags=re.I, string=note))

def has_allowed_cta(note: str) -> bool:
    if not isinstance(note, str):
        return False
    low = note.lower()
    return any(cta.lower() in low for cta in ALLOWED_SOFT_CTAS)

# Pick message column
msg_col = "Connect_Note_Final" if "Connect_Note_Final" in df.columns else (
    "Connect_Note_Draft" if "Connect_Note_Draft" in df.columns else None
)
if not msg_col:
    st.error("No Connect_Note columns found in this run.")
    st.stop()

# Derive validation columns
work = df.copy()
work["_first"] = work["fullName"].astype(str).str.strip().str.split().str[0]
work["_len"]   = work[msg_col].astype(str).str.len()
work["_len_ok"] = work["_len"] <= 250
work["_opener_ok"] = work.apply(lambda r: starts_with_hi(str(r.get(msg_col,"")), str(r.get("_first",""))), axis=1)
work["_cta_ok"] = work[msg_col].apply(has_allowed_cta)
work["_url_ok"] = work.get("Linkedin_ID_URL","").astype(str).str.contains("linkedin", case=False, na=False)

# ----- KPI row
c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("Prospects", len(work))
c2.metric("≤ 250 chars", int(work["_len_ok"].sum()))
c3.metric('Opener "Hi [First]"', int(work["_opener_ok"].sum()))
c4.metric("Soft CTA present", int(work["_cta_ok"].sum()))
c5.metric("Valid LinkedIn URL", int(work["_url_ok"].sum()))
c6.metric("Has Email seq", int(work["Email_Sequence_JSON"].astype(str).str.len().gt(2).sum()) if "Email_Sequence_JSON" in work.columns else 0)

st.markdown("### Filters")
colf = st.columns([1,1,1,2])
length_range = colf[0].slider("Length", 0, 300, (0, 250))
need_fix = colf[1].selectbox("Quality filter", ["(Any)","Needs fix","OK"], index=0)
cta_filter = colf[2].selectbox("CTA present", ["(Any)","Yes","No"], index=0)
search = colf[3].text_input("Search text (name/company/message)")

# Apply filters
mask = (work["_len"].between(*length_range))
if need_fix == "Needs fix":
    mask &= (~work["_len_ok"] | ~work["_opener_ok"] | ~work["_cta_ok"])
elif need_fix == "OK":
    mask &= (work["_len_ok"] & work["_opener_ok"] & work["_cta_ok"])
if cta_filter == "Yes":
    mask &= work["_cta_ok"]
elif cta_filter == "No":
    mask &= ~work["_cta_ok"]
if search.strip():
    s = search.lower()
    mask &= (
        work["fullName"].astype(str).str.lower().str.contains(s) |
        work["Company"].astype(str).str.lower().str.contains(s) |
        work[msg_col].astype(str).str.lower().str.contains(s)
    )

filtered = work[mask].copy()

st.markdown("### Preview (filtered)")
show_cols = ["fullName","Title","Company","Email","Linkedin_ID_URL", msg_col, "DM_Message","Quality_Score","Quality_Issues","_len","_opener_ok","_cta_ok"]
show_cols = [c for c in show_cols if c in filtered.columns]
st.dataframe(filtered[show_cols].head(250), use_container_width=True)

# ----- Charts
st.markdown("### QA charts")
clen, copn, ccta = st.columns(3)
clen.bar_chart(filtered["_len"].value_counts().sort_index(), height=220)
copn.bar_chart(filtered["_opener_ok"].value_counts().rename({True:"Yes", False:"No"}), height=220)
ccta.bar_chart(filtered["_cta_ok"].value_counts().rename({True:"Yes", False:"No"}), height=220)

# ----- Actions
st.markdown("---")
st.subheader("Actions on filtered rows")

colA, colB, colC = st.columns(3)
model = colA.text_input("Model for refine", value=DEFAULT_MODEL)
temperature = colB.slider("Temperature", 0.1, 1.2, float(DEFAULT_TEMP), 0.1)
do_refine = colC.button("Refine + Rescore", type="primary")

def update_row_in_db(row_id: str, final_text: str, score: int, issues: str):
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        "UPDATE outputs SET Connect_Note_Final=?, Quality_Score=?, Quality_Issues=? WHERE id=?",
        (final_text, int(score), issues or "", row_id)
    )
    conn.commit(); conn.close()

if do_refine:
    if filtered.empty:
        st.warning("No rows in current filter.")
    else:
        prog = st.progress(0, text="Refining…")
        updates = 0
        for i, (_, r) in enumerate(filtered.iterrows(), start=1):
            rid = r.get("id")
            first = str(r.get("_first","") or "").strip() or (str(r.get("fullName","")).split(" ")[0] if r.get("fullName","") else "there")
            title = str(r.get("Title") or "")
            company = str(r.get("Company") or "")
            draft = clean_note(str(r.get(msg_col,"") or ""), first)
            final, score, issues = validate_and_refine(draft, first, title, company, model)
            try:
                update_row_in_db(rid, final, score, issues)
                updates += 1
            except Exception as e:
                st.error(f"Update failed for {r.get('fullName','')} — {e}")
            prog.progress(i/len(filtered), text=f"Refining… {i}/{len(filtered)}")
        prog.empty()
        st.success(f"Refined & rescored {updates} rows. Reload the run (or change a filter) to see updates.")

# CTA replacement utility
st.markdown("#### CTA utility")
cta_choice = st.selectbox("Replace CTA with", ["(No change)"] + ALLOWED_SOFT_CTAS, index=0)
if st.button("Apply CTA to filtered rows"):
    if cta_choice == "(No change)":
        st.info("Pick a CTA first.")
    else:
        prog = st.progress(0, text="Replacing CTAs…")
        changed = 0
        for i, (_, r) in enumerate(filtered.iterrows(), start=1):
            rid = r.get("id")
            note = str(r.get(msg_col,"") or "")
            # remove existing allowed CTAs and append selected
            base = note
            for cta in ALLOWED_SOFT_CTAS:
                base = re.sub(re.escape(cta), "", base, flags=re.I).strip()
            new_text = (base.rstrip().rstrip(".") + ". " + cta_choice).strip()
            if len(new_text) > 250:
                new_text = new_text[:250].rstrip(". ") + "."
            try:
                update_row_in_db(rid, new_text, int(r.get("Quality_Score") or 0), r.get("Quality_Issues",""))
                changed += 1
            except Exception as e:
                st.error(f"Update failed for {r.get('fullName','')} — {e}")
            prog.progress(i/len(filtered), text=f"Replacing CTAs… {i}/{len(filtered)}")
        prog.empty()
        st.success(f"Updated CTA on {changed} rows.")

# Deduplicate utility (by LinkedIn URL or Email)
st.markdown("#### De-duplicate")
dd_key = st.selectbox("Key", ["Linkedin_ID_URL","Email","(none)"], index=0)
if st.button("Show duplicates (by key)"):
    if dd_key == "(none)":
        st.info("Pick a key first.")
    else:
        dup = filtered[filtered[dd_key].astype(str).ne("")].copy()
        dup["_dup_count"] = dup.groupby(dd_key)[dd_key].transform("count")
        duped = dup[dup["_dup_count"] > 1]
        if duped.empty:
            st.success("No duplicates found in filtered set.")
        else:
            st.dataframe(duped[[dd_key,"fullName","Company",msg_col,"_dup_count"]].sort_values([dd_key,"_dup_count"], ascending=[True,False]), use_container_width=True)

# ----- Downloads
st.markdown("---")
st.subheader("Export")
st.download_button("Download filtered rows (CSV)",
                   data=filtered.to_csv(index=False).encode("utf-8"),
                   file_name="dashboard_filtered.csv", mime="text/csv")

# Flatten email sequence export
if "Email_Sequence_JSON" in filtered.columns and filtered["Email_Sequence_JSON"].astype(str).str.len().gt(2).any():
    rows = []
    for _, r in filtered.iterrows():
        try:
            seq = r.get("Email_Sequence_JSON","")
            if isinstance(seq, str):
                data = json.loads(seq) if seq.strip().startswith("[") else []
            else:
                data = seq or []
            for t in data:
                rows.append({
                    "fullName": r.get("fullName",""),
                    "Company": r.get("Company",""),
                    **t
                })
        except Exception:
            pass
    if rows:
        sdf = pd.DataFrame(rows)
        st.download_button("Download email sequences (flattened)", data=sdf.to_csv(index=False).encode("utf-8"),
                           file_name="dashboard_email_sequences.csv", mime="text/csv")
