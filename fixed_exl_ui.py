#!/usr/bin/env python3
# exl_ui.py — Central top nav + logo + full-page loader
# Single-line, scrollable top nav with working navigation via ?nav=... + st.switch_page
# CSS is injected on EVERY render so styles persist across pages.

from pathlib import Path
from contextlib import contextmanager
import base64, time
import streamlit as st
import inspect

def image_compat(img, *, width=None, use_container_width=False):
    try:
        params = inspect.signature(st.image).parameters
        if "use_container_width" in params:
            return st.image(img, width=width, use_container_width=use_container_width)
        if use_container_width and "use_column_width" in params:
            return st.image(img, use_column_width=True)
        return st.image(img, width=width)
    except TypeError:
        if use_container_width:
            try:
                return st.image(img, use_column_width=True)
            except TypeError:
                pass
        return st.image(img, width=width)

# --- Menu (single source of truth) ---
MENU = [
    ("Campaign Builder",        "🗂️", "pages/exl_campaign_builder.py"),
    ("Contacts Extractor Agent","⛏",  "pages/salesnav_zoom_harvester.py"),
    ("Research Agent",          "🕵️", "pages/exl_research_harvester.py"),
    ("Content Composer Agent",  "✉️", "pages/exl_outreach_composer.py"),
    ("Content Vailidator",      "🔎", "pages/exl_content_vailidation_dashboard.py"),
    ("Outreach Agent (LI)",     "🔗", "pages/li_sender_native.py"),
    ("Outreach Agent (Email)",  "🗓️", "pages/outlook_job.py"),
    ("Autopilot",               "🔌", "pages/exl_autopilot.py"),
]

LABEL_TO_PATH = {label: path for (label, _, path) in MENU}

_ASSETS_DIR = Path("assets")
_LOGO_PATH  = _ASSETS_DIR / "exl_service_logo.png"

# ---------- CSS (inject EVERY render) ----------
def _inject_css():
    st.markdown("""
    <style>
      /* Layout */
      .exl-headerbar{ display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:6px; }
      .divider{height:1px;background:rgba(2,6,23,.06);margin:8px 0 12px}

      /* Clickable logo */
      .exl-logo{ height:36px; width:auto; object-fit:contain; display:block; }

      /* Horizontal, scrollable nav */
      .exl-nav{ display:flex; align-items:center; gap:8px; white-space:nowrap !important;
                overflow-x:auto !important; padding:2px 0 6px; scrollbar-width:thin; }
      .exl-nav::-webkit-scrollbar{ height:6px; }
      .exl-nav::-webkit-scrollbar-thumb{ background:#cbd5e1; border-radius:6px; }

      /* Links: never truncate; keep same color for normal/visited */
      .exl-nav a, .exl-nav a:visited{
        display:inline-flex !important; align-items:center; gap:6px;
        padding:.40rem .85rem; border-radius:999px;
        border:1px solid rgba(2,6,23,.12); background:#fff; text-decoration:none !important; color:#111 !important;
        font-size:.95rem; line-height:1.05;
        max-width:none !important; width:auto !important; min-width:max-content !important;
        overflow:visible !important; text-overflow:clip !important; white-space:nowrap !important;
      }
      .exl-nav a.active{ border-color:#6366f1; box-shadow:0 0 0 2px rgba(99,102,241,.12) inset; }

      /* Full-page loader styling */
      .exl-loader__overlay{ position:fixed; inset:0; z-index:999999; background:rgba(9,16,28,.98); display:flex; align-items:center; justify-content:center; }
      .exl-loader__panel{ display:flex; flex-direction:column; align-items:center; gap:.9rem; padding:24px 28px; border-radius:14px;
                          background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
                          border:1px solid rgba(255,255,255,.12); box-shadow:0 20px 60px rgba(0,0,0,.35); min-width:260px; max-width:460px; }
      .exl-loader__title{ color:#e6f2ff; font-size:1.05rem; letter-spacing:.2px; text-align:center; }
      .exl-loader__hint{ color:rgba(230,242,255,.78); font-size:.92rem; text-align:center; }
      .exl-loader__spinner{ width:58px; height:58px; border-radius:50%; border:4px solid rgba(255,255,255,.18); border-top-color:#00a8e1; animation: exl-spin 1s linear infinite; }
      @keyframes exl-spin{ to{ transform: rotate(360deg); } }
    </style>
    """, unsafe_allow_html=True)

def _logo_b64() -> str | None:
    try:
        if _LOGO_PATH.exists():
            return base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
    except Exception:
        pass
    return None

def _handle_query_nav():
    """If URL has ?nav=..., switch_page to it and clear the param."""
    nav_path = None
    try:
        nav_path = st.query_params.get("nav")
    except Exception:
        qp = st.experimental_get_query_params()
        nav_path = (qp.get("nav") or [None])[0]

    if nav_path:
        if hasattr(st, "switch_page"):
            try:
                st.query_params.clear()
            except Exception:
                st.experimental_set_query_params()
            st.switch_page(nav_path)
        else:
            st.info(f"Open `{nav_path}` from the sidebar.")
        st.stop()

def render_top_nav(active: str | None = None,
                   logo_path: str = str(_LOGO_PATH),
                   logo_width: int = 140,
                   menu: list[tuple[str, str, str]] | None = None):
    """
    Renders EXL logo + single-line, scrollable nav (no truncation).
    Navigation works by anchors setting ?nav=... which is handled above.
    """
    _inject_css()          # <-- inject styles on every render/page
    _handle_query_nav()
    menu = menu or MENU

    col_logo, col_nav = st.columns([1, 6], vertical_alignment="center") if hasattr(st, "columns") else st.columns([1,6])

    with col_logo:
        b64 = _logo_b64()
        if b64:
            st.markdown(
                f"""<a href="?nav=app.py" title="Home">
                        <img class="exl-logo" src="data:image/png;base64,{b64}" alt="EXL">
                    </a>""",
                unsafe_allow_html=True
            )
        else:
            st.markdown('<a href="?nav=app.py" class="exl-logo">EXL</a>', unsafe_allow_html=True)

    with col_nav:
        links = []
        for (label, icon, path) in menu:
            active_cls = "active" if active == label else ""
            links.append(f'<a class="{active_cls}" href="?nav={path}">{icon} {label}</a>')
        st.markdown(f'<div class="exl-nav">{"".join(links)}</div>', unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# -------------------- Loader primitives --------------------
def _loader_html(message: str, progress: int | None, show_bar: bool, logo_b64: str | None) -> str:
    logo_html = f'<img class="exl-logo" style="height:48px" src="data:image/png;base64,{logo_b64}" alt="EXL"/>' if logo_b64 else ""
    bar_html  = (f'<div style="position:relative;width:280px;height:8px;border-radius:999px;background:rgba(255,255,255,.12);overflow:hidden;"><span style="position:absolute;left:0;top:0;bottom:0;width:{max(0,min(int(progress or 0),100))}%;background:linear-gradient(90deg,#00a8e1,#004e7a);border-radius:999px;transition:width .25s ease;"></span></div>'
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
