import streamlit as st

from components.navbar import inject_global_css, top_banner
from components.workout_player import render_workout_player
from components.session_plan import render_session_plan
from utils.load_data import load_workouts

st.set_page_config(page_title="100% Abs -- Session", layout="centered")
inject_global_css()

workouts = load_workouts()
week_ids = list(workouts.keys())
week_labels = {wid: w["title"] for wid, w in workouts.items()}

PLAYER_ACTIVE_KEY = "_syx_player_active"
PLAYER_SEANCE_KEY = "_syx_player_seance_id"

player_active = st.session_state.get(PLAYER_ACTIVE_KEY, False)

# ============================================================
# DEDICATED PLAYER VIEW -- shown full-focus once "Start" is pressed
# ============================================================
if player_active:
    active_id = st.session_state.get(PLAYER_SEANCE_KEY)
    seance = None
    found_week_id, found_week_title = None, None
    for wid, w in workouts.items():
        for s in w.get("seances", []):
            if s["id"] == active_id:
                seance = s
                found_week_id = wid
                found_week_title = w.get("title")
    if seance is None:
        st.session_state[PLAYER_ACTIVE_KEY] = False
        st.rerun()

    if st.button("< Back", key="syx_back_to_setup"):
        st.session_state[PLAYER_ACTIVE_KEY] = False
        st.rerun()

    render_workout_player(seance, week_id=found_week_id, week_title=found_week_title)

# ============================================================
# SESSION SETUP VIEW -- pick week/session, preview the plan, then Start
# ============================================================
else:
    top_banner("Session", "Pick your week and today's session")

    week_choice = st.selectbox("Week", week_ids, format_func=lambda w: week_labels[w])
    week = workouts[week_choice]
    seances = week.get("seances", [])

    if not seances:
        st.warning(week.get("note", "This week has not been added to the app yet."))
        st.stop()

    seance_labels = {s["id"]: s["title"] for s in seances}
    seance_choice = st.radio(
        "Session",
        [s["id"] for s in seances],
        format_func=lambda sid: seance_labels[sid],
        horizontal=True,
    )
    seance = next(s for s in seances if s["id"] == seance_choice)

    with st.expander("Session details", expanded=False):
        render_session_plan(seance)

    st.divider()

    if st.session_state.get("_syx_current_seance") != seance_choice:
        st.session_state["_syx_current_seance"] = seance_choice

    if st.button("Start", key="syx_start_session", use_container_width=True):
        st.session_state[PLAYER_ACTIVE_KEY] = True
        st.session_state[PLAYER_SEANCE_KEY] = seance_choice
        st.rerun()
