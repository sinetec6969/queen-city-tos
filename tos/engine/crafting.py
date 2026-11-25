"""Crafting at a workbench: consumables and weapon mods, defined in data/recipes.yaml.

A location tagged `workbench` allows crafting. A recipe takes `inputs` and either gives an
`output` item or puts a `mod` on the equipped weapon (`applies: melee|ranged`, plus `acc`
and/or `dmg`). Mods live in `Player.mods` ({weapon id: [recipe ids]}) and are folded into
the weapon by `weapon_stats()`, which combat uses.
"""
from __future__ import annotations

from .content import Content, apply_effects, check, describe_check
from .state import GameState

MAX_MODS = 2


def at_workbench(state: GameState, content: Content) -> bool:
    loc = content.locations.get(state.location)
    return bool(loc) and "workbench" in loc.get("tags", [])


def weapon_kind(item: dict) -> str:
    return "melee" if item.get("melee") else "ranged"


def weapon_stats(state: GameState, content: Content, wid: str) -> dict:
    """The weapon's item dict with any mods applied (a copy; content is never changed)."""
    w = dict(content.item(wid))
    for rid in state.player.mods.get(wid, []):
        m = content.recipes.get(rid, {}).get("mod", {})
        w["acc"] = w.get("acc", 0) + m.get("acc", 0)
        if m.get("dmg") and w.get("dmg"):
            w["dmg"] = [w["dmg"][0] + m["dmg"], w["dmg"][1] + m["dmg"]]
    return w


def weapon_label(state: GameState, content: Content, wid: str) -> str:
    n = len(state.player.mods.get(wid, []))
    return content.item(wid)["name"] + (f" +{n}" if n else "")


def check_recipe(state: GameState, content: Content, rid: str) -> str | None:
    """None if it can be crafted right now, else the reason it can't."""
    r = content.recipes[rid]
    p = state.player
    if not at_workbench(state, content):
        return "You need a workbench."
    missing = [f"{n - p.inventory.get(i, 0)} {content.item(i)['name']}" for i, n in r["inputs"].items() if not p.has(i, n)]
    if missing:
        return "Missing " + ", ".join(missing) + "."
    if not check(r.get("requires"), state):
        return f"Needs {describe_check(r.get('requires'))}."
    if "mod" in r:
        w = content.item(p.weapon)
        if p.weapon == "fists" or w.get("type") != "weapon":
            return "Equip a weapon to mod first."
        if weapon_kind(w) != r["mod"]["applies"]:
            return f"That mod is for {r['mod']['applies']} weapons."
        mods = p.mods.get(p.weapon, [])
        if rid in mods:
            return f"Your {w['name']} already has it."
        if len(mods) >= MAX_MODS:
            return f"Your {w['name']} can't take more than {MAX_MODS} mods."
    return None


def craft(state: GameState, content: Content, rid: str) -> tuple[bool, list[tuple]]:
    why = check_recipe(state, content, rid)
    if why:
        return False, [("log", why)]
    r, p = content.recipes[rid], state.player
    for i, n in r["inputs"].items():
        p.take(i, n)
    if "mod" in r:
        p.mods.setdefault(p.weapon, []).append(rid)
        return True, [("log", f"Crafted {r['name'].replace('Mod: ', '')} onto your {content.item(p.weapon)['name']}.")]
    out = r["output"]
    return True, apply_effects([{"give": out["item"], "n": out.get("n", 1)}], state, content)


def ingredients(content: Content, rid: str) -> str:
    return ", ".join(f"{n} {content.item(i)['name']}" for i, n in content.recipes[rid]["inputs"].items())
