"""Google Sheets-backed storage for user profiles and session completion history.

Uses the `streamlit-gsheets` connector. Requires a `[connections.gsheets]`
section in Streamlit secrets (see /docs/GSHEETS_SETUP.md for the full
step-by-step setup). The app degrades gracefully (profile features simply
show a setup notice) if the connection isn't configured yet.
"""
from __future__ import annotations

import datetime
import re
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


def _make_profile_id(first_name: str, last_name: str, birthdate_str: str) -> str:
    """A stable identifier combining first name, last name, and birthdate --
    this is what disambiguates two people who share the same name."""
    raw = f"{first_name.strip().lower()}_{last_name.strip().lower()}_{birthdate_str}"
    raw = raw.replace(" ", "-")
    return re.sub(r"[^a-z0-9_\-]", "", raw)


@st.cache_data(ttl=30)
def load_profiles() -> list[dict]:
    """Each entry: {"id", "first_name", "last_name", "birthdate", "display"}."""
    df = _safe_read(PROFILES_SHEET)
    if "id" not in df.columns:
        return []
    profiles = []
    for _, row in df.iterrows():
        first = str(row.get("first_name", "")).strip()
        last = str(row.get("last_name", "")).strip()
        birthdate = str(row.get("birthdate", "")).strip()
        pid = str(row.get("id", "")).strip()
        if not pid:
            continue
        profiles.append({
            "id": pid,
            "first_name": first,
            "last_name": last,
            "birthdate": birthdate,
            "display": f"{first} {last}".strip(),
        })
    profiles.sort(key=lambda p: p["display"].lower())
    return profiles


def create_profile(first_name: str, last_name: str, birthdate) -> tuple[bool, str]:
    """Creates (or reuses, if it already exists) a profile identified by
    first name + last name + birthdate. Returns (success, profile_id)."""
    conn = _get_conn()
    if conn is None:
        return False, ""
    first_name = first_name.strip()
    last_name = last_name.strip()
    if not first_name or not last_name or not birthdate:
        return False, ""
    birthdate_str = birthdate.isoformat() if hasattr(birthdate, "isoformat") else str(birthdate)
    profile_id = _make_profile_id(first_name, last_name, birthdate_str)
    try:
        df = _safe_read(PROFILES_SHEET)
        if "id" in df.columns and profile_id in df["id"].astype(str).values:
            return True, profile_id  # already exists, nothing to do
        new_row = pd.DataFrame([{
            "id": profile_id,
            "first_name": first_name,
            "last_name": last_name,
            "birthdate": birthdate_str,
            "created_at": datetime.datetime.now().isoformat(),
        }])
        df = pd.concat([df, new_row], ignore_index=True) if not df.empty else new_row
        conn.update(worksheet=PROFILES_SHEET, data=df)
        load_profiles.clear()
        return True, profile_id
    except Exception as e:
        st.session_state["_syx_gsheets_last_error"] = f"create_profile: {type(e).__name__}: {e}"
        return False, ""


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
