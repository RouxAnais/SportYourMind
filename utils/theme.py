"""Central color palette for the SPORT YOUR MIND app.
Palette matches the "100% Abdos" book cover: electric indigo/blue-violet as the
main accent, a soft pale blue as a secondary highlight. Flat colors, no gradients.
"""

COLORS = {
    "black": "#0E0E13",
    "black_soft": "#17171F",
    "card": "#1D1D27",
    "border": "#2B2B36",
    "accent": "#5B4FE8",       # electric indigo/blue-violet (book title color)
    "accent_dim": "#443CB0",   # deeper shade for hover/secondary
    "accent_2": "#9AD4F0",     # pale sky blue (book subtitle color)
    "white": "#F2F1EE",
    "grey": "#96979E",
    "done": "#3FAE73",          # success green -- reserved for completion indicators only
}

# Phase colors used by the workout timer.
PHASE_COLORS = {
    "on": COLORS["accent"],
    "hold": COLORS["accent"],
    "rep": COLORS["accent"],
    "off": COLORS["grey"],
    "rest": COLORS["grey"],
    "all_out": COLORS["accent"],
    "tabata": COLORS["accent"],
}
