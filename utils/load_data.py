"""Data loading helpers for exercises.json and workouts.json."""
from __future__ import annotations

import json
import os
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images")
AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "audio")


@st.cache_data
def load_exercises() -> dict:
    """Return the full exercises dict: {"category_illustrations": {...}, "exercises": {...}}"""
    path = os.path.join(DATA_DIR, "exercises.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_workouts() -> dict:
    """Return the full workouts dict, keyed by week (semaine_1, semaine_2, ...)."""
    path = os.path.join(DATA_DIR, "workouts.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_exercise(exercise_id: str) -> dict:
    """Look up a single exercise by id. Returns a safe fallback if missing."""
    data = load_exercises()
    ex = data.get("exercises", {}).get(exercise_id)
    if ex is None:
        return {"name": exercise_id.replace("_", " ").title(), "category": "?",
                "description": "", "adaptation": None, "images": []}
    return ex


def get_exercise_image_path(exercise_id: str, index: int = 0) -> str | None:
    """Return the filesystem path to an exercise's image, trying common extensions."""
    ex = get_exercise(exercise_id)
    images = ex.get("images", [])
    if not images or index >= len(images):
        return None
    base_name = images[index]
    for ext in (".jpg", ".jpeg", ".png", ".JPG", ".PNG"):
        candidate = os.path.join(IMAGES_DIR, base_name + ext)
        if os.path.exists(candidate):
            return candidate
    return None


def get_exercise_image_paths(exercise_id: str) -> list[str]:
    """Return filesystem paths for ALL of an exercise's images (1 or 2), skipping any not found on disk."""
    ex = get_exercise(exercise_id)
    images = ex.get("images", [])
    paths = []
    for i in range(len(images)):
        p = get_exercise_image_path(exercise_id, i)
        if p:
            paths.append(p)
    return paths


def get_audio_path(base_name: str) -> str | None:
    """Look up a user-supplied audio file in the audio/ folder (mp3/wav/m4a/ogg).
    Returns None if the person hasn't added the file themselves -- the app never
    ships or fetches copyrighted music on its own."""
    if not base_name:
        return None
    for ext in (".mp3", ".m4a", ".wav", ".ogg", ".MP3", ".M4A", ".WAV"):
        candidate = os.path.join(AUDIO_DIR, base_name + ext)
        if os.path.exists(candidate):
            return candidate
    return None


def list_weeks() -> list[str]:
    workouts = load_workouts()
    return list(workouts.keys())


def get_week(week_id: str) -> dict:
    return load_workouts().get(week_id, {})


def get_seance(week_id: str, seance_id: str) -> dict | None:
    week = get_week(week_id)
    for seance in week.get("seances", []):
        if seance.get("id") == seance_id:
            return seance
    return None
