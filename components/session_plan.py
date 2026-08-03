import streamlit as st
from utils.load_data import get_exercise
from utils.helpers import build_readable_plan


def render_session_plan(seance: dict):
    """Full, at-a-glance text plan of the session: every block, every exercise name,
    every work time/rep count and every rest -- no photos, just names."""
    plan = build_readable_plan(seance, get_exercise)

    for entry in plan:
        title_class = "syx-plan-block-title-challenge" if entry.get("is_challenge") else "syx-plan-block-title"
        st.markdown(f"<div class='{title_class}'>{entry['title']}</div>", unsafe_allow_html=True)

        if (entry.get("is_challenge") or entry.get("always_show_note")) and entry.get("note"):
            st.markdown(f"<div class='syx-plan-note'>{entry['note']}</div>", unsafe_allow_html=True)

        rows_html = []
        for row in entry["rows"]:
            if row["type"] == "rest":
                rows_html.append(f"<div class='syx-plan-rest-row'>{row['label']}</div>")
            else:
                rows_html.append(
                    f"<div class='syx-plan-row'>"
                    f"<span class='syx-plan-row-exercise'>{row['exercise']}</span>"
                    f"<span class='syx-plan-row-meta'>{row['meta']}</span>"
                    f"</div>"
                )
        st.markdown("".join(rows_html), unsafe_allow_html=True)

        if entry.get("rest_after_block"):
            st.markdown(
                f"<div class='syx-plan-block-rest'>-- {entry['rest_after_block']} rest before next block --</div>",
                unsafe_allow_html=True,
            )
