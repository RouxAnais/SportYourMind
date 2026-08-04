import streamlit as st

from components.navbar import inject_global_css, top_banner
from components.workout_player import render_block_player
from components.session_plan import render_block_detail
from utils.load_data import load_workouts
from utils import progress

st.set_page_config(page_title="100% Abs -- Session", layout="centered")
inject_global_css()

workouts = load_workouts()
profile = st.session_state.get("_syx_profile")

FLOW_KEY = "_syx_flow"
BLOCK_KEY = "_syx_block_ref"
SIDEBAR_WEEK_KEY = "_syx_sidebar_week"
SIDEBAR_SEANCE_KEY = "_syx_sidebar_seance"


def _go(stage, **kwargs):
    st.session_state[FLOW_KEY] = stage
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


def _get_block(seance, block_ref):
    if block_ref == "__challenge__":
        return seance.get("challenge"), f"Challenge -- {seance.get('challenge', {}).get('name', '')}"
    block = seance["blocks"][block_ref]
    return block, block.get("name", f"Block {block_ref + 1}")


# ============================================================
# SIDEBAR -- week & session filters (always visible)
# ============================================================
with st.sidebar:
    st.markdown("#### Filters")

    week_ids = list(workouts.keys())

    def _week_label(wid):
        w = workouts[wid]
        mark = "\u2713 " if progress.is_week_done(profile, w) else ""
        return f"{mark}{w['title']}"

    week_choice = st.selectbox("Week", week_ids, format_func=_week_label, key="sidebar_week_select")
    week = workouts[week_choice]
    seances = week.get("seances", [])

    if seances:
        def _seance_label(sid):
            s = next(x for x in seances if x["id"] == sid)
            mark = "\u2713 " if progress.is_session_done(profile, s) else ""
            return f"{mark}{s['title']}"

        seance_choice = st.selectbox(
            "Session", [s["id"] for s in seances], format_func=_seance_label, key="sidebar_seance_select"
        )
    else:
        seance_choice = None
        st.caption(week.get("note", "This week has not been added to the app yet."))

# Reset to the block picker whenever the sidebar selection changes
if (st.session_state.get(SIDEBAR_WEEK_KEY) != week_choice
        or st.session_state.get(SIDEBAR_SEANCE_KEY) != seance_choice):
    st.session_state[SIDEBAR_WEEK_KEY] = week_choice
    st.session_state[SIDEBAR_SEANCE_KEY] = seance_choice
    st.session_state[FLOW_KEY] = "block"

if seance_choice is None:
    st.stop()

seance = next(s for s in seances if s["id"] == seance_choice)
flow = st.session_state.get(FLOW_KEY, "block")

# ============================================================
# STAGE: pick a block within the chosen session
# ============================================================
if flow == "block":
    top_banner(seance["title"], week["title"])

    for i, block in enumerate(seance.get("blocks", [])):
        label = block.get("name", f"Block {i + 1}")
        done = progress.is_block_done(profile, seance["id"], i)
        if done:
            label = f"\u2713 {label} -- done"
        if st.button(label, key=f"pick_block_{i}", use_container_width=True,
                     type="primary" if done else "secondary"):
            _go("detail", **{BLOCK_KEY: i})

    challenge = seance.get("challenge")
    if challenge:
        done = progress.is_block_done(profile, seance["id"], "__challenge__")
        challenge_label = f"Challenge -- {challenge.get('name', '')}"
        if done:
            challenge_label = f"\u2713 {challenge_label} -- done"
        if st.button(challenge_label, key="pick_block_challenge",
                     use_container_width=True, type="primary" if done else "secondary"):
            _go("detail", **{BLOCK_KEY: "__challenge__"})

    if profile:
        st.caption("Completed blocks are shown in green.")
    else:
        st.caption("Set up a profile (see the Profile page) to track which blocks you've done.")

# ============================================================
# STAGE: block detail (full plan for just this block) + Start
# ============================================================
elif flow == "detail":
    block_ref = st.session_state.get(BLOCK_KEY)
    if block_ref is None:
        _go("block")
    block, block_label = _get_block(seance, block_ref)

    if st.button("< Back to blocks"):
        _go("block")

    col_title, col_start = st.columns([3, 1])
    with col_title:
        st.markdown(f"### {block_label}")
    with col_start:
        if st.button("Start", key="start_block", use_container_width=True):
            _go("player")

    render_block_detail(block)

# ============================================================
# STAGE: player -- plays just this one block
# ============================================================
elif flow == "player":
    block_ref = st.session_state.get(BLOCK_KEY)
    if block_ref is None:
        _go("block")
    block, block_label = _get_block(seance, block_ref)

    if st.button("< Back to block"):
        _go("detail")

    player_key = f"{seance['id']}_{block_ref}"
    render_block_player(
        block, block_label, player_key,
        week_id=week_choice, week_title=week.get("title"),
        seance_id=seance["id"], seance_title=seance.get("title"),
        block_ref=block_ref,
    )
