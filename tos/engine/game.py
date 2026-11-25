"""Starting a game and moving between locations."""
from __future__ import annotations

from .content import Content, apply_effects
from .state import GameState, Player


def new_game(content: Content, stats: dict, tutorial: bool = True) -> tuple[GameState, list[tuple]]:
    p = Player(stats=dict(stats))
    p.recalc()
    p.hp = p.max_hp
    st = GameState(player=p)
    if tutorial:
        st.flags.add("tutorial")
    start = content.text["start"]
    place(st, content, start["location"], start["spawn"])
    events = apply_effects(start.get("effects"), st, content)
    return st, events


def place(state: GameState, content: Content, location: str, spawn: str) -> None:
    loc = content.locations[location]
    state.location = location
    state.pos = list(loc["spawns"][spawn])
    state.companion_pos = None


def follow_exit(state: GameState, content: Content, to: dict) -> str:
    """Apply an exit target. Returns 'city' or 'location'."""
    if "city" in to:
        state.location = f"city:{to['city']}"
        state.companion_pos = None
        return "city"
    place(state, content, to["location"], to["spawn"])
    return "location"
