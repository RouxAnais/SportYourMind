"""Google Sheets-backed storage for user profiles and session completion history.

Uses the `streamlit-gsheets` connector. Requires a `[connections.gsheets]`
section in Streamlit secrets (see /docs/GSHEETS_SETUP.md for the full
step-by-step setup). The app degrades gracefully (profile features simply
show a setup notice) if the connection isn't configured yet.
"""
from __future__ import annotations

import datetime
import pandas as pd
import streamlit as st

try:
    from streamlit_gsheets import GSheetsConnection
    _HAS_GSHEETS_PKG = True
except ImportError:
    _HAS_GSHEETS_PKG = False

PROFILES_SHEET = "profiles"
HISTORY_SHEET = "history"


@st.cache_resource
def _get_conn():
    if not _HAS_GSHEETS_PKG:
        return None
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception:
        return None


def is_configured() -> bool:
    return _get_conn() is not None


def _safe_read(worksheet: str) -> pd.DataFrame:
    conn = _get_conn()
    if conn is None:
        return pd.DataFrame()
    try:
        df = conn.read(worksheet=worksheet, ttl=0)
        return df.dropna(how="all")
    except Exception as e:
        st.session_state["_syx_gsheets_last_error"] = f"read({worksheet}): {type(e).__name__}: {e}"
        return pd.DataFrame()


@st.cache_data(ttl=30)
def load_profiles() -> list[str]:
    df = _safe_read(PROFILES_SHEET)
    if "name" not in df.columns:
        return []
    return sorted(df["name"].astype(str).unique().tolist())


def create_profile(name: str) -> bool:
    conn = _get_conn()
    if conn is None:
        return False
    name = name.strip()
    if not name:
        return False
    try:
        df = _safe_read(PROFILES_SHEET)
        if "name" in df.columns and name in df["name"].astype(str).values:
            return True  # already exists, nothing to do
        new_row = pd.DataFrame([{"name": name, "created_at": datetime.datetime.now().isoformat()}])
        df = pd.concat([df, new_row], ignore_index=True) if not df.empty else new_row
        conn.update(worksheet=PROFILES_SHEET, data=df)
        load_profiles.clear()
        return True
    except Exception as e:
        st.session_state["_syx_gsheets_last_error"] = f"create_profile: {type(e).__name__}: {e}"
        return False


def log_completion(profile: str, week_id: str, week_title: str, seance_id: str, seance_title: str,
                    block_ref: str = "") -> bool:
    conn = _get_conn()
    if conn is None:
        return False
    try:
        df = _safe_read(HISTORY_SHEET)
        new_row = pd.DataFrame([{
            "profile": profile,
            "week_id": week_id or "",
            "week_title": week_title or "",
            "seance_id": seance_id or "",
            "seance_title": seance_title or "",
            "block_ref": str(block_ref) if block_ref != "" else "",
            "completed_at": datetime.datetime.now().isoformat(),
        }])
        df = pd.concat([df, new_row], ignore_index=True) if not df.empty else new_row
        conn.update(worksheet=HISTORY_SHEET, data=df)
        load_history.clear()  # bust the cache so the just-completed block shows up right away
        return True
    except Exception:
        return False


@st.cache_data(ttl=20)
def load_history(profile: str) -> pd.DataFrame:
    """Cached for 20s -- this is read on every block/session/week label render,
    including while a timer is ticking (reruns every second), so an uncached
    live Google Sheets call on every tick was causing the countdown to stall.
    Busted immediately after a new completion is logged (see log_completion)."""
    df = _safe_read(HISTORY_SHEET)
    if "profile" not in df.columns:
        return pd.DataFrame()
    return df[df["profile"] == profile].copy()
