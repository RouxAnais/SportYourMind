import os
import streamlit as st

from components.navbar import inject_global_css, top_banner
from utils.load_data import load_workouts

st.set_page_config(page_title="100% Abs -- Home", layout="centered")
inject_global_css()

top_banner("100% ABS", "20 sessions x 20 min · Sport Your Mind")

active_profile = st.session_state.get("_syx_profile")
if active_profile:
    st.caption(f"Signed in as {active_profile}")
else:
    st.caption("No profile yet -- set one up on the Profile page to track your progress.")

assets_home = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "home.jpg")
if os.path.exists(assets_home):
    st.image(assets_home, use_container_width=True)

st.markdown(
    """
    Welcome to your **100% Abs** program.

    5 weeks of gradual progression, 4 sessions per week (**Rectus abdominis**,
    **Core bracing**, **Gym**, **Obliques**), 20 minutes per session.

    > Quality always beats quantity. If an exercise feels too hard, use the
    > adaptation shown for it.
    """
)

workouts = load_workouts()
n_weeks = len(workouts)
n_seances = sum(len(w.get("seances", [])) for w in workouts.values())

c1, c2, c3 = st.columns(3)
c1.metric("Weeks", n_weeks)
c2.metric("Sessions loaded", n_seances)
c3.metric("Per session", "~20 min")

st.divider()
st.page_link("pages/workout.py", label="Start a session")
st.page_link("pages/profile.py", label="My profile & progress")
st.page_link("pages/library.py", label="Exercise library")
