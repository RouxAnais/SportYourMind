import streamlit as st

pages = [
    st.Page("pages/home.py", title="Home", default=True),
    st.Page("pages/workout.py", title="Session"),
    st.Page("pages/library.py", title="Library"),
    st.Page("pages/about.py", title="About"),
]

nav = st.navigation(pages, position="sidebar")
nav.run()
