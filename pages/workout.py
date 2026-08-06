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


# Default selection: first week that has sessions, its first session
week_ids = list(workouts.keys())
_default_week = next((w for w in week_ids if workouts[w].get("seances")), week_ids[0])
if SIDEBAR_WEEK_KEY not in st.session_state:
    st.session_state[SIDEBAR_WEEK_KEY] = _default_week
if SIDEBAR_SEANCE_KEY not in st.session_state:
    _default_seances = workouts[st.session_state[SIDEBAR_WEEK_KEY]].get("seances", [])
    st.session_state[SIDEBAR_SEANCE_KEY] = _default_seances[0]["id"] if _default_seances else None

# ============================================================
# SIDEBAR -- program tree: weeks expand to show their sessions
# ============================================================
with st.sidebar:
    st.markdown("#### Program")

    for wid, w in workouts.items():
        w_seances = w.get("seances", [])
        if not w_seances:
            st.caption(f"{w['title']} (coming soon)")
            continue

        week_done = progress.is_week_done(profile, w)
        mark = "\u2713 " if week_done else ""
        week_label = f"{mark}{w['title']}"

        with st.expander(week_label, expanded=(wid == st.session_state[SIDEBAR_WEEK_KEY])):
            for s in w_seances:
                done = progress.is_session_done(profile, s)
                s_mark = "\u2713 " if done else ""
                label = f"{s_mark}{s['title']}"
                if st.button(label, key=f"nav_{s['id']}", use_container_width=True,
                             type="primary" if done else "secondary"):
                    st.session_state[SIDEBAR_WEEK_KEY] = wid
                    st.session_state[SIDEBAR_SEANCE_KEY] = s["id"]
                    st.session_state[FLOW_KEY] = "block"
                    st.rerun()

week_choice = st.session_state[SIDEBAR_WEEK_KEY]
week = workouts[week_choice]
seance_choice = st.session_state[SIDEBAR_SEANCE_KEY]

if seance_choice is None:
    st.stop()

seance = next(s for s in week["seances"] if s["id"] == seance_choice)
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
        st.caption("Completed blocks are shown in blue.")
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

    player_key = f"{seance['id']}_{block_ref}"
    render_block_player(
        block, block_label, player_key,
        week_id=week_choice, week_title=week.get("title"),
        seance_id=seance["id"], seance_title=seance.get("title"),
        block_ref=block_ref,
    )
