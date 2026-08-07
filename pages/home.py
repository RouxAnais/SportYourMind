import os
import streamlit as st

from components.navbar import inject_global_css
from utils import gsheets, progress
from utils.load_data import load_workouts

st.set_page_config(page_title="100% Abs -- Home", layout="centered")
inject_global_css()

assets_home = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "home.jpg")
if os.path.exists(assets_home):
    try:
        st.image(assets_home, width="stretch")
    except Exception as e:
        st.caption(f"(cover image could not be displayed: {e})")

active_profile = st.session_state.get("_syx_profile")

if not active_profile:
    st.caption("No profile yet -- set one up to track your progress.")
    if st.button("Start", use_container_width=True, type="primary"):
        st.switch_page("pages/profile.py")
else:
    display_name = st.session_state.get("_syx_profile_name", active_profile)
    st.caption(f"Signed in as {display_name}")

    workouts = load_workouts()
    done_count, _ = progress.get_overall_progress(active_profile, workouts)
    next_session = progress.get_next_session(active_profile, workouts)

    if next_session is None:
        st.success("You've completed the whole program! Feel free to start again any time.")
    else:
        label = "Start" if done_count == 0 else "Continue"
        if st.button(f"{label} {next_session['week_title']} \u00b7 {next_session['seance_title']}",
                     use_container_width=True, type="primary"):
            st.session_state["_syx_sidebar_week"] = next_session["week_id"]
            st.session_state["_syx_sidebar_seance"] = next_session["seance_id"]
            st.session_state["_syx_flow"] = "block"
            st.switch_page("pages/workout.py")
