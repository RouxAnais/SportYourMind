"""Completion tracking: which blocks/sessions/weeks a profile has finished,
derived from the Google Sheets history log. Used to color-code the block
picker and the week/session sidebar filters."""
from __future__ import annotations

from utils import gsheets


def get_done_block_refs(profile: str, seance_id: str) -> set:
    """Set of block_ref values (as strings) completed by this profile for one session."""
    if not profile:
        return set()
    history = gsheets.load_history(profile)
    if history.empty or "seance_id" not in history.columns or "block_ref" not in history.columns:
        return set()
    df = history[history["seance_id"] == seance_id]
    return set(df["block_ref"].astype(str).unique().tolist())


def is_block_done(profile: str, seance_id: str, block_ref) -> bool:
    return str(block_ref) in get_done_block_refs(profile, seance_id)


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
