"""Completion tracking: which blocks/sessions/weeks a profile has finished,
derived from the Google Sheets history log. Used to color-code the block
picker and the week/session sidebar filters."""
from __future__ import annotations

from utils import gsheets


def _norm_ref(value) -> str:
    """Normalize a block_ref for comparison: Google Sheets / pandas sometimes
    round-trips a written "0" as the float 0.0 (e.g. when a column mixes
    blank legacy rows with numeric-looking values), which would otherwise
    silently break string matching ("0" != "0.0")."""
    s = str(value).strip()
    if s.endswith(".0"):
        try:
            s = str(int(float(s)))
        except ValueError:
            pass
    return s


def get_done_block_refs(profile: str, seance_id: str) -> set:
    """Set of block_ref values (normalized strings) completed by this profile for one session."""
    if not profile:
        return set()
    history = gsheets.load_history(profile)
    if history.empty or "seance_id" not in history.columns or "block_ref" not in history.columns:
        return set()
    df = history[history["seance_id"] == seance_id]
    return {_norm_ref(v) for v in df["block_ref"].tolist()}


def is_block_done(profile: str, seance_id: str, block_ref) -> bool:
    return _norm_ref(block_ref) in get_done_block_refs(profile, seance_id)


def is_session_done(profile: str, seance: dict) -> bool:
    if not profile:
        return False
    total_units = len(seance.get("blocks", [])) + (1 if seance.get("challenge") else 0)
    if total_units == 0:
        return False
    done_refs = get_done_block_refs(profile, seance["id"])
    return len(done_refs) >= total_units


def is_week_done(profile: str, week: dict) -> bool:
    if not profile:
        return False
    seances = week.get("seances", [])
    if not seances:
        return False
    return all(is_session_done(profile, s) for s in seances)


def get_next_session(profile: str, workouts: dict) -> dict | None:
    """The first session that isn't fully done yet, walking weeks/sessions in
    order. Returns None if the whole program is complete."""
    if not profile:
        return None
    for week_id, week in workouts.items():
        for seance in week.get("seances", []):
            if not is_session_done(profile, seance):
                return {
                    "week_id": week_id,
                    "week_title": week.get("title", ""),
                    "seance_id": seance["id"],
                    "seance_title": seance.get("title", ""),
                }
    return None


def get_overall_progress(profile: str, workouts: dict) -> tuple[int, int]:
    """(completed_sessions, total_sessions) across the whole program."""
    total = 0
    done = 0
    if not profile:
        return 0, sum(len(w.get("seances", [])) for w in workouts.values())
    for week in workouts.values():
        for seance in week.get("seances", []):
            total += 1
            if is_session_done(profile, seance):
                done += 1
    return done, total
