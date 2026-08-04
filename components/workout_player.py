import time
import streamlit as st

from utils.helpers import build_seance_timeline, build_block_timeline, describe_step_short, remaining_in_block
from utils.load_data import get_audio_path, get_exercise
from utils import gsheets
from components.exercise_card import exercise_thumb
from components.timer import countdown_display, run_autorefresh
from components.beep import play_start_beep, play_rest_beep


def _inject_fullscreen_css():
    """Edge-to-edge training screen: fixed header (block name + progress strip)
    and fixed footer (Pause/Resume + Skip, full width, split in two) -- only
    while actually training, not on the rest of the app."""
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 90px !important;
            padding-bottom: 90px !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }
        [data-testid="stMainBlockContainer"] {
            padding-top: 90px !important;
        }

        /* Fixed header -- block name */
        .syx-player-header {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 64px;
            background: var(--syx-black-soft);
            border-bottom: 1px solid var(--syx-border);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 1rem;
            color: var(--syx-white);
            z-index: 1000;
            text-align: center;
            padding: 0 1rem;
        }
        .syx-player-loader {
            position: fixed;
            top: 64px;
            left: 0;
            width: 100%;
            height: 4px;
            background: var(--syx-border);
            z-index: 1000;
        }
        .syx-player-loader-fill {
            height: 100%;
            background: var(--syx-accent);
            transition: width 0.3s ease;
        }

        /* Fixed footer -- Pause/Resume + Skip, full width, split in two */
        [data-testid="stHorizontalBlock"] {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 64px;
            margin: 0 !important;
            background: var(--syx-black-soft);
            border-top: 1px solid var(--syx-border);
            z-index: 1000;
        }
        [data-testid="stHorizontalBlock"] [data-testid="column"] {
            height: 100%;
            display: flex;
            align-items: stretch;
        }
        [data-testid="stHorizontalBlock"] [data-testid="column"]:last-child {
            border-left: 1px solid var(--syx-border);
        }
        [data-testid="stHorizontalBlock"] .stButton {
            width: 100%;
            height: 100%;
        }
        [data-testid="stHorizontalBlock"] .stButton > button {
            width: 100%;
            height: 100%;
            border-radius: 0 !important;
            border: none !important;
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
        st.session_state[_k(player_key, "logged")] = False


def _advance(player_key: str):
    st.session_state[_k(player_key, "idx")] += 1
    st.session_state[_k(player_key, "phase_start")] = None
    st.session_state[_k(player_key, "pause_elapsed")] = 0.0
    st.session_state[_k(player_key, "paused")] = False


def _restart(player_key: str):
    st.session_state[_k(player_key, "idx")] = 0
    st.session_state[_k(player_key, "phase_start")] = None
    st.session_state[_k(player_key, "pause_elapsed")] = 0.0
    st.session_state[_k(player_key, "paused")] = False
    st.session_state[_k(player_key, "logged")] = False


def _jump_to(player_key: str, target_idx: int):
    st.session_state[_k(player_key, "idx")] = target_idx
    st.session_state[_k(player_key, "phase_start")] = None
    st.session_state[_k(player_key, "pause_elapsed")] = 0.0
    st.session_state[_k(player_key, "paused")] = False


def _play_timeline(player_key: str, timeline: list, on_finished):
    """Core playback engine: steps through `timeline`, one exercise/rest at a
    time, with pause/skip/beeps/next-up preview. `on_finished` is called (and
    should render its own completion UI) once the timeline is exhausted."""
    _init_state(player_key, timeline)
    idx = st.session_state[_k(player_key, "idx")]

    if idx >= len(timeline):
        on_finished(player_key)
        return

    step = timeline[idx]
    kind = step["kind"]

    # Play a beep the first time we render this step (not on every autorefresh tick)
    beeped_key = _k(player_key, "beeped_idx")
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

        if st.button("Continue", key=f"cont_{player_key}_{idx}", use_container_width=True):
            _advance(player_key)
            st.rerun()

    elif kind == "note":
        st.info(step["label"])
        if st.button("Got it, continue", key=f"cont_{player_key}_{idx}", use_container_width=True):
            _advance(player_key)
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

        if st.button("Next step", key=f"cont_{player_key}_{idx}", use_container_width=True):
            _advance(player_key)
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
        if st.button("Done, next step", key=f"done_{player_key}_{idx}", use_container_width=True):
            _advance(player_key)
            st.rerun()
        st.caption(f"{remaining_in_block(timeline, idx)} exercise(s) left")

    elif kind in ("work", "rest"):
        phase = "rest" if kind == "rest" else step.get("label", "on").lower()
        phase = phase if phase in ("hold", "on", "off", "rest") else "on"
        total = step["duration"]
        start_key = _k(player_key, "phase_start")
        pause_key = _k(player_key, "paused")
        elapsed_key = _k(player_key, "pause_elapsed")

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
                if st.button("Resume", key=f"resume_{player_key}_{idx}", use_container_width=True):
                    st.session_state[start_key] = time.time()
                    st.session_state[pause_key] = False
                    st.rerun()
            else:
                if st.button("Pause", key=f"pause_{player_key}_{idx}", use_container_width=True):
                    st.session_state[elapsed_key] = elapsed
                    st.session_state[pause_key] = True
                    st.rerun()
        with c2:
            if st.button("Skip", key=f"skip_{player_key}_{idx}", use_container_width=True):
                _advance(player_key)
                st.rerun()

        st.caption(f"{remaining_in_block(timeline, idx)} exercise(s) left")

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
    moving to another block is a manual, user-driven action (Back to blocks)."""
    _inject_fullscreen_css()
    timeline = build_block_timeline(block)
    idx_now = st.session_state.get(_k(player_key, "idx"), 0)
    pct = min(idx_now / max(len(timeline), 1), 1.0)
    st.markdown(f"<div class='syx-player-header'>{block_label}</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='syx-player-loader'><div class='syx-player-loader-fill' "
        f"style='width:{pct * 100:.1f}%;'></div></div>",
        unsafe_allow_html=True,
    )

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
        if st.button("Restart this block", key=f"restart_{pkey}"):
            _restart(pkey)
            st.rerun()

    _play_timeline(player_key, timeline, on_finished)
