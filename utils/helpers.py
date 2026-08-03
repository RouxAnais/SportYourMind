"""Misc helpers: time formatting and turning a séance's blocks into a flat playable timeline."""


def format_duration_short(seconds) -> str:
    if seconds is None:
        return ""
    seconds = int(seconds)
    if seconds >= 60 and seconds % 60 == 0:
        return f"{seconds // 60} min"
    return f"{seconds}s"


def _side_suffix(side) -> str:
    return {"right": " (right)", "left": " (left)", "alternate": " (alternating)"}.get(side, "")


def describe_step_short(step: dict, get_exercise_fn) -> str:
    """One-line, human-readable summary of a timeline step: exercise + time/reps,
    or a rest line. Used for the 'coming up next' preview in the player."""
    kind = step.get("kind")
    if kind == "rest":
        return f"Rest -- {format_duration_short(step['duration'])}"
    if kind == "reps":
        name = get_exercise_fn(step["exercise"])["name"] if step.get("exercise") else ""
        return f"{name}{_side_suffix(step.get('side'))} -- {step['reps']} reps"
    if kind == "work":
        name = get_exercise_fn(step["exercise"])["name"] if step.get("exercise") else ""
        return f"{name}{_side_suffix(step.get('side'))} -- {format_duration_short(step['duration'])}"
    if kind == "manual":
        name = get_exercise_fn(step["exercise"])["name"] if step.get("exercise") else ""
        return f"{name}{_side_suffix(step.get('side'))}" if name else "Follow the music"
    if kind == "block_title":
        return step.get("label", "Next block")
    if kind == "note":
        return "Instructions"
    return ""


def _plan_rows_from_steps(steps, get_exercise_fn) -> list[dict]:
    rows = []
    for step in steps:
        if step["kind"] == "rest":
            rows.append({"type": "rest", "label": f"Rest -- {format_duration_short(step['duration'])}"})
        elif step["kind"] == "reps":
            name = get_exercise_fn(step["exercise"])["name"] if step["exercise"] else ""
            meta = f"{step['reps']} reps"
            if step.get("note"):
                meta += f" ({step['note']})"
            rows.append({"type": "work", "exercise": name + _side_suffix(step.get("side")), "meta": meta})
        elif step["kind"] == "work":
            name = get_exercise_fn(step["exercise"])["name"] if step["exercise"] else ""
            meta = format_duration_short(step["duration"])
            if step.get("note"):
                meta += f" ({step['note']})"
            rows.append({"type": "work", "exercise": name + _side_suffix(step.get("side")), "meta": meta})
        elif step["kind"] == "manual":
            name = get_exercise_fn(step["exercise"])["name"] if step.get("exercise") else ""
            rows.append({"type": "work", "exercise": name + _side_suffix(step.get("side")), "meta": step.get("label", "")})
    return rows


def build_readable_plan(seance: dict, get_exercise_fn) -> list[dict]:
    """Build a static, at-a-glance plan of the whole session: one entry per block
    (+ one for the challenge), each with a title, an optional note, and readable rows
    (exercise name + work time/reps, or a rest line). Used for the 'Session details'
    view -- no timer/interactivity, just the full plan to read at a glance."""
    plan = []
    blocks = seance.get("blocks", [])
    rest_between_blocks = seance.get("rest_between_blocks", 0)

    for i, block in enumerate(blocks):
        rows = _plan_rows_from_steps(build_block_timeline(block), get_exercise_fn)
        entry = {"title": block.get("name", f"Block {i+1}"), "note": block.get("note"), "rows": rows,
                 "always_show_note": block.get("always_show_note", False)}
        if i < len(blocks) - 1 and rest_between_blocks:
            entry["rest_after_block"] = format_duration_short(rest_between_blocks)
        plan.append(entry)

    challenge = seance.get("challenge")
    if challenge:
        if blocks:
            plan[-1]["rest_after_block"] = format_duration_short(60)
        rows = _plan_rows_from_steps(build_block_timeline(challenge), get_exercise_fn)
        plan.append({"title": f"Challenge -- {challenge.get('name', '')}", "note": challenge.get("note"), "rows": rows, "is_challenge": True})

    return plan


def format_time(seconds: int) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m:01d}:{s:02d}"


def _step(exercise, kind, duration=None, reps=None, label=None, side=None, note=None,
          audio_file=None, external_link=None):
    return {
        "exercise": exercise,
        "kind": kind,  # "work" (timed), "reps" (untimed, user confirms), "rest"
        "duration": duration,
        "reps": reps,
        "label": label,
        "side": side,
        "note": note,
        "audio_file": audio_file,
        "external_link": external_link,
    }


def build_block_timeline(block: dict) -> list[dict]:
    """Turn one block dict from workouts.json into a flat list of steps to play through."""
    steps = []
    block_type = block.get("type")
    rest_between = block.get("rest_between", 0)

    if block_type in ("hold", "on", "nostop", "rep"):
        rounds = block.get("rounds", [])
        for i, r in enumerate(rounds):
            if "duration" in r and r["duration"] is not None:
                steps.append(_step(r["exercise"], "work", duration=r["duration"],
                                    label=block_type.upper(), side=r.get("side")))
            elif "reps" in r:
                steps.append(_step(r["exercise"], "reps", reps=r["reps"],
                                    label="REP", side=r.get("side")))
            if rest_between and i < len(rounds) - 1:
                steps.append(_step(None, "rest", duration=rest_between, label="OFF"))

    elif block_type == "sequence":
        # These blocks are always performed right leg then left leg (as described in the book)
        repeat = block.get("repeat", 1)
        for _ in range(repeat):
            for side in ["right", "left"]:
                for r in block.get("rounds", []):
                    if "duration" in r and r["duration"] is not None:
                        steps.append(_step(r["exercise"], "work", duration=r["duration"],
                                            label="HOLD", side=side, note=r.get("note")))
                    elif "reps" in r:
                        steps.append(_step(r["exercise"], "reps", reps=r["reps"],
                                            label="REP", side=side, note=r.get("note")))
                if rest_between:
                    steps.append(_step(None, "rest", duration=rest_between, label="OFF"))

    elif block_type == "chain":
        # Fully explicit list of rounds, each with its own optional "rest_after" (in
        # seconds). Used whenever the rest pattern is irregular (rest after every
        # exercise, or only after certain ones) rather than a uniform rest_between.
        for r in block.get("rounds", []):
            if "duration" in r and r["duration"] is not None:
                steps.append(_step(r["exercise"], "work", duration=r["duration"],
                                    label=r.get("label", "ON"), side=r.get("side"), note=r.get("note")))
            elif "reps" in r:
                steps.append(_step(r["exercise"], "reps", reps=r["reps"],
                                    label="REP", side=r.get("side"), note=r.get("note")))
            if r.get("rest_after"):
                steps.append(_step(None, "rest", duration=r["rest_after"], label="OFF"))

    elif block_type == "AB_couple":
        ex_a, ex_b = block.get("exercise_a"), block.get("exercise_b")
        for item in block.get("sequence", []):
            ex = ex_a if item.get("who") == "A" else ex_b
            if "duration" in item:
                steps.append(_step(ex, "work", duration=item["duration"], label="ON", side=block.get("side")))
            elif "reps" in item:
                steps.append(_step(ex, "reps", reps=item["reps"], label="REP", side=block.get("side")))
            if item.get("rest_after"):
                steps.append(_step(None, "rest", duration=item["rest_after"], label="OFF"))

    elif block_type in ("tabata", "hold_chain", "music_cue"):
        rounds = block.get("rounds", [])
        rb = block.get("rest_between", 0)
        audio_file = block.get("audio_file")
        external_link = block.get("external_link")
        for i, r in enumerate(rounds):
            if r.get("duration") is None:
                steps.append(_step(r["exercise"], "manual", label="Follow the music", side=r.get("side"),
                                    audio_file=audio_file, external_link=external_link))
            else:
                steps.append(_step(r["exercise"], "work", duration=r["duration"],
                                    label="ON/HOLD", side=r.get("side")))
            if rb and i < len(rounds) - 1:
                steps.append(_step(None, "rest", duration=rb, label="OFF"))

    return steps


def build_seance_timeline(seance: dict) -> list[dict]:
    """Full playable timeline for a séance: all blocks (with rest between blocks) + challenge."""
    timeline = []
    blocks = seance.get("blocks", [])
    rest_between_blocks = seance.get("rest_between_blocks", 60)

    for i, block in enumerate(blocks):
        timeline.append(_step(None, "block_title", label=block.get("name", f"Bloc {i+1}")))
        if block.get("always_show_note") and block.get("note"):
            timeline.append(_step(None, "note", label=block["note"]))
        timeline.extend(build_block_timeline(block))
        if i < len(blocks) - 1 and rest_between_blocks:
            timeline.append(_step(None, "rest", duration=rest_between_blocks, label="Rest"))

    challenge = seance.get("challenge")
    if challenge:
        timeline.append(_step(None, "rest", duration=60, label="Rest before the challenge"))
        timeline.append(_step(None, "block_title", label=f"CHALLENGE : {challenge.get('name', '')}",
                               audio_file=challenge.get("audio_file"), external_link=challenge.get("external_link")))
        if challenge.get("note"):
            timeline.append(_step(None, "note", label=challenge["note"]))
        timeline.extend(build_block_timeline(challenge))

    return timeline
