#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Streamlit page: EXL Autopilot (Campaigns + Research + Email Compose + Send)
UI-only layer:
- Campaign name / description (saved to DB)
- LLM provider settings (Azure / Ollama / HF)
- CSV upload + column mapping
- Research via exl_research_job (DuckDuckGo)
- Email generation via exl_autopilot_job (4-touch)
- Email sending via exl_send_job (Outlook or SMTP, with schedule)
- Campaign & Runs dashboard

All heavy logic lives under jobs/ modules.
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

# ---------------------- PATHS & IMPORTS ----------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
JOBS_DIR = ROOT_DIR / "jobs"

for p in (ROOT_DIR, JOBS_DIR):
    if str(p) not in sys.path:
        sys.path.append(str(p))

# Optional top nav
try:
    from exl_ui import render_top_nav
except Exception:  # noqa: BLE001
    render_top_nav = None

from exl_research_job import ddg_insights, topic_from_insights, clean_focus_snippet, strip_urls
from exl_send_job import send_email_sequence
from exl_autopilot_job import (
    init_db,
    upsert_campaign,
    list_campaigns,
    create_run,
    finalize_run,
    insert_result,
    list_runs,
    generate_email_sequence,
)

# ---------------------- STREAMLIT CONFIG ----------------------
st.set_page_config(
    page_title="EXL Autopilot Mode",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "About": "EXLead.AI Autopilot — EXL internal outreach orchestrator (campaigns, research, emails, send).",
    },
)

if render_top_nav:
    try:
        render_top_nav(active="Automation")
    except Exception:
        pass

st.title("EXLead.AI — Autopilot Agent")
st.caption("Campaign-aware outreach automation: research → compose → send → dashboard.")


# ---------------------- SIDEBAR SETTINGS ----------------------
with st.sidebar:
    st.header("⚙️ Run Settings")

    # Campaign info snapshot (just for reference in sidebar)
    st.markdown("**Campaign snapshot** (configure in main tab):")
    st.text("Name, description and owner\nare stored in the Autopilot DB.")

    st.subheader("LLM Provider")
    provider = st.radio("Provider", ["azure", "ollama", "huggingface"], index=0)

    # LLM provider settings (saved only into config_json for reference; runtime uses these directly)
    az_endpoint = az_deployment = az_api_version = az_api_key = az_api_key2 = None
    ollama_model = None
    hf_model = None
    hf_max_new_tokens = 1800

    if provider == "azure":
        az_endpoint = st.text_input("Azure endpoint", value="https://lead-swat-ai.openai.azure.com")
        az_deployment = st.text_input("Deployment name", value="gpt-5-mini")
        az_api_version = st.text_input("API version", value="2025-03-01-preview")
        az_api_key = st.text_input("API key #1", value="", type="password")
        az_api_key2 = st.text_input("API key #2 (optional)", value="", type="password")
    elif provider == "ollama":
        ollama_model = st.text_input("Ollama model", value="llama3.2:latest")
    else:
        hf_model = st.text_input("HF model", value="Qwen/Qwen2.5-1.5B-Instruct")
        hf_max_new_tokens = st.number_input("HF max_new_tokens", 64, 4096, 1800, 64)

    st.subheader("Email sending")
    send_method = st.radio("Send via", ["Outlook desktop (recommended)", "SMTP"], index=0)

    smtp_conf: Optional[Dict[str, Any]] = None
    if send_method == "SMTP":
        smtp_host = st.text_input("SMTP host", value="smtp.office365.com")
        smtp_port = st.number_input("SMTP port", 1, 65535, 587)
        smtp_username = st.text_input("SMTP username", value="")
        smtp_password = st.text_input("SMTP password", value="", type="password")
        smtp_from = st.text_input("From address", value="")
        smtp_use_tls = st.checkbox("Use STARTTLS", value=True)
        smtp_conf = {
            "host": smtp_host,
            "port": int(smtp_port),
            "username": smtp_username,
            "password": smtp_password,
            "from_addr": smtp_from or smtp_username,
            "use_tls": bool(smtp_use_tls),
        }

    st.subheader("Sequence schedule (days from now)")
    t1 = st.number_input("Touch 1 delay", 0, 365, 0)
    t2 = st.number_input("Touch 2 delay", 0, 365, 7)
    t3 = st.number_input("Touch 3 delay", 0, 365, 14)
    t4 = st.number_input("Touch 4 delay", 0, 365, 21)
    touch_delays_days = [t1, t2, t3, t4]

    st.subheader("Run Mode")
    dry_run = st.checkbox("Dry run (no actual sending)", value=True)
    max_rows = st.number_input("Max prospects to process", 1, 5000, 50)
    show_raw = st.checkbox("Show raw LLM outputs", value=False)
    force_template_emails = st.checkbox("Force template emails (no LLM)", value=False)


# ---------------------- HELPER: LLM KWARGS ----------------------
def llm_kwargs_for(provider_name: str) -> Dict[str, Any]:
    if provider_name == "azure":
        return dict(
            az_endpoint=az_endpoint,
            az_deployment=az_deployment,
            az_api_version=az_api_version,
            az_api_key=az_api_key,
            az_api_key2=az_api_key2,
            max_tokens=1800,
            temperature=0.2,
        )
    if provider_name == "huggingface":
        return dict(
            hf_model=hf_model or "Qwen/Qwen2.5-1.5B-Instruct",
            max_tokens=hf_max_new_tokens,
            temperature=0.2,
        )
    return dict(
        ollama_model=ollama_model or "llama3.2:latest",
        max_tokens=1800,
        temperature=0.2,
    )


def cell_str(row: pd.Series, col: Optional[str]) -> str:
    if not col:
        return ""
    if col not in row.index:
        return ""
    v = row[col]
    return str(v).strip() if pd.notna(v) else ""


def guess_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = list(df.columns)
    lower_map = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    for cand in candidates:
        norm = cand.lower().replace(" ", "")
        for col in cols:
            if col.lower().replace(" ", "") == norm:
                return col
    return None


# ---------------------- TABS ----------------------
tab_run, tab_dash = st.tabs(["🚀 Run Autopilot", "📊 Campaign Dashboard"])

# ===================== TAB 1 – RUN AUTOPILOT =====================
with tab_run:
    st.markdown("### 1️⃣ Campaign configuration")

    db_path = init_db()  # ensure DB exists

    c1, c2, c3 = st.columns([2, 3, 2])
    with c1:
        campaign_name = st.text_input("Campaign name", value="Autopilot — Wave 1")
    with c2:
        campaign_description = st.text_area(
            "Campaign description",
            value="CX / Analytics executive outreach — Autopilot generated emails.",
            height=70,
        )
    with c3:
        owner_email = st.text_input("Owner (your email, optional)", value="")

    st.markdown("### 2️⃣ Content & SGU context")

    col_a, col_b = st.columns(2)
    with col_a:
        resource_profile = st.text_input("Resource profile / theme", "Customer experience transformation")
        fewshot_snippets = st.text_area(
            "Template style snippets (tone only, not content)",
            value="Opening: I recently came across your work in...\nEXL intro: We're a data and AI company (Nasdaq: EXLS)...",
            height=90,
        )
    with col_b:
        sgu_options = [
            "Analytics & AI Services",
            "DE & AI Solutions",
            "Domain Ops",
            "F&A Ops",
            "Domain Platforms",
            "Payment Integrity Services",
            "Data Management",
        ]
        sgu_alignment = st.multiselect(
            "SGU alignment",
            options=sgu_options,
            default=["Analytics & AI Services"],
        )
        profile_notes_default = st.text_area("Default PROFILE_NOTES (optional)", "", height=70)
        global_rag_context = st.text_area("Global RAG_CONTEXT (optional)", "", height=90)

    st.markdown("### 3️⃣ Upload prospects & map columns")

    uploaded = st.file_uploader(
        "Upload CSV (required columns: Name, Title, Company, Email; optional: LinkedIn URL, Industry)",
        type=["csv"],
    )

    if uploaded is not None:
        df = pd.read_csv(uploaded)
        st.markdown("#### Preview")
        st.dataframe(df.head(20), use_container_width=True)

        cols = list(df.columns)
        opt = ["— None —"] + cols

        def col_select(label: str, candidates: List[str], key: str) -> Optional[str]:
            default = guess_col(df, candidates)
            idx = opt.index(default) if default in opt else 0
            sel = st.selectbox(label, opt, index=idx, key=key)
            return None if sel == "— None —" else sel

        c1, c2, c3 = st.columns(3)
        with c1:
            name_col = col_select("Name", ["Name", "Full Name"], "name_col")
            first_name_col = col_select("First name", ["First Name", "Firstname"], "fname_col")
        with c2:
            title_col = col_select("Title", ["Title", "Job Title"], "title_col")
            company_col = col_select("Company", ["Company", "Account"], "company_col")
        with c3:
            email_col = col_select("Email", ["Email", "Work Email", "Business Email"], "email_col")
            li_col = col_select("LinkedIn URL", ["LinkedIn URL", "LinkedIn", "LI URL"], "li_col")
            industry_col = col_select("Industry", ["Industry", "Sector", "Vertical"], "industry_col")

        if not name_col or not title_col or not company_col or not email_col:
            st.error("Please map at least Name, Title, Company, and Email.")
        else:
            st.markdown("### 4️⃣ Generate & send")

            col_flags = st.columns(3)
            with col_flags[0]:
                generate_email_seq = st.checkbox("Generate 4-touch emails", True)
            with col_flags[1]:
                send_email_flag = st.checkbox("Send emails via selected method", True)
            with col_flags[2]:
                st.caption("If dry run is ON, nothing is actually sent.")

            run_btn = st.button("🚀 Run Autopilot for this CSV", type="primary")
            log_box = st.empty()
            status_box = st.empty()

            if run_btn:
                # Upsert campaign first
                config_json = json.dumps(
                    {
                        "provider": provider,
                        "send_method": send_method,
                        "resource_profile": resource_profile,
                        "sgu_alignment": sgu_alignment,
                    },
                    ensure_ascii=False,
                )
                campaign_id = upsert_campaign(
                    campaign_name, campaign_description, owner_email, config_json, db_path=db_path
                )

                df_run = df.head(int(max_rows))
                total = len(df_run)

                run_extra = {
                    "max_rows": int(max_rows),
                    "dry_run": bool(dry_run),
                    "force_template_emails": bool(force_template_emails),
                }
                run_id = create_run(
                    campaign_id=campaign_id,
                    dry_run=dry_run,
                    send_method=send_method,
                    total_prospects=total,
                    extra_json=json.dumps(run_extra, ensure_ascii=False),
                    db_path=db_path,
                )

                progress = st.progress(0.0)
                logs: List[str] = []
                results: List[Dict[str, Any]] = []

                llm_kwargs = llm_kwargs_for(provider)

                try:
                    for idx, (_, row) in enumerate(df_run.iterrows(), start=1):
                        row_idx = idx
                        try:
                            name = cell_str(row, name_col)
                            first_name = cell_str(row, first_name_col) or (name.split()[0] if name else "")
                            title = cell_str(row, title_col)
                            company = cell_str(row, company_col)
                            email = cell_str(row, email_col)
                            linkedin_url = cell_str(row, li_col)
                            industry_slug = (
                                cell_str(row, industry_col).lower().replace(" ", "_") if industry_col else ""
                            )

                            status_box.markdown(
                                f"Processing **{idx}/{total}** — {name or 'Unknown'} @ {company or 'Unknown'}"
                            )
                            logs.append(f"[{time.strftime('%H:%M:%S')}] {idx}/{total} → {name} @ {company}")
                            log_box.text("\n".join(logs[-200:]))

                            # --- Research
                            query = f"{name} {title} {company} customer experience analytics transformation"
                            insights_raw = ddg_insights(query, max_results=5)
                            topic_hint = topic_from_insights(insights_raw)
                            focus_snippet = clean_focus_snippet(insights_raw) or topic_hint
                            focus_block = strip_urls(insights_raw)
                            rag_context = global_rag_context or focus_block
                            profile_notes = profile_notes_default or ""

                            touches: List[Dict[str, str]] = []
                            email_status = "Email sequence off"
                            raw_llm_out: Optional[str] = None

                            if generate_email_seq or send_email_flag:
                                touches, raw_llm_out = generate_email_sequence(
                                    provider=provider,
                                    llm_kwargs=llm_kwargs,
                                    name=name,
                                    first_name=first_name,
                                    title=title,
                                    company=company,
                                    industry_slug=industry_slug,
                                    topic_hint=topic_hint,
                                    focus_block=focus_block,
                                    fewshot_snippets=fewshot_snippets,
                                    resource_profile=resource_profile,
                                    profile_notes=profile_notes,
                                    sgu_alignment=sgu_alignment,
                                    rag_context=rag_context,
                                    force_template=force_template_emails or not generate_email_seq,
                                    return_raw=show_raw,
                                )

                            if show_raw and raw_llm_out:
                                with st.expander(
                                    f"Raw LLM output — {name or 'Unknown'} @ {company or 'Unknown'}",
                                    expanded=False,
                                ):
                                    st.code((raw_llm_out or "")[:1600], language="json")

                            # --- Send emails
                            prospect = {
                                "Name": name,
                                "FirstName": first_name,
                                "Title": title,
                                "Company": company,
                                "Email": email,
                                "LinkedInURL": linkedin_url,
                                "Industry": industry_slug,
                                "RawRow": row.to_dict(),
                            }

                            if send_email_flag and touches:
                                email_status = send_email_sequence(
                                    prospect=prospect,
                                    touches=touches,
                                    send_method=send_method,
                                    dry_run=bool(dry_run),
                                    touch_delays_days=touch_delays_days,
                                    smtp_conf=smtp_conf,
                                )
                            elif touches:
                                email_status = "Sequence generated (sending disabled)"

                            # --- Store result in DB
                            insights_trunc = (strip_urls(insights_raw) or "")[:500]
                            insert_result(
                                run_id=run_id,
                                row_index=row_idx,
                                name=name,
                                title=title,
                                company=company,
                                email=email,
                                industry=industry_slug,
                                li_url=linkedin_url,
                                topic_hint=topic_hint,
                                email_status=email_status,
                                touches=touches,
                                insights_trunc=insights_trunc,
                                error_text="",
                                db_path=db_path,
                            )

                            # --- Local results for on-screen table
                            res_row = {
                                "Name": name,
                                "Company": company,
                                "Title": title,
                                "Email": email,
                                "Industry": industry_slug,
                                "Email Status": email_status,
                                "Topic": topic_hint,
                            }
                            for i, t in enumerate(touches[:4], start=1):
                                res_row[f"Email{i} Subject"] = t["subject"]
                                res_row[f"Email{i} Body"] = t["body"]
                            results.append(res_row)

                            # --- Per-prospect expander
                            with st.expander(f"{name or 'Unknown'} — {title or ''} @ {company or ''}", expanded=False):
                                st.markdown("**Email sequence (4 touches)**")
                                for i, t in enumerate(touches[:4], start=1):
                                    st.markdown(f"**Touch {i}: {t['subject']}**")
                                    st.markdown(t["body"].replace("\n- ", "\n• ").replace("\n•", "\n\n•"))

                            logs.append(f"   Email: {email_status}")
                            log_box.text("\n".join(logs[-200:]))

                        except Exception as e:
                            err_msg = f"{type(e).__name__}: {e}"
                            logs.append(f"ERROR row {idx}: {err_msg}")
                            log_box.text("\n".join(logs[-200:]))

                            # persist error row
                            insert_result(
                                run_id=run_id,
                                row_index=row_idx,
                                name=cell_str(row, name_col),
                                title=cell_str(row, title_col),
                                company=cell_str(row, company_col),
                                email=cell_str(row, email_col),
                                industry=cell_str(row, industry_col) if industry_col else "",
                                li_url=cell_str(row, li_col),
                                topic_hint="",
                                email_status="ERROR",
                                touches=[],
                                insights_trunc="",
                                error_text=err_msg,
                                db_path=db_path,
                            )

                        progress.progress(idx / max(1, total))

                    finalize_run(run_id, status="completed", db_path=db_path)
                    st.success("✅ Autopilot run finished.")

                    if results:
                        out_df = pd.DataFrame(results)
                        st.markdown("### 5️⃣ Run summary (this session)")
                        st.dataframe(out_df, use_container_width=True)
                        st.download_button(
                            "⬇️ Download results (CSV)",
                            data=out_df.to_csv(index=False).encode("utf-8"),
                            file_name=f"autopilot_run_{int(time.time())}.csv",
                            mime="text/csv",
                        )
                except Exception as e:
                    finalize_run(run_id, status=f"error: {e}", db_path=db_path)
                    st.error(f"Run failed with error: {e}")
    else:
        st.info("Upload a CSV to configure and run Autopilot.")


# ===================== TAB 2 – DASHBOARD =====================
with tab_dash:
    st.markdown("### 📊 Campaigns & Runs Dashboard")

    campaigns = list_campaigns(db_path=db_path)
    runs = list_runs(campaign_id=None, limit=100, db_path=db_path)

    if not campaigns and not runs:
        st.info("No Autopilot campaigns or runs found yet. Run your first campaign in the other tab.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total campaigns", len(campaigns))
        with col2:
            st.metric("Total runs", len(runs))
        with col3:
            last_status = runs[0]["status"] if runs else "n/a"
            st.metric("Last run status", last_status)

        if campaigns:
            st.markdown("#### Campaigns")
            camp_df = pd.DataFrame(campaigns)
            st.dataframe(camp_df, use_container_width=True)

        if runs:
            st.markdown("#### Recent runs")
            # Map campaign_id → name
            id_to_name = {c["id"]: c["name"] for c in campaigns}
            runs_view = []
            for r in runs:
                r_view = dict(r)
                r_view["campaign_name"] = id_to_name.get(r["campaign_id"], "—")
                runs_view.append(r_view)
            runs_df = pd.DataFrame(runs_view)
            st.dataframe(
                runs_df[
                    [
                        "id",
                        "campaign_name",
                        "started_at",
                        "ended_at",
                        "dry_run",
                        "send_method",
                        "total_prospects",
                        "status",
                    ]
                ],
                use_container_width=True,
            )
