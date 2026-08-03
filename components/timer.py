import time
import streamlit as st
from utils.theme import PHASE_COLORS
from utils.helpers import format_time

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False


def countdown_display(remaining: float, total: float, phase: str, big_label: str = ""):
    """Render the big countdown number + progress ring/bar for the current phase."""
    color = PHASE_COLORS.get(phase, PHASE_COLORS["on"])
    pct = 0 if total <= 0 else max(0.0, min(1.0, remaining / total))
    st.markdown(
        f"""
        <div class="syx-timer-wrap" style="--phase-color:{color};">
            <div class="syx-timer-label">{big_label}</div>
            <div class="syx-timer-number">{format_time(remaining)}</div>
            <div class="syx-timer-track">
                <div class="syx-timer-fill" style="width:{pct*100:.1f}%;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def run_autorefresh(interval_ms: int = 250, key: str = "syx_tick"):
    if HAS_AUTOREFRESH:
        st_autorefresh(interval=interval_ms, key=key)
    else:
        # Fallback: no live ticking without the package: show a manual refresh hint once.
        st.caption("Installe `streamlit-autorefresh` (voir requirements.txt) pour un chrono en temps réel.")
