import time
import streamlit as st

from utils.helpers import build_seance_timeline, build_block_timeline, describe_step_short, remaining_in_block
from utils.load_data import get_audio_path, get_exercise
from utils import gsheets
from components.exercise_card import exercise_thumb
from components.timer import countdown_display, run_autorefresh
from components.beep import play_start_beep, play_rest_beep


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
        /* Tighter vertical rhythm between elements */
        .element-container {
            margin-bottom: 0.3rem !important;
        }
        /* Icon controls (Pause/Return/Stop) -- plain HTML links in a flex
           row, NOT Streamlit buttons/columns. Streamlit auto-stacks columns
           vertically on narrow phones regardless of configuration, so this
           uses the same reliable raw-HTML technique as the exercise photos. */
        .syx-icon-row {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            margin: 8px 0;
        }
        .syx-icon-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 42px;
            height: 42px;
            border-radius: 10px;
            background: var(--syx-black-soft);
            border: 1px solid var(--syx-border);
            color: var(--syx-white) !important;
            font-size: 1.15rem;
            text-decoration: none !important;
        }
        .syx-icon-btn:hover {
            background: var(--syx-accent-dim);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_icon_row(actions):
    """actions: list of (query_value, icon_char) tuples. Renders a small,
    tightly-packed, centered row of icon links (not Streamlit buttons)."""
    links = "".join(
        f"<a href='?nav={val}' class='syx-icon-btn' target='_self'>{icon}</a>"
        for val, icon in actions
    )
    st.markdown(f"<div class='syx-icon-row'>{links}</div>", unsafe_allow_html=True)


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


def _go_back(player_key: str):
    idx_key = _k(player_key, "idx")
    st.session_state[idx_key] = max(0, st.session_state[idx_key] - 1)
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


def _toggle_pause(player_key: str):
    pause_key = _k(player_key, "paused")
    start_key = _k(player_key, "phase_start")
    elapsed_key = _k(player_key, "pause_elapsed")
    if st.session_state.get(pause_key):
        st.session_state[start_key] = time.time()
        st.session_state[pause_key] = False
    else:
        if st.session_state.get(start_key):
            elapsed_so_far = (time.time() - st.session_state[start_key]) + st.session_state.get(elapsed_key, 0.0)
            st.session_state[elapsed_key] = elapsed_so_far
        st.session_state[pause_key] = True


def _handle_nav_action(player_key: str):
    """Handle a click from the HTML icon row (Return/Stop/Pause), read from
    the URL query params since these are plain links, not Streamlit buttons."""
    action = st.query_params.get("nav")
    if not action:
        return
    st.query_params.clear()
    if action == "return":
        _go_back(player_key)
    elif action == "stop":
        st.session_state["_syx_flow"] = "block"
    elif action == "pause":
        _toggle_pause(player_key)
    st.rerun()


def _render_nav_controls(player_key: str, idx: int):
    """Next (big, always the same) to move forward. Return/Stop as a small
    icon row below."""
    if st.button("Next", key=f"next_{player_key}_{idx}", use_container_width=True):
        _advance(player_key)
        st.rerun()
    _render_icon_row([("return", "\u21A9\ufe0f"), ("stop", "\u23F9\ufe0f")])


def _play_timeline(player_key: str, timeline: list, on_finished):
    """Core playback engine: steps through `timeline`, one exercise/rest at a
    time, with beeps and a next-up preview. `on_finished` is called (and
    should render its own completion UI) once the timeline is exhausted."""
    _init_state(player_key, timeline)
    _handle_nav_action(player_key)
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

        st.caption(f"{remaining_in_block(timeline, idx)} exercise(s) left")

        # Next -- always the same, full width, same position as every other screen
        if st.button("Next", key=f"next_{player_key}_{idx}", use_container_width=True):
            _advance(player_key)
            st.rerun()

        pause_icon = "\u25B6\ufe0f" if st.session_state[pause_key] else "\u23F8\ufe0f"
        _render_icon_row([("pause", pause_icon), ("return", "\u21A9\ufe0f"), ("stop", "\u23F9\ufe0f")])

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
