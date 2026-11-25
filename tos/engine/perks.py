"""Perks: bought with perk points (one per level-up), defined in data/perks.yaml.

A perk has `requires` (conditions), optional `mods` (numbers read by the engine) and
optional `effects` (run once when taken). Mod keys and where they're read:

  hit_melee, hit_ranged   +% hit chance          Combat.hit_chance
  dmg_melee, dmg_ranged   +damage per hit        Combat.attack
  crit                    +% critical chance     Combat.attack
  lockon_ap               +/- Lock-On AP cost    Combat.attack_cost
  ap                      +AP per combat turn    Combat.max_ap
  surprise_good           +% good surprises      Combat.roll_surprise
  companion_dmg           +companion damage      Combat.companion_act
  heal_bonus              +HP from aid items     combat.use_aid
  signal_rate_pct         +/- % Signal per step  Location.player_move
  hack_attempts           +attempts              hack.for_terminal
  hack_words              +/- words in the dump  hack.for_terminal
"""
from __future__ import annotations

from .content import Content, apply_effects, check, describe_check
from .state import GameState


def mod(state: GameState, content: Content, key: str) -> float:
    return sum(content.perks.get(pid, {}).get("mods", {}).get(key, 0) for pid in state.player.perks)


def requirement_text(perk: dict) -> str:
    conds = perk.get("requires") or []
    conds = [conds] if isinstance(conds, dict) else conds
    parts = [describe_check([c]) for c in conds if "stat" in c]
    parts += [f"[LEVEL {c['level_gte']}]" for c in conds if "level_gte" in c]
    return " ".join(p for p in parts if p)


def listing(state: GameState, content: Content) -> list[tuple[str, str]]:
    """(perk id, status) for every perk: owned / ready / locked."""
    out = []
    for pid, perk in content.perks.items():
        if pid in state.player.perks:
            out.append((pid, "owned"))
        elif check(perk.get("requires"), state):
            out.append((pid, "ready"))
        else:
            out.append((pid, "locked"))
    return out


def take(state: GameState, content: Content, pid: str) -> tuple[bool, list[tuple]]:
    """Spend a point on a perk. Returns (taken, events)."""
    perk = content.perks.get(pid)
    p = state.player
    if perk is None:
        return False, [("log", "No such perk.")]
    if pid in p.perks:
        return False, [("log", f"You already have {perk['name']}.")]
    if p.perk_points < 1:
        return False, [("log", "No perk points. You earn one each level.")]
    if not check(perk.get("requires"), state):
        return False, [("log", f"{perk['name']} needs {requirement_text(perk)}.")]
    p.perk_points -= 1
    p.perks.append(pid)
    events = [("log", f"PERK: {perk['name']}. {perk['desc']}")]
    return True, events + apply_effects(perk.get("effects"), state, content)
