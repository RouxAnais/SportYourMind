import streamlit as st

from components.navbar import inject_global_css, top_banner
from components.workout_player import render_block_player
from components.session_plan import render_block_detail
from utils.load_data import load_workouts

st.set_page_config(page_title="100% Abs -- Session", layout="centered")
inject_global_css()

workouts = load_workouts()

FLOW_KEY = "_syx_flow"
WEEK_KEY = "_syx_week_id"
SEANCE_KEY = "_syx_seance_id"
BLOCK_KEY = "_syx_block_ref"


def _go(stage, **kwargs):
    st.session_state[FLOW_KEY] = stage
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


def _get_seance(week, seance_id):
    if not week:
        return None
    return next((s for s in week.get("seances", []) if s["id"] == seance_id), None)


def _get_block(seance, block_ref):
    if block_ref == "__challenge__":
        return seance.get("challenge"), f"Challenge -- {seance.get('challenge', {}).get('name', '')}"
    block = seance["blocks"][block_ref]
    return block, block.get("name", f"Block {block_ref + 1}")


flow = st.session_state.get(FLOW_KEY, "week")

# ============================================================
# STAGE 1: pick a week
# ============================================================
if flow == "week":
    top_banner("Session", "Pick your week")
    for wid, week in workouts.items():
        n = len(week.get("seances", []))
        label = week["title"] if n else f"{week['title']} (coming soon)"
        if st.button(label, key=f"week_{wid}", use_container_width=True, disabled=(n == 0)):
            _go("session", **{WEEK_KEY: wid})

# ============================================================
# STAGE 2: pick a session (1-4) within the chosen week
# ============================================================
elif flow == "session":
    week_id = st.session_state.get(WEEK_KEY)
    week = workouts.get(week_id)
    if week is None:
        _go("week")

    if st.button("< Back to weeks"):
        _go("week")

    top_banner(week["title"], "Pick today's session")
    for s in week.get("seances", []):
        if st.button(s["title"], key=f"seance_{s['id']}", use_container_width=True):
            _go("block", **{SEANCE_KEY: s["id"]})

# ============================================================
# STAGE 3: pick a block within the chosen session
# ============================================================
elif flow == "block":
    week = workouts.get(st.session_state.get(WEEK_KEY))
    seance = _get_seance(week, st.session_state.get(SEANCE_KEY))
    if seance is None:
        _go("week")

    if st.button("< Back to sessions"):
        _go("session")

    top_banner(seance["title"], "Pick a block")

    for i, block in enumerate(seance.get("blocks", [])):
        if st.button(block.get("name", f"Block {i + 1}"), key=f"pick_block_{i}", use_container_width=True):
            _go("detail", **{BLOCK_KEY: i})

    challenge = seance.get("challenge")
    if challenge:
        if st.button(f"Challenge -- {challenge.get('name', '')}", key="pick_block_challenge", use_container_width=True):
            _go("detail", **{BLOCK_KEY: "__challenge__"})

# ============================================================
# STAGE 4: block detail (full plan for just this block) + Start
# ============================================================
elif flow == "detail":
    week = workouts.get(st.session_state.get(WEEK_KEY))
    seance = _get_seance(week, st.session_state.get(SEANCE_KEY))
    block_ref = st.session_state.get(BLOCK_KEY)
    if seance is None or block_ref is None:
        _go("week")
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
# STAGE 5: player -- plays just this one block
# ============================================================
elif flow == "player":
    week = workouts.get(st.session_state.get(WEEK_KEY))
    seance = _get_seance(week, st.session_state.get(SEANCE_KEY))
    block_ref = st.session_state.get(BLOCK_KEY)
    if seance is None or block_ref is None:
        _go("week")
    block, block_label = _get_block(seance, block_ref)

    if st.button("< Back to block"):
        _go("detail")

    player_key = f"{seance['id']}_{block_ref}"
    render_block_player(
        block, block_label, player_key,
        week_id=st.session_state.get(WEEK_KEY), week_title=week.get("title"),
        seance_id=seance["id"], seance_title=seance.get("title"),
    )
