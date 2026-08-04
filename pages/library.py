import streamlit as st

from components.navbar import inject_global_css, top_banner
from components.exercise_card import exercise_card
from utils.load_data import load_exercises

st.set_page_config(page_title="100% Abs -- Library", layout="centered")
inject_global_css()
top_banner("Library", "Every exercise, with instructions and adaptations")

st.markdown(
    "<div class='syx-plan-note'>"
    "For exercises held in a static position, aim to hold it for the full "
    "interval. Always try the exercise as prescribed first -- if you can't hold "
    "it the whole time without stopping, break it into 2 sets. If you need more "
    "than 2 breaks, it's a sign to switch to the easier adaptation instead."
    "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='syx-plan-note'>"
    "Quality always beats quantity. If an exercise feels too hard, switch to its "
    "adaptation rather than pushing through bad form. Leave your ego at the "
    "door -- some exercises are built for an advanced level, so take the time to "
    "progress at your own pace and stay safe."
    "</div>",
    unsafe_allow_html=True,
)
st.markdown("")

data = load_exercises()
exercises = data.get("exercises", {})

categories = sorted(set(ex.get("category", "?") for ex in exercises.values()))
choice = st.selectbox("Filter by category", ["All"] + categories)

search = st.text_input("Search an exercise", "")

for ex_id, ex in exercises.items():
    if choice != "All" and ex.get("category") != choice:
        continue
    if search and search.lower() not in ex["name"].lower():
        continue
    exercise_card(ex_id)
