import base64
import os

import streamlit as st

import theme
import ui
from services import auth

#brand assets, anchored to this file so the paths work regardless of working directory
_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_LOGO = os.path.join(_ASSETS, "logo-lockup.svg")
_MARK = os.path.join(_ASSETS, "logo-mark.svg")
_FAVICON = os.path.join(_ASSETS, "favicon.svg")

st.set_page_config(page_title="StratLab", page_icon=_FAVICON, layout="wide", initial_sidebar_state="collapsed")

#inject the theme and apply it to matplotlib on every run, before anything renders
ui.inject_css()
theme.apply_mpl_theme()


#render the lockup as a centred, self-contained image. the SVG is already outlined,
#so it needs no web font even when embedded as an <img>.
def _centered_logo(width: int = 260) -> None:
    with open(_LOGO, encoding="utf-8") as f:
        data = base64.b64encode(f.read().encode("utf-8")).decode()
    st.markdown(
        f"<div style='text-align:center; margin: 0.5rem 0 1rem'>"
        f"<img src='data:image/svg+xml;base64,{data}' width='{width}'></div>",
        unsafe_allow_html=True,
    )


#login / register screen shown until the user is authenticated
def login_screen() -> None:
    #no sidebar on the login screen
    st.markdown("<style>[data-testid='stSidebar']{display:none;}</style>", unsafe_allow_html=True)
    #centre the login card on the page
    left, middle, right = st.columns([1, 1.4, 1])
    with middle:
        _centered_logo()

        with st.container(border=True):
            login_tab, register_tab = st.tabs(["Log in", "Register"])

            with login_tab:
                username = st.text_input("Username", key="login_user")
                password = st.text_input("Password", type="password", key="login_pw")
                if st.button("Log in", type="primary", use_container_width=True):
                    if auth.login(username, password):
                        #store the user and rerun so the gate opens
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error("Wrong username or password.")

            with register_tab:
                new_user = st.text_input("Choose a username", key="reg_user")
                new_pw = st.text_input("Choose a password", type="password", key="reg_pw")
                if st.button("Create account", type="primary", use_container_width=True):
                    if not new_user or not new_pw:
                        st.warning("Please fill in both a username and a password.")
                    elif auth.register(new_user, new_pw):
                        st.success("Account created, switch to the Log in tab to continue.")
                    else:
                        st.error("That username is already taken.")


#the authenticated app: logo + grouped navigation in the sidebar.
#we build the menu by hand with st.navigation/st.Page (not the automatic pages/ logic)
#so we control the labels, the branding and the grouping.
def main_app() -> None:
    #the lockup brands the sidebar; the mark shows when the sidebar is collapsed
    st.logo(_LOGO, icon_image=_MARK, size="large")

    pages = {
        "": [
            st.Page("pages/0_Home.py", title="Home", icon=":material/home:", default=True),
        ],
        "Strategy": [
            st.Page("pages/1_Builder.py", title="Builder", icon=":material/build:"),
            st.Page("pages/2_Evaluate.py", title="Evaluate", icon=":material/insights:"),
            st.Page("pages/3_Compare.py", title="Compare", icon=":material/balance:"),
        ],
        "Research": [
            st.Page("pages/4_Explore.py", title="Explore", icon=":material/search:"),
        ],
        "Reference": [
            st.Page("pages/5_Glossary.py", title="Glossary", icon=":material/menu_book:"),
        ],
    }
    navigation = st.navigation(pages)
    #log-out sits in the sidebar on every page, centred between two divider lines
    with st.sidebar:
        if st.button("Log out", use_container_width=True, key="logout"):
            st.session_state.clear()
            st.rerun()
    navigation.run()


#entry point: gate the whole app behind login
if "username" not in st.session_state:
    login_screen()
else:
    main_app()
