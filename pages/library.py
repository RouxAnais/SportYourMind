import streamlit as st

from components.navbar import inject_global_css, top_banner
from components.exercise_card import exercise_card
from utils.load_data import load_exercises

st.set_page_config(page_title="100% Abs -- Library", layout="centered")
inject_global_css()
top_banner("Library", "Every exercise, with instructions and adaptations")

st.markdown(
    "<div class='syx-plan-note'>"
    "When an exercise is held in a static position, your goal is to hold it for "
    "the entire interval. Always prioritize doing the required exercise -- if you "
    "can't complete the full interval without stopping, you can split it into 2. "
    "If you need to split it into more than 2, it's better to switch to the "
    "optimized adaptation instead."
    "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='syx-plan-note'>"
    "Always prioritize quality over quantity. If an exercise is too difficult, "
    "choose its adaptation instead. Leave your ego aside -- some exercises are "
    "designed for an advanced level, take the time to progress at your own pace "
    "for more safety."
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
