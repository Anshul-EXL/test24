import streamlit as st

# ------------------ FIXED USER ------------------
VALID_EMAIL = "anshul.thareja@exlservice.com"
VALID_PASSWORD = "exl@12345"

# --------- INIT SESSION (so login persists across pages in this tab) ---------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.session_state.get("logged_in") and "user" not in st.session_state:
    st.session_state["user"] = {"email": VALID_EMAIL, "name": "Anshul"}


def require_login(title: str = "EXLead.AI — Sign in"):
    """
    Call this right after your page's st.set_page_config(...).
    If not logged in, renders the login UI and stops the script.
    If logged in, returns a user dict.
    """
    # already logged in → just return
    if st.session_state.get("logged_in"):
        return st.session_state.get("user", {"email": VALID_EMAIL, "name": "Anshul"})

    # ---------- Global styles ----------
    st.markdown(
        """
        <style>
          :root {
            --brand: #FF6B00;
            --ink: #0F172A;
            --text: #334155;
          }

          /* Hide Streamlit sidebar + collapse control on login */
          [data-testid="stSidebar"] {
            display: none !important;
          }
          [data-testid="collapsedControl"] {
            display: none !important;
          }

          /* Center main area; soft background like your screenshot */
          .block-container {
            min-height: 100vh;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            display: flex;
            align-items: center;
            justify-content: center;
            background: radial-gradient(circle at top left, #EEF2FF 0, #FFFFFF 45%, #F8FAFC 100%);
          }

          .exl-title {
            margin: 10px 0 4px 0;
            font-weight: 700;
            font-size: 24px;
            color: var(--ink);
            text-align: center;
          }

          .exl-tagline {
            margin: 0;
            font-size: 13px;
            color: var(--text);
            text-align: center;
          }

          .exl-foot {
            text-align: center;
            font-size: 11px;
            color: #94A3B8;
            margin-top: 12px;
          }

          .stTextInput > div > div > input {
            border-radius: 10px !important;
          }

          .stCheckbox > label {
            font-size: 12px;
          }

          .stButton > button {
            width: 100%;
            border-radius: 10px;
            padding: 10px 14px;
            border: 1px solid var(--brand);
            background: var(--brand);
            color: #fff;
            font-weight: 600;
          }

          .stButton > button:hover {
            filter: brightness(0.98);
          }

          .exl-forgot {
            font-size: 12px;
            text-align: right;
            margin-top: 4px;
            color: #2563EB;
          }
          .exl-forgot a {
            color: #2563EB;
            text-decoration: none;
            font-weight: 500;
          }
          .exl-forgot a:hover {
            text-decoration: underline;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---------- Centered columns: card in the middle ----------
    left, center, right = st.columns([1, 1.1, 1])
    with center:
        # This container IS the card (border=True gives box + rounded corners)
        card = st.container(border=True)
        with card:
            # Centered logo + title inside card
            st.markdown(
                """
                <div style="text-align:center;">
                  <img src="https://www.exlservice.com/themes/exl_service/exl_logo_rgb_orange_pos_94.png"
                       width="120" alt="EXL"
                       style="display:block;margin:0 auto 4px auto;">
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("<h2 class='exl-title'>EXLead.AI</h2>", unsafe_allow_html=True)
            st.markdown(
                "<p class='exl-tagline'>AI-powered outreach & research suite for EXL teams</p>",
                unsafe_allow_html=True,
            )

            st.markdown("---")

            # --------- Inputs INSIDE the card ----------
            email = st.text_input(
                "Work email",
                value="",
                key="exl_email",
                placeholder="you@exlservice.com",
            )
            pw = st.text_input(
                "Password",
                type="password",
                value="",
                key="exl_pw",
                placeholder="Enter your password",
            )

            c1, c2 = st.columns([1, 1])
            with c1:
                remember = st.checkbox("Remember me", value=False, key="exl_remember")
            with c2:
                st.markdown(
                    '<div class="exl-forgot"><a href="#">Forgot your password?</a></div>',
                    unsafe_allow_html=True,
                )

            if st.button("Sign in"):
                if email.strip().lower() == VALID_EMAIL.lower() and pw == VALID_PASSWORD:
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = {
                        "email": VALID_EMAIL,
                        "name": "Anshul",
                    }
                    # you can use `remember` later for custom session logic
                    st.success("Welcome back!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")

        # footer just under the card
        st.markdown(
            "<div class='exl-foot'>© EXL · EXLead.AI POC environment</div>",
            unsafe_allow_html=True,
        )

    # Stop the rest of the page until authenticated
    st.stop()


def signout_button(label: str = "Sign out"):
    if st.button(label):
        st.session_state["logged_in"] = False
        st.session_state.pop("user", None)
        st.rerun()
