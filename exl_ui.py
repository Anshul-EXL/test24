#!/usr/bin/env python3
# exl_ui.py — Central top nav + logo + full-page loader
# Always horizontal via st.columns; no global font/size changes.

from pathlib import Path
from contextlib import contextmanager
import base64, time
import streamlit as st

# put near top of exl_ui.py
import inspect

def image_compat(img, *, width=None, use_container_width=False):
    """
    Calls st.image with the right args across Streamlit versions.
    - Newer versions: use_container_width
    - Older versions: use_column_width
    """
    try:
        params = inspect.signature(st.image).parameters
        if "use_container_width" in params:
            return st.image(img, width=width, use_container_width=use_container_width)
        # fallback (older versions)
        if use_container_width and "use_column_width" in params:
            return st.image(img, use_column_width=True)
        return st.image(img, width=width)
    except TypeError:
        # super old versions: last resort
        if use_container_width:
            try:
                return st.image(img, use_column_width=True)
            except TypeError:
                pass
        return st.image(img, width=width)


# --- Menu (single source of truth) ---
MENU = [
    ("Home",                "🏠", "app.py"),
    ("Campaign Builder",    "🗂️", "pages/exl_campaign_builder.py"),
    ("Contacts Extractor Agent",      "⛏", "pages/salesnav_zoom_harvester.py"),
    ("Research Agent",  "🕵️", "pages/exl_research_harvester.py"),
    ("Content Composer Agent",   "✉️", "pages/exl_outreach_composer.py"),
    ("Content Vailidator",  "🔎", "pages/exl_content_vailidation_dashboard.py"),
    ("Outreach Agent (LI)",  "🔗", "pages/li_sender_native.py"),
    ("Outreach Agent (Email)",         "🗓️", "pages/outlook_job.py"),
    ("Autopilot",           "🤖", "pages/exl_autopilot.py"),  #
]

LABEL_TO_PATH = {label: path for (label, _, path) in MENU}

_ASSETS_DIR = Path("assets")
_LOGO_PATH  = _ASSETS_DIR / "exl_service_logo.png"

def goto(path: str):
    if hasattr(st, "switch_page"):
        st.switch_page(path)
    else:
        st.info(f"Open `{path}` from the sidebar.")

def _inject_css_once():
    if st.session_state.get("_exl_topnav_css_injected"):
        return
    st.markdown("""
    <style>
      /* Header row */
      .exl-headerbar{ display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:6px; }
      .exl-logo{ height:36px; width:auto; object-fit:contain; }

      /* Row divider */
      .divider{height:1px;background:rgba(2,6,23,.06);margin:8px 0 12px}

      /* Make page links look like pills without touching global fonts */
      [data-testid="stPageLink"] a{
        display:inline-flex; align-items:center; gap:6px;
        padding:.40rem .85rem; border-radius:999px;
        border:1px solid rgba(2,6,23,.12); background:#fff; text-decoration:none !important;
        font-size:.95rem; line-height:1.05; white-space:nowrap;
      }
      /* “(current)” marker is appended in label; optional visual cue */
      [data-testid="stPageLink"]:has(a:contains("(current)")) a{
        border-color:#6366f1; box-shadow:0 0 0 2px rgba(99,102,241,.12) inset;
      }

      /* Full-page loader styling */
      .exl-loader__overlay{ position:fixed; inset:0; z-index:999999; background:rgba(9,16,28,.98); display:flex; align-items:center; justify-content:center; }
      .exl-loader__panel{ display:flex; flex-direction:column; align-items:center; gap:.9rem; padding:24px 28px; border-radius:14px;
                          background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
                          border:1px solid rgba(255,255,255,.12); box-shadow:0 20px 60px rgba(0,0,0,.35); min-width:260px; max-width:460px; }
      .exl-loader__logo{ width:120px; height:auto; object-fit:contain; filter: drop-shadow(0 2px 8px rgba(0,0,0,.35)); }
      .exl-loader__title{ color:#e6f2ff; font-size:1.05rem; letter-spacing:.2px; text-align:center; }
      .exl-loader__bar{ position:relative; width:280px; height:8px; border-radius:999px; background:rgba(255,255,255,.12); overflow:hidden; }
      .exl-loader__bar>span{ position:absolute; left:0; top:0; bottom:0; width:0%; background:linear-gradient(90deg, #00a8e1, #004e7a); border-radius:999px; transition: width .25s ease; }
      .exl-loader__hint{ color:rgba(230,242,255,.78); font-size:.92rem; text-align:center; }
      .exl-loader__spinner{ width:58px; height:58px; border-radius:50%; border:4px solid rgba(255,255,255,.18); border-top-color:#00a8e1; animation: exl-spin 1s linear infinite; }
      @keyframes exl-spin{ to{ transform: rotate(360deg); } }
    </style>
    """, unsafe_allow_html=True)
    st.session_state["_exl_topnav_css_injected"] = True

def _logo_b64() -> str | None:
    try:
        if _LOGO_PATH.exists():
            return base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
    except Exception:
        pass
    return None

def render_top_nav(active: str | None = None,
                   logo_path: str = str(_LOGO_PATH),
                   logo_width: int = 140,
                   menu: list[tuple[str, str, str]] | None = None):
    """
    Renders EXL logo + a guaranteed-horizontal nav row using st.columns.
    No JS; consistent on Windows/macOS/Linux.
    """
    _inject_css_once()
    menu = menu or MENU

    try:
        logo_col, nav_col = st.columns([1, 6], vertical_alignment="center")
    except TypeError:
        logo_col, nav_col = st.columns([1, 6])

    with logo_col:
        p = Path(logo_path)
        if p.exists():
            image_compat(str(p), width=logo_width, use_container_width=True)
        else:
            st.write("EXL")

    with nav_col:
        # One fixed row with N equal-width columns
        cols = st.columns(len(menu))
        for i, (label, icon, path) in enumerate(menu):
            lab = f"{icon} {label}" + (" (current)" if active == label else "")
            with cols[i]:
                if hasattr(st, "page_link"):
                    # Native fast navigation
                    st.page_link(path, label=lab, help=None)
                else:
                    # Fallback: button + switch_page
                    if st.button(lab, key=f"_exl_top_{i}", use_container_width=True):
                        goto(path)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# -------------------- Loader primitives --------------------
def _loader_html(message: str, progress: int | None, show_bar: bool, logo_b64: str | None) -> str:
    logo_html = f'<img class="exl-loader__logo" src="data:image/png;base64,{logo_b64}" alt="EXL"/>' if logo_b64 else ""
    bar_html  = (f'<div class="exl-loader__bar"><span style="width:{max(0,min(int(progress or 0),100))}%"></span></div>'
                 if show_bar else '<div class="exl-loader__spinner"></div>')
    return f"""
<div class="exl-loader__overlay" id="exl_loader_overlay">
  <div class="exl-loader__panel">
    {logo_html}
    <div class="exl-loader__title">{message}</div>
    {bar_html}
    <div class="exl-loader__hint" id="exl_loader_hint"></div>
  </div>
</div>
"""

def mount_loader(message: str = "Preparing workspace…", show_progress_bar: bool = True):
    """Mount a full-page overlay loader."""
    _inject_css_once()
    ph = st.empty()
    logo_b64 = _logo_b64()
    ph.markdown(_loader_html(message, 2 if show_progress_bar else None, show_progress_bar, logo_b64),
                unsafe_allow_html=True)

    def set_progress(pct: int | float = 0, msg: str | None = None):
        pct = int(max(0, min(100, round(pct))))
        html = _loader_html(message, pct, True, logo_b64)
        if msg:
            html = html.replace('id="exl_loader_hint"></div>', f'id="exl_loader_hint">{msg}</div>')
        ph.markdown(html, unsafe_allow_html=True)

    def set_message(msg: str):
        html = _loader_html(message, None, show_progress_bar, logo_b64)
        html = html.replace('id="exl_loader_hint"></div>', f'id="exl_loader_hint">{msg}</div>')
        ph.markdown(html, unsafe_allow_html=True)

    def done():
        ph.empty()

    return ph, set_progress, set_message, done

@contextmanager
def page_loader(message: str = "Loading…", show_progress_bar: bool = True):
    """Context manager for long blocks."""
    _, set_progress, _, done = mount_loader(message, show_progress_bar=show_progress_bar)
    try:
        yield set_progress
    finally:
        done()

# -------------------- Auto splash logic --------------------
def _page_key(page_id: str | None, active_label: str | None) -> str:
    if page_id and str(page_id).strip():
        return f"pid::{str(page_id).strip()}"
    if active_label and str(active_label).strip():
        return f"label::{str(active_label).strip()}"
    return "global"

def auto_splash_on_first_load(message: str = "Loading EXLead.ai…", min_ms: int = 500):
    key = "_exl_auto_splashed_once"
    if not st.session_state.get(key):
        _, _, set_msg, done = mount_loader(message, show_progress_bar=False)
        set_msg("Starting up…")
        time.sleep(max(0, min_ms) / 1000.0)
        done()
        st.session_state[key] = True

def auto_splash_on_page_change(active: str | None = None,
                               page_id: str | None = None,
                               message: str = "Loading…",
                               min_ms: int = 450):
    keyset = "_exl_splashed_pages"
    if keyset not in st.session_state:
        st.session_state[keyset] = set()
    k = _page_key(page_id, active)
    if k not in st.session_state[keyset]:
        _, _, set_msg, done = mount_loader(message, show_progress_bar=False)
        set_msg("Preparing view…")
        time.sleep(max(0, min_ms) / 1000.0)
        done()
        st.session_state[keyset].add(k)
