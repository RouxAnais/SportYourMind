import os
import streamlit as st

from components.navbar import inject_global_css

st.set_page_config(page_title="100% Abs -- Home", layout="centered")
inject_global_css()

assets_home = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "home.jpg")
if os.path.exists(assets_home):
    try:
        st.image(assets_home, width="stretch")
    except Exception as e:
        st.caption(f"(cover image could not be displayed: {e})")

active_profile = st.session_state.get("_syx_profile")
if active_profile:
    display_name = st.session_state.get("_syx_profile_name", active_profile)
    st.caption(f"Signed in as {display_name}")
else:
    st.caption("No profile yet -- set one up to track your progress.")
    if st.button("Start", use_container_width=True, type="primary"):
        st.switch_page("pages/profile.py")

st.divider()
st.page_link("pages/workout.py", label="Start a session")
st.page_link("pages/profile.py", label="My profile & progress")
st.page_link("pages/library.py", label="Exercise library")
