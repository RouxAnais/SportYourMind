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
    st.caption(f"Signed in as {active_profile}")
else:
    st.caption("No profile yet -- set one up on the Profile page to track your progress.")

st.markdown(
    """
    > Quality always beats quantity. If an exercise feels too hard, use the
    > adaptation shown for it.
    """
)

st.divider()
st.page_link("pages/workout.py", label="Start a session")
st.page_link("pages/profile.py", label="My profile & progress")
st.page_link("pages/library.py", label="Exercise library")
