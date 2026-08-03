import streamlit as st

from components.navbar import inject_global_css, top_banner
from components.workout_player import render_workout_player
from components.session_plan import render_session_plan
from utils.load_data import load_workouts

st.set_page_config(page_title="100% Abs -- Session", layout="centered")
inject_global_css()
top_banner("Session", "Pick your week and today's session")

workouts = load_workouts()
week_ids = list(workouts.keys())
week_labels = {wid: w["title"] for wid, w in workouts.items()}

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

render_workout_player(seance)
