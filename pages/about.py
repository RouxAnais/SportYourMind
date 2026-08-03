import streamlit as st

from components.navbar import inject_global_css, top_banner

st.set_page_config(page_title="100% Abs -- About", layout="centered")
inject_global_css()
top_banner("About", "Sport Your Mind")

st.markdown(
    """
    **Anais Roux** -- Personal trainer, former CrossFit(R) athlete, former
    military, graduate of the Lyon Faculty of Sport (2017), CrossFit(R)
    Level 2, Pilates and Yoga instructor.

    Founder of **Sport Your Mind**, specialized in bodyweight training.

    ---

    This program can be repeated as many times as needed to reach your
    goals. Remember to take a before/after photo to track your progress!
    """
)
