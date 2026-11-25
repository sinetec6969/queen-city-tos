"""Region maps and travel between their nodes.

`city.yaml` holds every node. A node belongs to a region (`region:`, default "charlotte");
each region has its own canvas (`regions: {id: {name, width, height}}`). A node with
`goto: <node id>` is a gateway: picking it switches to that node's region instead of
loading a location. Both frontends call `go()`, so travel rules live in one place.
"""
from __future__ import annotations

from .content import Content, check
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


def go(state: GameState, content: Content, nid: str) -> dict:
    """Try to travel to a node. Returns {"kind": ..., "msg": str, "events": [...]}:
    locked / unbuilt (stay put), region (switched maps, still on the city screen),
    location (placed in a location; events to queue on arrival)."""
    n = node(content, nid)
    name = n["name"].title()
    if not unlocked(content, state, nid):
        return {"kind": "locked", "msg": "SERVICE UNAVAILABLE IN YOUR AREA. The Concierge thanks you for your patience.", "events": []}
    if n.get("goto"):
        state.location = f"city:{n['goto']}"
        return {"kind": "region", "msg": n.get("travel_text", f"You head for {name}."), "events": []}
    if not n.get("location"):
        return {"kind": "unbuilt", "msg": f"{name} isn't built yet. The Concierge apologizes for the inconvenience.", "events": []}
    place(state, content, n["location"], n["spawn"])
    return {"kind": "location", "msg": "", "events": [("log", f"You head back to {name}.")]}
