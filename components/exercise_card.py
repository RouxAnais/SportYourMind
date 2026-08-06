import base64
import streamlit as st
from utils.load_data import get_exercise, get_exercise_image_paths


def _image_to_data_uri(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower()
    mime = "image/png" if ext == "png" else "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def _image_gallery(image_paths, key_prefix="", centered=False):
    """Show 1 or 2 images. With centered=True (player screen), both cases use
    raw HTML/flexbox so they are reliably centered and stay side by side even
    on narrow phones -- Streamlit's own image widget/columns don't center or
    stay side-by-side reliably on mobile. With centered=False (library page,
    default), a single image keeps using st.image at full container width,
    unchanged."""
    if not image_paths:
        st.markdown(
            "<div class='syx-img-placeholder'>photo coming soon</div>",
            unsafe_allow_html=True,
        )
        return
    if len(image_paths) == 1 and not centered:
        st.image(image_paths[0], width="stretch")
        return
    imgs_html = "".join(f"<img src='{_image_to_data_uri(p)}' />" for p in image_paths)
    st.markdown(f"<div class='syx-img-row'>{imgs_html}</div>", unsafe_allow_html=True)


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
    """Inline preview used inside the workout player. Always centered, shows
    both images when the exercise has 2 (needed to understand the movement)."""
    ex = get_exercise(exercise_id)
    image_paths = get_exercise_image_paths(exercise_id)
    side_label = {"right": " (right)", "left": " (left)", "alternate": " (alternating)"}.get(side, "")

    _image_gallery(image_paths, centered=True)
    st.markdown(f"<div class='syx-ex-name-sm'>{ex['name']}{side_label}</div>", unsafe_allow_html=True)
    if ex.get("adaptation"):
        st.caption(f"Too hard? -> {ex['adaptation']}")
