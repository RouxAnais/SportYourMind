import datetime
import streamlit as st
import pandas as pd
import altair as alt

from components.navbar import inject_global_css, top_banner
from utils import gsheets, progress
from utils.load_data import load_workouts

st.set_page_config(page_title="100% Abs -- Profile", layout="centered")
inject_global_css()
top_banner("Profile", "Track your progress over time")

PROFILE_KEY = "_syx_profile"          # stores the internal profile id
PROFILE_NAME_KEY = "_syx_profile_name"  # stores "First Last" for display

if not gsheets.is_configured():
    st.warning(
        "Profiles aren't connected yet. This needs a one-time Google Sheets "
        "setup -- see `docs/GSHEETS_SETUP.md` in the project files."
    )
    st.stop()

_last_err = st.session_state.get("_syx_gsheets_last_error")
if _last_err:
    st.warning(f"(Debug -- temporary) Last Google Sheets error: {_last_err}")

active_profile = st.session_state.get(PROFILE_KEY)

# ============================================================
# No profile selected yet -- pick or create one
# ============================================================
if not active_profile:
    profiles = gsheets.load_profiles()

    if profiles:
        st.markdown("#### Who's training today?")
        labels = [p["display"] for p in profiles]
        choice_label = st.selectbox("Select your profile", labels)
        chosen = profiles[labels.index(choice_label)]
        entered_dob = st.text_input(
            "Confirm your date of birth (DDMMYY, e.g. 120590)",
            max_chars=6, key="login_dob",
        )
        if st.button("Continue", use_container_width=True):
            if gsheets.verify_birthdate(chosen["id"], entered_dob):
                st.session_state[PROFILE_KEY] = chosen["id"]
                st.session_state[PROFILE_NAME_KEY] = chosen["display"]
                st.rerun()
            else:
                st.error("That doesn't match -- please try again.")
        st.divider()

    st.markdown("#### New here?")
    st.caption("First name, last name, and date of birth are used together "
               "so two people with the same name don't share one profile. "
               "Your date of birth isn't shown publicly -- it's used to "
               "confirm it's you when you come back.")
    first_name = st.text_input("First name")
    last_name = st.text_input("Last name")
    birthdate = st.date_input(
        "Date of birth",
        value=None,
        min_value=datetime.date(1920, 1, 1),
        max_value=datetime.date.today(),
    )
    if st.button("Create profile", use_container_width=True):
        if first_name.strip() and last_name.strip() and birthdate:
            ok, profile_id = gsheets.create_profile(first_name, last_name, birthdate)
            if ok:
                st.session_state[PROFILE_KEY] = profile_id
                st.session_state[PROFILE_NAME_KEY] = f"{first_name.strip()} {last_name.strip()}"
                st.rerun()
            else:
                st.error("Couldn't save the profile -- please try again.")
        else:
            st.error("Enter your first name, last name, and date of birth.")

# ============================================================
# Active profile -- progress dashboard
# ============================================================
else:
    display_name = st.session_state.get(PROFILE_NAME_KEY, active_profile)
    st.markdown(f"#### Hi {display_name}!")
    if st.button("Log out", key="switch_profile"):
        st.session_state[PROFILE_KEY] = None
        st.session_state[PROFILE_NAME_KEY] = None
        st.rerun()

    st.caption("This program runs over 5 weeks, with 4 sessions per week -- "
               "20 sessions in total.")

    workouts = load_workouts()
    done_count, total_count = progress.get_overall_progress(active_profile, workouts)
    st.progress(0 if total_count == 0 else done_count / total_count,
                text=f"{done_count} / {total_count} sessions completed")

    next_session = progress.get_next_session(active_profile, workouts)
    if next_session is None:
        st.success("You've completed the whole program! Feel free to start again any time.")
    else:
        label = "Start" if done_count == 0 else "Continue"
        st.markdown(f"**Next up:** {next_session['week_title']} -- {next_session['seance_title']}")
        if st.button(f"{label} {next_session['week_title']} \u00b7 {next_session['seance_title']}",
                     use_container_width=True, type="primary"):
            st.session_state["_syx_sidebar_week"] = next_session["week_id"]
            st.session_state["_syx_sidebar_seance"] = next_session["seance_id"]
            st.session_state["_syx_flow"] = "block"
            st.switch_page("pages/workout.py")

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
            st.markdown("##### Exercises per week")
            week_order = ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5"]
            counts_map = history["week_title"].value_counts().to_dict()
            chart_df = pd.DataFrame({
                "week": week_order,
                "count": [counts_map.get(w, 0) for w in week_order],
            })
            chart = alt.Chart(chart_df).mark_bar().encode(
                x=alt.X("week:N", sort=week_order, title=None),
                y=alt.Y("count:Q", title="Exercises completed"),
                color=alt.condition(
                    alt.datum.count > 0,
                    alt.value("#6C5CE7"),
                    alt.value("#808080"),
                ),
            ).properties(height=260)
            st.altair_chart(chart, use_container_width=True)

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
