import streamlit as st
import os


def inject_global_css():
    css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def top_banner(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="syx-banner">
            <div class="syx-banner-title">{title}</div>
            <div class="syx-banner-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
