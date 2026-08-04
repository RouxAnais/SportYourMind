import streamlit as st
import pandas as pd

from components.navbar import inject_global_css, top_banner
from utils import gsheets

st.set_page_config(page_title="100% Abs -- Profile", layout="centered")
inject_global_css()
top_banner("Profile", "Track your progress over time")

PROFILE_KEY = "_syx_profile"

if not gsheets.is_configured():
    st.warning(
        "Profiles aren't connected yet. This needs a one-time Google Sheets "
        "setup -- see `docs/GSHEETS_SETUP.md` in the project files."
    )
    st.stop()

active_profile = st.session_state.get(PROFILE_KEY)

# ============================================================
# No profile selected yet -- pick or create one
# ============================================================
if not active_profile:
    profiles = gsheets.load_profiles()

    if profiles:
        st.markdown("#### Who's training today?")
        choice = st.selectbox("Select your profile", profiles)
        if st.button("Continue", use_container_width=True):
            st.session_state[PROFILE_KEY] = choice
            st.rerun()
        st.divider()

    st.markdown("#### New here?")
    new_name = st.text_input("Create a profile with your name")
    if st.button("Create profile", use_container_width=True):
        if new_name.strip():
            if gsheets.create_profile(new_name.strip()):
                st.session_state[PROFILE_KEY] = new_name.strip()
                st.rerun()
            else:
                st.error("Couldn't save the profile -- please try again.")
        else:
            st.error("Enter a name first.")

# ============================================================
# Active profile -- progress dashboard
# ============================================================
else:
    st.markdown(f"#### Hi {active_profile}!")
    if st.button("Switch profile", key="switch_profile"):
        st.session_state[PROFILE_KEY] = None
        st.rerun()

    st.divider()

    history = gsheets.load_history(active_profile)

    if history.empty:
        st.info("No completed sessions yet -- finish a session to see your progress here.")
    else:
        total = len(history)
        weeks_touched = history["week_title"].nunique() if "week_title" in history.columns else 0

        c1, c2 = st.columns(2)
        c1.metric("Sessions completed", total)
        c2.metric("Weeks started", weeks_touched)

        if "week_title" in history.columns:
            st.markdown("##### Sessions per week")
            counts = history["week_title"].value_counts().sort_index()
            st.bar_chart(counts)

        st.markdown("##### Recent sessions")
        recent = history.sort_values("completed_at", ascending=False).head(10)
        for _, row in recent.iterrows():
            date_str = str(row.get("completed_at", ""))[:16].replace("T", " at ")
            st.markdown(
                f"<div class='syx-plan-row'>"
                f"<span class='syx-plan-row-exercise'>{row.get('seance_title', '')}</span>"
                f"<span class='syx-plan-row-meta' style='font-size:0.8rem;'>{date_str}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
