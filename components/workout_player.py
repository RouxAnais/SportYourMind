import time
import math
import streamlit as st

from utils.helpers import build_seance_timeline, build_block_timeline, describe_step_short, remaining_in_block
from utils.load_data import get_audio_path, get_exercise
from utils import gsheets
from components.exercise_card import exercise_thumb
from components.timer import countdown_display, run_autorefresh
from components.beep import play_doorbell_beep, play_countdown_beep


def _inject_fullscreen_css():
    """Compact spacing for the training screen so the whole thing fits one
    phone screen without scrolling, as much as content length allows.
    Scoped to this screen only (not the rest of the app) since it's only
    called from render_block_player."""
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
        .syx-img-row img {
            max-height: 22vh !important;
            width: auto !important;
        }
        .element-container {
            margin-bottom: 0.3rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _k(player_key: str, suffix: str) -> str:
    return f"syx_play_{player_key}_{suffix}"


def _init_state(player_key: str, timeline: list):
    idx_key = _k(player_key, "idx")
    if idx_key not in st.session_state:
        st.session_state[idx_key] = 0
        st.session_state[_k(player_key, "timeline")] = timeline
        st.session_state[_k(player_key, "phase_start")] = None
        st.session_state[_k(player_key, "paused")] = False
        st.session_state[_k(player_key, "pause_elapsed")] = 0.0
        st.session_state[_k(player_key, "beeped_idx")] = -1
        st.session_state[_k(player_key, "last_tick")] = None
        st.session_state[_k(player_key, "doorbell_played")] = False
        st.session_state[_k(player_key, "logged")] = False


def _advance(player_key: str):
    st.session_state[_k(player_key, "idx")] += 1
    st.session_state[_k(player_key, "phase_start")] = None
    st.session_state[_k(player_key, "last_tick")] = None
    st.session_state[_k(player_key, "doorbell_played")] = False
    st.session_state[_k(player_key, "pause_elapsed")] = 0.0
    st.session_state[_k(player_key, "paused")] = False


def _go_back(player_key: str):
    idx_key = _k(player_key, "idx")
    st.session_state[idx_key] = max(0, st.session_state[idx_key] - 1)
    st.session_state[_k(player_key, "phase_start")] = None
    st.session_state[_k(player_key, "last_tick")] = None
    st.session_state[_k(player_key, "doorbell_played")] = False
    st.session_state[_k(player_key, "pause_elapsed")] = 0.0
    st.session_state[_k(player_key, "paused")] = False


def _restart(player_key: str):
    st.session_state[_k(player_key, "idx")] = 0
    st.session_state[_k(player_key, "phase_start")] = None
    st.session_state[_k(player_key, "last_tick")] = None
    st.session_state[_k(player_key, "doorbell_played")] = False
    st.session_state[_k(player_key, "pause_elapsed")] = 0.0
    st.session_state[_k(player_key, "paused")] = False
    st.session_state[_k(player_key, "logged")] = False


def _jump_to(player_key: str, target_idx: int):
    st.session_state[_k(player_key, "idx")] = target_idx
    st.session_state[_k(player_key, "phase_start")] = None
    st.session_state[_k(player_key, "last_tick")] = None
    st.session_state[_k(player_key, "doorbell_played")] = False
    st.session_state[_k(player_key, "pause_elapsed")] = 0.0
    st.session_state[_k(player_key, "paused")] = False


def _render_nav_controls(player_key: str, idx: int):
    """Next (big, always the same) to move forward. Return/Stop as a small,
    centered icon row below (real st.button()s, grouped via a keyed
    container -- see _inject_fullscreen_css)."""
    if st.button("Next", key=f"next_{player_key}_{idx}", use_container_width=True):
        _advance(player_key)
        st.rerun()

    control_key = f"ctrl_{player_key}_{idx}"
    choice = st.segmented_control(
        "controls", options=["\u21A9 Return", "\u25A0 Stop"],
        key=control_key, label_visibility="collapsed",
    )
    if choice is not None:
        st.session_state[control_key] = None
        if choice.startswith("\u21A9"):
            _go_back(player_key)
        else:
            st.session_state["_syx_flow"] = "block"
        st.rerun()


def _play_timeline(player_key: str, timeline: list, on_finished):
    """Core playback engine: steps through `timeline`, one exercise/rest at a
    time, with beeps and a next-up preview. `on_finished` is called (and
    should render its own completion UI) once the timeline is exhausted."""
    _init_state(player_key, timeline)
    idx = st.session_state[_k(player_key, "idx")]

    if idx >= len(timeline):
        on_finished(player_key)
        return

    step = timeline[idx]
    kind = step["kind"]

    next_step = timeline[idx + 1] if idx + 1 < len(timeline) else None
    if next_step:
        preview = describe_step_short(next_step, get_exercise)
        if preview:
            st.markdown(f"<div class='syx-next-up'>Next -- {preview}</div>", unsafe_allow_html=True)

    if kind == "block_title":
        st.markdown(f"<div class='syx-block-title'>{step['label']}</div>", unsafe_allow_html=True)

        audio_file = step.get("audio_file")
        local_audio = get_audio_path(audio_file) if audio_file else None
        if local_audio:
            st.audio(local_audio)
        elif audio_file:
            st.caption(
                f"Add your own '{audio_file}.mp3' (a file you legally own) to the "
                f"audio/ folder to play it here."
            )
        if step.get("external_link"):
            st.link_button("Open the track", step["external_link"])

        _render_nav_controls(player_key, idx)

    elif kind == "note":
        st.info(step["label"])
        _render_nav_controls(player_key, idx)

    elif kind == "manual":
        if step.get("exercise"):
            exercise_thumb(step["exercise"], step.get("side"))
        st.warning(step["label"])

        audio_file = step.get("audio_file")
        local_audio = get_audio_path(audio_file) if audio_file else None
        if local_audio:
            st.audio(local_audio)
        elif audio_file:
            st.caption(
                f"Add your own '{audio_file}.mp3' (a file you legally own) to the "
                f"audio/ folder to play it here."
            )
        if step.get("external_link"):
            st.link_button("Open the track", step["external_link"])

        _render_nav_controls(player_key, idx)

    elif kind == "reps":
        if step.get("exercise"):
            exercise_thumb(step["exercise"], step.get("side"))
        st.markdown(
            f"""
            <div class="syx-timer-wrap">
                <div class="syx-timer-label">REPS</div>
                <div class="syx-timer-number">{step['reps']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if step.get("note"):
            st.caption(step["note"])
        st.caption(f"{remaining_in_block(timeline, idx)} exercise(s) left")
        _render_nav_controls(player_key, idx)

    elif kind in ("work", "rest"):
        phase = "rest" if kind == "rest" else step.get("label", "on").lower()
        phase = phase if phase in ("hold", "on", "off", "rest") else "on"
        total = step["duration"]
        start_key = _k(player_key, "phase_start")
        pause_key = _k(player_key, "paused")
        elapsed_key = _k(player_key, "pause_elapsed")
        tick_key = _k(player_key, "last_tick")
        doorbell_key = _k(player_key, "doorbell_played")

        if st.session_state[start_key] is None:
            st.session_state[start_key] = time.time()

        if step.get("exercise"):
            exercise_thumb(step["exercise"], step.get("side"))

        if st.session_state[pause_key]:
            elapsed = st.session_state[elapsed_key]
        else:
            elapsed = (time.time() - st.session_state[start_key]) + st.session_state[elapsed_key]

        remaining = max(0.0, total - elapsed)
        big_label = step.get("label", "")
        countdown_display(remaining, total, phase, big_label)

        if not st.session_state[pause_key]:
            # Doorbell chime -- once, 1 second into the countdown
            if elapsed >= 1 and not st.session_state[doorbell_key]:
                play_doorbell_beep()
                st.session_state[doorbell_key] = True
            # Countdown beep -- once, on the second-to-last second
            tick = math.ceil(remaining)
            if tick == 2 and tick != st.session_state[tick_key]:
                play_countdown_beep()
                st.session_state[tick_key] = tick

        st.caption(f"{remaining_in_block(timeline, idx)} exercise(s) left")

        # Next -- always the same, full width, same position as every other screen
        if st.button("Next", key=f"next_{player_key}_{idx}", use_container_width=True):
            _advance(player_key)
            st.rerun()

        # Pause / Return / Stop -- one native segmented control, always on a
        # single line (not built from separate buttons/columns, which
        # Streamlit stacks vertically on narrow phones no matter what).
        pause_label = "\u25B6 Resume" if st.session_state[pause_key] else "\u23F8 Pause"
        control_key = f"ctrl_{player_key}_{idx}"
        choice = st.segmented_control(
            "controls", options=[pause_label, "\u21A9 Return", "\u25A0 Stop"],
            key=control_key, label_visibility="collapsed",
        )
        if choice is not None:
            st.session_state[control_key] = None
            if choice == pause_label:
                if st.session_state[pause_key]:
                    st.session_state[start_key] = time.time()
                    st.session_state[pause_key] = False
                else:
                    st.session_state[elapsed_key] = elapsed
                    st.session_state[pause_key] = True
            elif choice.startswith("\u21A9"):
                _go_back(player_key)
            else:
                st.session_state["_syx_flow"] = "block"
            st.rerun()

        if remaining <= 0 and not st.session_state[pause_key]:
            _advance(player_key)
            st.rerun()

        if not st.session_state[pause_key]:
            run_autorefresh(1000, key=f"tick_{player_key}_{idx}")


# ============================================================
# Whole-session player (kept for potential reuse elsewhere)
# ============================================================
def render_workout_player(seance: dict, week_id: str = None, week_title: str = None):
    player_key = seance["id"]
    timeline = build_seance_timeline(seance)
    st.markdown(f"### {seance['title']}")
    st.progress(min(st.session_state.get(_k(player_key, "idx"), 0) / max(len(timeline), 1), 1.0))

    def on_finished(pkey):
        st.success("Session complete! Great work.")
        profile = st.session_state.get("_syx_profile")
        logged_key = _k(pkey, "logged")
        if profile and not st.session_state.get(logged_key):
            gsheets.log_completion(profile, week_id, week_title, seance["id"], seance.get("title", ""))
            st.session_state[logged_key] = True
        elif not profile:
            st.caption("Set up a profile (see the Profile page) to save this to your progress history.")
        if st.button("Restart session", key=f"restart_{pkey}"):
            _restart(pkey)
            st.rerun()

    _play_timeline(player_key, timeline, on_finished)


# ============================================================
# Single-block player -- new primary flow
# ============================================================
def render_block_player(block: dict, block_label: str, player_key: str,
                         week_id: str = None, week_title: str = None,
                         seance_id: str = None, seance_title: str = None,
                         block_ref=None):
    """Play just ONE block (or the challenge). No inter-block rest is inserted --
    moving to another block is a manual, user-driven action (the Stop icon)."""
    _inject_fullscreen_css()
    timeline = build_block_timeline(block)
    st.markdown(f"### {block_label}")
    st.progress(min(st.session_state.get(_k(player_key, "idx"), 0) / max(len(timeline), 1), 1.0))

    def on_finished(pkey):
        st.success("Nice work -- you've completed this part of the session!")
        profile = st.session_state.get("_syx_profile")
        logged_key = _k(pkey, "logged")
        if profile and not st.session_state.get(logged_key):
            gsheets.log_completion(profile, week_id, week_title, seance_id or "", seance_title or "",
                                    block_ref=block_ref)
            st.session_state[logged_key] = True
        elif not profile:
            st.caption("Set up a profile (see the Profile page) to save this to your progress history.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Restart", key=f"restart_{pkey}", use_container_width=True):
                _restart(pkey)
                st.rerun()
        with c2:
            if st.button("Back", key=f"done_back_{pkey}", use_container_width=True):
                st.session_state["_syx_flow"] = "block"
                st.rerun()

    _play_timeline(player_key, timeline, on_finished)
