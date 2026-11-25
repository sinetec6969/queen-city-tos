"""Loads YAML content and evaluates the shared condition/effect language.

Content files never touch Python. Conditions and effects are small dicts:

  conditions: {flag: x} {not_flag: x} {stat: Charm, gte: 3} {item: x}
              {quest: id, gte: 2} {quest_done: id} {weapon: x} {taken: "loc:entity"}
              {steps: n} {signal_gte: n} {hp_below: 0.5} {level_gte: n} {cells_gte: n}
              {any: [cond-or-list, ...]}   (true if any one of them holds)
  effects:    {set: x} {unset: x} {give: item, n: 1} {take: item, n: 1}
              {cells: n} {xp: n} {quest: id, stage: 2|done} {note: [title, body]}
              {log: text} {signal: n} {heal: n} {game_over: text}
              {companion: id} {take_entity: "loc:entity"} (removes it from the world)
              {stat_up: Aim, n: 1} (permanent, capped at STAT_CAP)
              {max_hp: n} (permanent max-HP bonus; also heals that much)

Enemy entities may also carry `on_death: [effects]` and
`phases: [{hp_below: 0.5, effects: [...]}]` (each phase runs once, the first time
the enemy drops below that fraction of its max HP; see Combat.phases).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from .state import STAT_CAP, GameState

DATA = Path(__file__).resolve().parent.parent / "data"
# libyaml's loader is ~10x faster; it matters on a Pi, where every packet connection starts a new process
_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class Content:
    def __init__(self, root: Path = DATA):
        self.root = root
        self.items = self._load("items.yaml")
        self.enemies = self._load("enemies.yaml")
        self.quests = self._load("quests.yaml")
        self.city = self._load("city.yaml")
        self.surprises = self._load("surprises.yaml")
        self.hack_words = self._load("hack_words.yaml")
        self.text = self._load("text.yaml")
        self.tutorial = self._load("tutorial.yaml")
        self.companions = self._load("companions.yaml")
        self.perks = self._load("perks.yaml")
        self.recipes = self._load("recipes.yaml")
        self.locations = self._load_dir("locations")
        self.dialogues = self._load_dir("dialogues")

    def _load(self, name: str):
        with open(self.root / name, encoding="utf-8") as f:
            return yaml.load(f, Loader=_LOADER) or {}

    def _load_dir(self, name: str) -> dict:
        out = {}
        for p in sorted((self.root / name).glob("*.yaml")):
            with open(p, encoding="utf-8") as f:
                out.update(yaml.load(f, Loader=_LOADER) or {})
        return out

    def item(self, iid: str) -> dict:
        return self.items.get(iid, {"name": iid, "type": "junk"})


@lru_cache(maxsize=1)
def get_content() -> Content:
    return Content()


# ---- conditions ---------------------------------------------------------
def quest_stage(state: GameState, qid: str) -> int:
    s = state.quests.get(qid, 0)
    return 999 if s == "done" else int(s)


def check_one(cond: dict, state: GameState) -> bool:
    p = state.player
    if "flag" in cond:
        return cond["flag"] in state.flags
    if "not_flag" in cond:
        return cond["not_flag"] not in state.flags
    if "stat" in cond:
        return p.stats.get(cond["stat"], 0) >= cond.get("gte", 1)
    if "item" in cond:
        return p.has(cond["item"], cond.get("n", 1))
    if "quest" in cond:
        return quest_stage(state, cond["quest"]) >= cond.get("gte", 1)
    if "quest_done" in cond:
        return state.quests.get(cond["quest_done"]) == "done"
    if "weapon" in cond:
        return p.weapon == cond["weapon"]
    if "taken" in cond:
        return cond["taken"] in state.taken
    if "steps" in cond:
        return state.steps >= cond["steps"]
    if "signal_gte" in cond:
        return p.signal >= cond["signal_gte"]
    if "hp_below" in cond:
        return p.hp < p.max_hp * cond["hp_below"]
    if "level_gte" in cond:
        return p.level >= cond["level_gte"]
    if "cells_gte" in cond:
        return p.cells >= cond["cells_gte"]
    if "any" in cond:
        return any(check(c, state) for c in cond["any"])
    raise ValueError(f"unknown condition {cond!r}")


def check(conds, state: GameState) -> bool:
    if not conds:
        return True
    if isinstance(conds, dict):
        conds = [conds]
    return all(check_one(c, state) for c in conds)


def describe_check(conds) -> str:
    """Short tag shown next to a gated dialogue option, e.g. [CHARM ★★★]."""
    if isinstance(conds, dict):
        conds = [conds]
    tags = []
    for c in conds or []:
        if "stat" in c:
            tags.append(f"[{c['stat'].upper()} {'★' * c.get('gte', 1)}]")
    return " ".join(tags)


# ---- effects -------------------------------------------------------------
def apply_effects(effects, state: GameState, content: Content) -> list[tuple]:
    """Apply effects and return UI events: ('log', text) or ('game_over', text)."""
    events: list[tuple] = []
    p = state.player
    for e in effects or []:
        if "set" in e:
            state.flags.add(e["set"])
        elif "unset" in e:
            state.flags.discard(e["unset"])
        elif "give" in e:
            n = e.get("n", 1)
            p.give(e["give"], n)
            name = content.item(e["give"])["name"]
            events.append(("log", f"Received: {name}" + (f" x{n}" if n > 1 else "")))
        elif "take" in e:
            p.take(e["take"], e.get("n", 1))
        elif "cells" in e:
            p.cells += e["cells"]
            events.append(("log", f"{'+' if e['cells'] >= 0 else ''}{e['cells']} cells"))
        elif "xp" in e:
            events += [("log", m) for m in state.add_xp(e["xp"])]
        elif "quest" in e:
            events += set_quest(state, content, e["quest"], e["stage"])
        elif "note" in e:
            title, body = e["note"]
            state.add_note(title, body)
            events.append(("log", f"WristLink: new data — {title}"))
        elif "log" in e:
            events.append(("log", e["log"]))
        elif "signal" in e:
            events += [("log", m) for m in state.add_signal(e["signal"])]
        elif "heal" in e:
            p.hp = min(p.max_hp, p.hp + e["heal"])
        elif "game_over" in e:
            events.append(("game_over", e["game_over"]))
        elif "companion" in e:
            state.companion = e["companion"]
            state.companion_pos = None
            state.flags.add(e["companion"])
        elif "take_entity" in e:
            state.taken.add(e["take_entity"])
        elif "stat_up" in e:
            st_name, n = e["stat_up"], e.get("n", 1)
            before = p.stats[st_name]
            p.stats[st_name] = min(STAT_CAP, before + n)
            p.recalc()
            gained = p.stats[st_name] - before
            events.append(("log", f"{st_name} +{gained} (now {p.stats[st_name]})" if gained
                           else f"{st_name} is already as high as it goes."))
        elif "max_hp" in e:
            p.hp_bonus += e["max_hp"]
            p.recalc()
            p.hp = min(p.max_hp, p.hp + e["max_hp"])
            events.append(("log", f"Max HP +{e['max_hp']} (now {p.max_hp})"))
        else:
            raise ValueError(f"unknown effect {e!r}")
    return events


def set_quest(state: GameState, content: Content, qid: str, stage) -> list[tuple]:
    q = content.quests[qid]
    old = state.quests.get(qid, 0)
    if old == stage or old == "done":
        return []
    if stage != "done" and old != 0 and int(stage) < int(old):
        return []  # quests never move backwards
    state.quests.pop(qid, None)
    state.quests[qid] = stage  # most recently updated quest sits last (shown as active)
    if stage == "done":
        return [("log", f"QUEST COMPLETE: {q['name']}")]
    if old == 0:
        return [("log", f"NEW QUEST: {q['name']}"), ("log", q["stages"][stage])]
    return [("log", f"QUEST UPDATED: {q['name']} — {q['stages'][stage]}")]
