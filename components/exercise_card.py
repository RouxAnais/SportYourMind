import streamlit as st
from utils.load_data import get_exercise, get_exercise_image_paths


def _image_gallery(image_paths, key_prefix=""):
    """Show 1 or 2 images side by side (both are needed to understand the movement)."""
    if not image_paths:
        st.markdown(
            "<div class='syx-img-placeholder'>photo coming soon</div>",
            unsafe_allow_html=True,
        )
        return
    if len(image_paths) == 1:
        st.image(image_paths[0], use_container_width=True)
    else:
        cols = st.columns(len(image_paths))
        for c, p in zip(cols, image_paths):
            with c:
                st.image(p, use_container_width=True)


def exercise_card(exercise_id: str, show_adaptation: bool = True, compact: bool = False):
    ex = get_exercise(exercise_id)
    image_paths = get_exercise_image_paths(exercise_id)

    with st.container(border=True):
        cols = st.columns([1, 2]) if not compact else st.columns([1, 3])
        with cols[0]:
            _image_gallery(image_paths)
        with cols[1]:
            st.markdown(f"<div class='syx-ex-name'>{ex['name']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='syx-ex-cat'>{ex.get('category','')}</div>", unsafe_allow_html=True)
            if not compact:
                st.markdown(f"<div class='syx-ex-desc'>{ex.get('description','')}</div>", unsafe_allow_html=True)
                if show_adaptation and ex.get("adaptation"):
                    st.markdown(
                        f"<div class='syx-ex-adapt'>Easier option: {ex['adaptation']}</div>",
                        unsafe_allow_html=True,
                    )


def exercise_thumb(exercise_id: str, side: str | None = None):
    """Inline preview used inside the workout player. Shows both images when the
    exercise has 2 (needed to understand the movement), stacked above the name."""
    ex = get_exercise(exercise_id)
    image_paths = get_exercise_image_paths(exercise_id)
    side_label = {"right": " (right)", "left": " (left)", "alternate": " (alternating)"}.get(side, "")

    _image_gallery(image_paths)
    st.markdown(f"<div class='syx-ex-name-sm'>{ex['name']}{side_label}</div>", unsafe_allow_html=True)
    if ex.get("adaptation"):
        st.caption(f"Too hard? -> {ex['adaptation']}")
