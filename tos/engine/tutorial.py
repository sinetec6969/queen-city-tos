"""New Resident Orientation: step checklist + one-time tips, driven by tutorial.yaml."""
from __future__ import annotations

from .content import Content, check
from .state import GameState

ON, DONE = "tutorial", "tutorial_done"


def active(state: GameState) -> bool:
    return ON in state.flags and DONE not in state.flags


def steps(content: Content) -> list[dict]:
    return content.tutorial.get("steps", [])


def current(state: GameState, content: Content) -> tuple[int, dict] | None:
    """(1-based index, step) of the first unfinished step, or None."""
    if not active(state):
        return None
    for i, s in enumerate(steps(content), 1):
        if f"tut:{s['id']}" not in state.flags:
            return i, s
    return None


def tip_due(state: GameState, tid: str) -> bool:
    # tips keep firing after the checklist is done (first level-up, first city visit...)
    return ON in state.flags and f"tip:{tid}" not in state.flags


def take_tip(state: GameState, tid: str) -> bool:
    """Mark a tip as shown. Returns True if it should be shown now."""
    if not tip_due(state, tid):
        return False
    state.flags.add(f"tip:{tid}")
    return True


def update(state: GameState, content: Content) -> list[tuple]:
    """Tick off finished steps and fire automatic tips. Returns UI events."""
    events: list[tuple] = []
    for tid, tip in content.tutorial.get("tips", {}).items():
        if tip.get("auto") and check(tip.get("when"), state) and take_tip(state, tid):
            events.append(("tip", tid))
    if not active(state):
        return events
    for s in steps(content):
        key = f"tut:{s['id']}"
        if key not in state.flags and check(s.get("done_if"), state):
            state.flags.add(key)
            events.append(("log", f"✓ ORIENTATION: {s['title']}"))
    now = current(state, content)
    if now is None:
        state.flags.update({"tip:complete", DONE})
        events.append(("tip", "complete"))
    elif f"tut:announced:{now[0]}" not in state.flags:
        state.flags.add(f"tut:announced:{now[0]}")
        events.append(("tutorial_step", now[0]))
    return events
