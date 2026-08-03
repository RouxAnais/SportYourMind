import time
import streamlit as st

from utils.helpers import build_seance_timeline, format_time, describe_step_short
from utils.load_data import get_audio_path, get_exercise
from components.exercise_card import exercise_thumb
from components.timer import countdown_display, run_autorefresh


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


def render_workout_player(seance: dict):
    seance_id = seance["id"]
    _init_state(seance)

    timeline = st.session_state[_state_key(seance_id, "timeline")]
    idx = st.session_state[_state_key(seance_id, "idx")]

    st.markdown(f"### {seance['title']}")

    block_points = [(i, step["label"]) for i, step in enumerate(timeline) if step["kind"] == "block_title"]
    if block_points:
        with st.expander("Jump to a block"):
            cols = st.columns(len(block_points))
            for col, (target_idx, label) in zip(cols, block_points):
                short_label = "Challenge" if label.startswith("CHALLENGE") else label.split(" (")[0]
                with col:
                    if st.button(short_label, key=f"jump_{seance_id}_{target_idx}", use_container_width=True):
                        _jump_to(seance_id, target_idx)
                        st.rerun()

    st.progress(min(idx / max(len(timeline), 1), 1.0))

    if idx >= len(timeline):
        st.success("Session complete! Great work.")
        if st.button("Restart session", key=f"restart_{seance_id}"):
            _restart(seance_id)
            st.rerun()
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
            f"<div class='syx-timer-label'>{step['reps']} REPS</div>",
            unsafe_allow_html=True,
        )
        if step.get("note"):
            st.caption(step["note"])
        if st.button("Done, next step", key=f"done_{seance_id}_{idx}", use_container_width=True):
            _advance(seance_id)
            st.rerun()

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

        c1, c2, c3 = st.columns(3)
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
        with c3:
            st.caption(f"Step {idx+1} / {len(timeline)}")

        if remaining <= 0 and not st.session_state[pause_key]:
            _advance(seance_id)
            st.rerun()

        if not st.session_state[pause_key]:
            run_autorefresh(250, key=f"tick_{seance_id}_{idx}")
