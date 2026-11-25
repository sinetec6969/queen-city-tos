"""Region maps and travel between their nodes.

`city.yaml` holds every node. A node belongs to a region (`region:`, default "charlotte");
each region has its own canvas (`regions: {id: {name, width, height}}`). A node with
`goto: <node id>` is a gateway: picking it switches to that node's region instead of
loading a location. Both frontends call `go()`, so travel rules live in one place.
"""
from __future__ import annotations

import random

from .content import Content, apply_effects, check
from .game import place
from .state import GameState

DEFAULT_REGION = "charlotte"


def node(content: Content, nid: str) -> dict:
    return content.city["nodes"][nid]


def region_of(content: Content, nid: str) -> str:
    return node(content, nid).get("region", DEFAULT_REGION)


def region(content: Content, rid: str) -> dict:
    regions = content.city.get("regions", {})
    if rid in regions:
        return regions[rid]
    return {"name": "CHARLOTTE", "width": content.city.get("width", 52), "height": content.city.get("height", 15)}


def region_nodes(content: Content, rid: str) -> list[str]:
    """Node ids in a region, top to bottom then left to right (the menu order)."""
    nodes = content.city["nodes"]
    ids = [n for n in nodes if nodes[n].get("region", DEFAULT_REGION) == rid]
    return sorted(ids, key=lambda n: (nodes[n]["y"], nodes[n]["x"]))


def region_links(content: Content, rid: str) -> list:
    return [l for l in content.city.get("links", []) if region_of(content, l[0]) == rid and region_of(content, l[1]) == rid]


def current_node(state: GameState) -> str | None:
    return state.location.split(":", 1)[1] if state.location.startswith("city:") else None


def unlocked(content: Content, state: GameState, nid: str) -> bool:
    return check(node(content, nid).get("unlocked_if"), state)


def encounter_chance(state: GameState, content: Content, rid: str) -> float:
    return min(0.6, region(content, rid).get("encounter_chance", 0.0) + state.player.signal / 400)


def roll_encounter(state: GameState, content: Content, rid: str, rng: random.Random) -> dict | None:
    pool = [e for e in content.encounters if e.get("region", DEFAULT_REGION) == rid and check(e.get("if"), state)]
    if not pool:  # check first: no eligible encounters must not consume randomness (keeps chapter one stable)
        return None
    if rng.random() >= encounter_chance(state, content, rid):
        return None
    return rng.choices(pool, weights=[e.get("weight", 1) for e in pool])[0]


def go(state: GameState, content: Content, nid: str, rng: random.Random | None = None) -> dict:
    """Try to travel to a node. Returns {"kind": ..., "msg": str, "events": [...]}:
    locked / unbuilt (stay put), region (switched maps, still on the city screen),
    location (placed in a location; events to queue on arrival). With an rng, a trip to a
    different node may roll a travel encounter (data/encounters.yaml) first."""
    n = node(content, nid)
    name = n["name"].title()
    if not unlocked(content, state, nid):
        return {"kind": "locked", "msg": "SERVICE UNAVAILABLE IN YOUR AREA. The Concierge thanks you for your patience.", "events": []}
    if n.get("goto"):
        state.location = f"city:{n['goto']}"
        return {"kind": "region", "msg": n.get("travel_text", f"You head for {name}."), "events": []}
    if not n.get("location"):
        return {"kind": "unbuilt", "msg": f"{name} isn't built yet. The Concierge apologizes for the inconvenience.", "events": []}
    here = current_node(state)
    enc = roll_encounter(state, content, region_of(content, nid), rng) if rng and here and here != nid else None
    if enc and enc.get("ambush"):
        amb = enc["ambush"]
        state.taken = {k for k in state.taken if not k.startswith(amb["location"] + ":")}  # fresh every time
        state.travel_dest = nid
        place(state, content, amb["location"], amb["spawn"])
        return {"kind": "location", "msg": "", "events": [("log", f"On the way to {name}: {enc['text']}"), ("combat",)]}
    events = [("log", f"You head back to {name}.")]
    if enc:
        events = [("log", f"On the way to {name}: {enc['text']}")] + apply_effects(enc.get("effects"), state, content)
    place(state, content, n["location"], n["spawn"])
    return {"kind": "location", "msg": "", "events": events}
