import time
import streamlit as st

from utils.helpers import build_seance_timeline, format_time, describe_step_short, remaining_in_block
from utils.load_data import get_audio_path, get_exercise
from utils import gsheets
from components.exercise_card import exercise_thumb
from components.timer import countdown_display, run_autorefresh
from components.beep import play_start_beep, play_rest_beep


def _state_key(seance_id: str, suffix: str) -> str:
    return f"syx_player_{seance_id}_{suffix}"


def _init_state(seance: dict):
    seance_id = seance["id"]
    idx_key = _state_key(seance_id, "idx")
    if idx_key not in st.session_state:
        st.session_state[idx_key] = 0
        st.session_state[_state_key(seance_id, "timeline")] = build_seance_timeline(seance)
        st.session_state[_state_key(seance_id, "phase_start")] = None
        st.session_state[_state_key(seance_id, "paused")] = False
        st.session_state[_state_key(seance_id, "pause_elapsed")] = 0.0
        st.session_state[_state_key(seance_id, "finished")] = False
        st.session_state[_state_key(seance_id, "beeped_idx")] = -1


def _advance(seance_id: str):
    st.session_state[_state_key(seance_id, "idx")] += 1
    st.session_state[_state_key(seance_id, "phase_start")] = None
    st.session_state[_state_key(seance_id, "pause_elapsed")] = 0.0
    st.session_state[_state_key(seance_id, "paused")] = False


def _restart(seance_id: str):
    st.session_state[_state_key(seance_id, "idx")] = 0
    st.session_state[_state_key(seance_id, "phase_start")] = None
    st.session_state[_state_key(seance_id, "pause_elapsed")] = 0.0
    st.session_state[_state_key(seance_id, "paused")] = False
    st.session_state[_state_key(seance_id, "finished")] = False


def _jump_to(seance_id: str, target_idx: int):
    st.session_state[_state_key(seance_id, "idx")] = target_idx
    st.session_state[_state_key(seance_id, "phase_start")] = None
    st.session_state[_state_key(seance_id, "pause_elapsed")] = 0.0
    st.session_state[_state_key(seance_id, "paused")] = False
    st.session_state[_state_key(seance_id, "finished")] = False


def render_workout_player(seance: dict, week_id: str = None, week_title: str = None):
    seance_id = seance["id"]
    _init_state(seance)

    timeline = st.session_state[_state_key(seance_id, "timeline")]
    idx = st.session_state[_state_key(seance_id, "idx")]

    block_points = [(i, step["label"]) for i, step in enumerate(timeline) if step["kind"] == "block_title"]
    block_short_labels = [
        "Challenge" if label.startswith("CHALLENGE") else label.split(" (")[0]
        for _, label in block_points
    ]

    col_title, col_block = st.columns([3, 2])
    with col_title:
        st.markdown(f"### {seance['title']}")
    with col_block:
        if block_points:
            picked = st.selectbox(
                "Block", block_short_labels, key=f"block_select_{seance_id}",
                label_visibility="collapsed",
            )
            if st.button("Go to block", key=f"block_go_{seance_id}", use_container_width=True):
                target_idx = block_points[block_short_labels.index(picked)][0]
                _jump_to(seance_id, target_idx)
                st.rerun()

    st.progress(min(idx / max(len(timeline), 1), 1.0))

    if idx >= len(timeline):
        st.success("Session complete! Great work.")

        logged_key = _state_key(seance_id, "logged")
        profile = st.session_state.get("_syx_profile")
        if profile and not st.session_state.get(logged_key):
            gsheets.log_completion(profile, week_id, week_title, seance_id, seance.get("title", ""))
            st.session_state[logged_key] = True
        elif not profile:
            st.caption("Set up a profile (see the Profile page) to save this to your progress history.")

        if st.button("Restart session", key=f"restart_{seance_id}"):
            _restart(seance_id)
            st.session_state[logged_key] = False
            st.rerun()
        return

    step = timeline[idx]
    kind = step["kind"]

    # Play a beep the first time we render this step (not on every autorefresh tick)
    beeped_key = _state_key(seance_id, "beeped_idx")
    if st.session_state[beeped_key] != idx:
        if kind == "work":
            play_start_beep()
        elif kind == "rest":
            play_rest_beep()
        st.session_state[beeped_key] = idx

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

        if st.button("Continue", key=f"cont_{seance_id}_{idx}", use_container_width=True):
            _advance(seance_id)
            st.rerun()

    elif kind == "note":
        st.info(step["label"])
        if st.button("Got it, continue", key=f"cont_{seance_id}_{idx}", use_container_width=True):
            _advance(seance_id)
            st.rerun()

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

        if st.button("Next step", key=f"cont_{seance_id}_{idx}", use_container_width=True):
            _advance(seance_id)
            st.rerun()

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
        if st.button("Done, next step", key=f"done_{seance_id}_{idx}", use_container_width=True):
            _advance(seance_id)
            st.rerun()
        st.caption(f"{remaining_in_block(timeline, idx)} exercise(s) left in this block")

    elif kind in ("work", "rest"):
        phase = "rest" if kind == "rest" else step.get("label", "on").lower()
        phase = phase if phase in ("hold", "on", "off", "rest") else "on"
        total = step["duration"]
        start_key = _state_key(seance_id, "phase_start")
        pause_key = _state_key(seance_id, "paused")
        elapsed_key = _state_key(seance_id, "pause_elapsed")

        if st.session_state[start_key] is None:
            st.session_state[start_key] = time.time()

        if step.get("exercise"):
            exercise_thumb(step["exercise"], step.get("side"))
        elif kind == "rest":
            st.markdown("<div class='syx-rest-icon'>Rest</div>", unsafe_allow_html=True)

        if st.session_state[pause_key]:
            elapsed = st.session_state[elapsed_key]
        else:
            elapsed = (time.time() - st.session_state[start_key]) + st.session_state[elapsed_key]

        remaining = max(0.0, total - elapsed)
        big_label = step.get("label", "")
        countdown_display(remaining, total, phase, big_label)

        c1, c2 = st.columns(2)
        with c1:
            if st.session_state[pause_key]:
                if st.button("Resume", key=f"resume_{seance_id}_{idx}", use_container_width=True):
                    st.session_state[start_key] = time.time()
                    st.session_state[pause_key] = False
                    st.rerun()
            else:
                if st.button("Pause", key=f"pause_{seance_id}_{idx}", use_container_width=True):
                    st.session_state[elapsed_key] = elapsed
                    st.session_state[pause_key] = True
                    st.rerun()
        with c2:
            if st.button("Skip", key=f"skip_{seance_id}_{idx}", use_container_width=True):
                _advance(seance_id)
                st.rerun()

        st.caption(f"{remaining_in_block(timeline, idx)} exercise(s) left in this block")

        if remaining <= 0 and not st.session_state[pause_key]:
            _advance(seance_id)
            st.rerun()

        if not st.session_state[pause_key]:
            run_autorefresh(1000, key=f"tick_{seance_id}_{idx}")
