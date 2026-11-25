"""Turn-based combat on the location grid: AP, Lock-On aimed shots, surprises."""
from __future__ import annotations

import random

from . import crafting, perks
from .content import apply_effects
from .world import Entity, Location

MAX_AP = 6
LOCK_ON_AP = 2
SURPRISE_CHANCE = 0.15


class Combat:
    def __init__(self, loc: Location, rng: random.Random | None = None):
        self.loc, self.state, self.content = loc, loc.state, loc.content
        self.p = self.state.player
        self.rng = rng or random.Random()
        self.round = 1
        self.max_ap = MAX_AP + int(perks.mod(self.state, self.content, "ap"))
        self.ap = self.max_ap
        self.target_id: str | None = None
        self.outcome: str | None = None  # None | "won" | "lost" | "fled"
        self.retarget()

    # ---- queries -------------------------------------------------------
    def enemies(self) -> list[Entity]:
        px, py = self.state.pos
        return sorted(self.loc.awake_enemies(), key=lambda e: e.dist(px, py))

    def target(self) -> Entity | None:
        es = self.enemies()
        return next((e for e in es if e.id == self.target_id), es[0] if es else None)

    def retarget(self) -> None:
        t = self.target()
        self.target_id = t.id if t else None

    def cycle_target(self) -> None:
        es = self.enemies()
        if not es:
            return
        ids = [e.id for e in es]
        i = ids.index(self.target_id) if self.target_id in ids else -1
        self.target_id = ids[(i + 1) % len(ids)]

    def weapon(self) -> dict:
        return crafting.weapon_stats(self.state, self.content, self.p.weapon)

    def parts(self, e: Entity) -> list[dict]:
        return e.template.get("parts", [])

    def in_range(self, e: Entity) -> bool:
        px, py = self.state.pos
        return e.dist(px, py) <= self.weapon().get("range", 1)

    def hit_chance(self, e: Entity, part: dict | None = None) -> int:
        w, s = self.weapon(), self.p.stats
        px, py = self.state.pos
        d = e.dist(px, py)
        if w.get("melee"):
            base = 60 + 6 * s["Brawn"] + perks.mod(self.state, self.content, "hit_melee")
        else:
            base = 50 + 7 * s["Aim"] - 3 * max(0, d - 2) + perks.mod(self.state, self.content, "hit_ranged")
        base += w.get("acc", 0) - e.template.get("evade", 0)
        if part:
            base += part.get("mod", 0)
        return int(max(5, min(95, base)))

    def attack_cost(self, part: dict | None = None) -> int:
        lock = max(0, LOCK_ON_AP + int(perks.mod(self.state, self.content, "lockon_ap"))) if part else 0
        return self.weapon().get("ap", 3) + lock

    # ---- player actions -----------------------------------------------
    def attack(self, part_id: str | None = None) -> list[str]:
        e = self.target()
        if e is None:
            return ["No target."]
        w = self.weapon()
        part = next((p for p in self.parts(e) if p["id"] == part_id), None) if part_id else None
        cost = self.attack_cost(part)
        if self.ap < cost:
            return [f"Not enough AP ({cost} needed)."]
        if not self.in_range(e):
            return [f"{e.name} is out of range for your {w['name']}."]
        px, py = self.state.pos
        if not self.loc.los(px, py, e.x, e.y):
            return ["No clear line of sight."]
        ammo = w.get("ammo")
        if ammo:
            if not self.p.take(ammo):
                return [f"Out of {self.content.item(ammo)['name'].lower()}."]
        self.ap -= cost
        chance = self.hit_chance(e, part)
        aim = f" at its {part['name'].lower()}" if part else ""
        if self.rng.random() * 100 >= chance:
            return [f"You swing{aim} and miss." if w.get("melee") else f"You fire{aim} and miss."]
        dmg = self.rng.randint(*w["dmg"]) + (self.p.stats["Brawn"] - 1 if w.get("melee") else 0)
        dmg += int(perks.mod(self.state, self.content, "dmg_melee" if w.get("melee") else "dmg_ranged"))
        msgs = []
        if self.rng.random() < 0.03 + 0.02 * self.p.stats["Luck"] + perks.mod(self.state, self.content, "crit") / 100:
            dmg *= 2
            msgs.append("CRITICAL. Five stars.")
        if part:
            fx = part.get("effect")
            if fx == "blind":
                e.status["blind"] = 2
                msgs.append(f"{e.name}'s sensor cracks. It's swinging blind.")
            elif fx == "slow":
                e.status["slow"] = 2
                msgs.append(f"{e.name}'s actuator grinds. Half speed.")
            elif fx == "explode" and self.rng.random() < 0.35:
                dmg += 10
                msgs.append(f"{e.name}'s battery vents in a bright, expensive flash.")
        e.hp -= dmg
        msgs.insert(0, f"You hit {e.name}{aim} for {dmg}.")
        if e.hp <= 0:
            msgs += self.kill(e)
        else:
            msgs += self.phases(e)
        return msgs

    def phases(self, e: Entity) -> list[str]:
        """Entity `phases: [{hp_below: 0.5, effects: [...]}]`: each runs its effects once, the
        first time the enemy is hurt below that fraction of max HP (flag `<loc>:<id>:phase:<i>`).
        Enemies woken by a phase's flags join the fight at once: `enemies()` is live."""
        msgs: list[str] = []
        for i, ph in enumerate(e.data.get("phases", [])):
            key = f"{e.key}:phase:{i}"
            if key not in self.state.flags and e.hp < e.max_hp * ph.get("hp_below", 0.5):
                self.state.flags.add(key)
                msgs += [ev[1] for ev in apply_effects(ph.get("effects"), self.state, self.content) if ev[0] == "log"]
        return msgs

    def kill(self, e: Entity) -> list[str]:
        e.alive = False
        self.state.taken.add(e.key)
        t = e.template
        msgs = [t.get("death", f"{e.name} goes still.")]
        msgs += self.state.add_xp(t.get("xp", 10))
        lo, hi = t.get("cells", [0, 0])
        cells = self.rng.randint(lo, hi)
        if cells:
            self.p.cells += cells
            msgs.append(f"Salvaged {cells} cells.")
        for ev in apply_effects(e.data.get("on_death"), self.state, self.content):
            if ev[0] == "log":
                msgs.append(ev[1])
        for drop in t.get("drops", []):
            if self.rng.random() < drop.get("chance", 1.0):
                self.p.give(drop["id"], drop.get("n", 1))
                msgs.append(f"Salvaged: {self.content.item(drop['id'])['name']}")
        self.retarget()
        self._check_outcome()
        return msgs

    def move(self, dx: int, dy: int) -> list[tuple]:
        if self.ap < 1:
            return [("log", "No AP left. End your turn.")]
        px, py = self.state.pos
        nx, ny = px + dx, py + dy
        ent = self.loc.entity_at(nx, ny)
        if self.loc.is_wall(nx, ny) or not self.loc.passable(ent):
            return [("log", "Something's in the way.")] if ent else []
        self.ap -= 1
        self.state.pos = [nx, ny]
        if ent is not None and ent.type == "door" and "to" in ent.data:
            self.outcome = "fled"
            return [("log", "You break off and run."), ("exit", ent.data["to"])]
        return []

    def use_item(self, iid: str) -> list[str]:
        it = self.content.item(iid)
        if self.ap < 2:
            return ["Using an item costs 2 AP."]
        if it.get("type") != "aid" or not self.p.has(iid):
            return ["You can't use that now."]
        self.ap -= 2
        return use_aid(self.state, self.content, iid)

    def best_heal(self) -> str | None:
        heals = [(self.content.item(i).get("heal", 0), i) for i in self.p.inventory
                 if self.content.item(i).get("heal")]
        return max(heals)[1] if heals else None

    # ---- enemy turn -----------------------------------------------------
    def end_turn(self) -> list[str]:
        msgs: list[str] = self.companion_act()
        self._check_outcome()
        if self.outcome:
            return msgs
        for e in self.enemies():
            if self.p.hp <= 0:
                break
            msgs += self.enemy_act(e)
            for k in list(e.status):
                e.status[k] -= 1
                if e.status[k] <= 0:
                    del e.status[k]
        self._check_outcome()
        if self.outcome:
            return msgs
        self.round += 1
        self.ap = self.max_ap
        msgs += self.roll_surprise()
        self._check_outcome()
        return msgs

    def companion_act(self) -> list[str]:
        """The companion moves up to 3 tiles toward the nearest enemy and rams it.
        Enemies ignore it: the Concierge files it as a registered delivery vehicle."""
        st = self.state
        cid = st.companion
        if not cid or not st.companion_pos:
            return []
        c = self.content.companions.get(cid, {})
        es = self.enemies()
        if not es:
            return []

        class Pos:
            x, y = st.companion_pos
        target = min(es, key=lambda e: e.dist(Pos.x, Pos.y))
        for _ in range(c.get("moves", 3)):
            if target.dist(Pos.x, Pos.y) <= 1:
                break
            step = self.loc.step_toward(Pos, target.x, target.y)
            if step is None or list(step) == st.pos:
                break
            Pos.x, Pos.y = step
        st.companion_pos = [Pos.x, Pos.y]
        name = c.get("name", cid)
        if target.dist(Pos.x, Pos.y) > 1:
            return [f"{name} can't reach anything and beeps about it."]
        if self.rng.random() * 100 >= c.get("hit", 70):
            return [f"{name} rams at {target.name} and misses. \"{self.rng.choice(c.get('barks', ['Beep.']))}\""]
        dmg = self.rng.randint(*c.get("dmg", [2, 4])) + int(perks.mod(self.state, self.content, "companion_dmg"))
        target.hp -= dmg
        msgs = [f"{name} rams {target.name} for {dmg}. \"{self.rng.choice(c.get('barks', ['Beep.']))}\""]
        if target.hp <= 0:
            msgs += self.kill(target)
        else:
            msgs += self.phases(target)
        return msgs

    def enemy_act(self, e: Entity) -> list[str]:
        t = e.template
        if e.status.get("updating"):
            return [f"{e.name}: \"Installing update... {self.rng.randint(4, 97)}%\""]
        ap = t["ap"] // 2 if e.status.get("slow") else t["ap"]
        msgs = []
        while ap > 0 and self.p.hp > 0:
            px, py = self.state.pos
            d = e.dist(px, py)
            if d <= t["range"] and ap >= t["attack_ap"] and self.loc.los(e.x, e.y, px, py):
                ap -= t["attack_ap"]
                chance = t["hit"] - (40 if e.status.get("blind") else 0) + (10 if self.p.signal >= 75 else 0)
                verb = self.rng.choice(t["attacks"])
                if self.rng.random() * 100 < chance:
                    dmg = self.rng.randint(*t["dmg"])
                    self.p.hp = max(0, self.p.hp - dmg)
                    msgs.append(f"{e.name} {verb} — {dmg} damage.")
                else:
                    msgs.append(f"{e.name} {verb} — misses.")
                continue
            if d <= t["range"] and self.loc.los(e.x, e.y, px, py):
                break  # in position, just out of AP
            step = self.loc.step_toward(e, px, py)
            if step is None:
                break
            e.x, e.y = step
            ap -= 1
        if not msgs and self.rng.random() < 0.5 and t.get("barks"):
            msgs.append(f"{e.name}: \"{self.rng.choice(t['barks'])}\"")
        return msgs

    # ---- surprises ------------------------------------------------------
    def roll_surprise(self) -> list[str]:
        if self.rng.random() >= SURPRISE_CHANCE:
            return []
        good = self.rng.random() < 0.3 + 0.1 * self.p.stats["Luck"] + perks.mod(self.state, self.content, "surprise_good") / 100
        pool = [s for s in self.content.surprises
                if s["good"] == good and _requires_ok(s, self.state, self.loc)]
        if not pool:
            return []
        s = self.rng.choice(pool)
        es = self.enemies()
        victim = self.rng.choice(es) if es else None
        text = s["text"].format(enemy=victim.name if victim else "Something",
                                weapon=self.weapon()["name"].lower())
        msgs = [f"SURPRISE! {text}"]
        fx, n = s["effect"], s.get("n", 0)
        if fx == "enemy_update" and victim:
            victim.status["updating"] = 2
        elif fx == "player_ap":
            self.ap = max(0, self.ap + n)
        elif fx == "blind_all":
            for e in es:
                e.status["blind"] = n or 1
        elif fx == "signal":
            msgs += self.state.add_signal(n)
        elif fx == "heal":
            self.p.hp = min(self.p.max_hp, self.p.hp + n)
        elif fx == "enemy_damage" and victim:
            victim.hp -= n
            if victim.hp <= 0:
                msgs += self.kill(victim)
            else:
                msgs += self.phases(victim)
        return msgs

    def _check_outcome(self) -> None:
        if self.p.hp <= 0:
            self.outcome = "lost"
        elif not self.loc.awake_enemies():
            self.outcome = "won"


def _requires_ok(s: dict, state, loc: Location) -> bool:
    if "flag" in s and s["flag"] not in state.flags:
        return False
    if "tag" in s and s["tag"] not in loc.d.get("tags", []):
        return False
    return True


def use_aid(state, content, iid: str) -> list[str]:
    it = content.item(iid)
    p = state.player
    if not p.take(iid):
        return ["You don't have that."]
    msgs = [it.get("use_text", f"You use the {it['name']}.")]
    if it.get("heal"):
        before = p.hp
        p.hp = min(p.max_hp, p.hp + it["heal"] + int(perks.mod(state, content, "heal_bonus")))
        msgs.append(f"+{p.hp - before} HP")
    if it.get("signal"):
        msgs += state.add_signal(it["signal"])
        msgs.append(f"Signal {it['signal']:+d}")
    return msgs
