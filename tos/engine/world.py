"""Grid locations: parsing ASCII maps, movement, bump-to-interact, line of sight."""
from __future__ import annotations

from collections import deque

from . import noise, perks
from .content import Content, apply_effects, check
from .state import GameState

WALL, FLOOR, VOID = "#", ".", " "
SOLID_TYPES = {"item", "object", "npc", "terminal", "enemy"}


class Entity:
    def __init__(self, loc: "Location", eid: str, x: int, y: int, data: dict):
        self.loc, self.id, self.x, self.y, self.data = loc, eid, x, y, data
        self.type = data["type"]
        self.key = f"{loc.id}:{eid}"
        self.alive = True
        if self.type == "enemy":
            t = loc.content.enemies[data["enemy"]]
            self.template = t
            self.max_hp = self.hp = t["hp"]
            self.status: dict[str, int] = {}

    @property
    def name(self) -> str:
        if self.type == "enemy":
            return self.data.get("name", self.template["name"])
        return self.data.get("name", self.id)

    def dist(self, x: int, y: int) -> int:
        return max(abs(self.x - x), abs(self.y - y))


class Location:
    def __init__(self, lid: str, state: GameState, content: Content):
        self.id, self.state, self.content = lid, state, content
        d = content.locations[lid]
        self.d = d
        self.name = d["name"]
        self.district = d.get("district", "")
        self.signal_rate = d.get("signal_rate", 0.0)
        legend = d.get("legend", {})
        lines = d["map"].rstrip("\n").split("\n")
        self.h, self.w = len(lines), max(len(l) for l in lines)
        self.terrain: list[list[str]] = []
        self.entities: list[Entity] = []
        for y, line in enumerate(lines):
            row = []
            for x, ch in enumerate(line.ljust(self.w)):
                if ch in (WALL, FLOOR, VOID):
                    row.append(ch)
                elif ch in legend:
                    row.append(FLOOR)
                    spec = legend[ch]
                    ent = Entity(self, spec.get("id", ch), x, y, spec)
                    if ent.key not in state.taken:
                        self.entities.append(ent)
                else:
                    raise ValueError(f"{lid}: unknown map char {ch!r} at {x},{y}")
            self.terrain.append(row)
        self.spawns = {k: tuple(v) for k, v in d.get("spawns", {}).items()}
        self.place_companion()

    # ---- companion ------------------------------------------------------
    def place_companion(self) -> None:
        """Put the companion on the nearest free tile next to the player if it has no spot here."""
        st = self.state
        if not st.companion:
            return
        if st.companion_pos and not self.blocked(*st.companion_pos) and list(st.companion_pos) != st.pos:
            return
        start = tuple(st.pos)
        seen, q = {start}, deque([start])
        while q:
            cur = q.popleft()
            if cur != start and not self.blocked(*cur):
                st.companion_pos = list(cur)
                return
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (cur[0] + dx, cur[1] + dy)
                if nxt not in seen and not self.is_wall(*nxt):
                    seen.add(nxt)
                    q.append(nxt)
        st.companion_pos = list(start)

    # ---- location rules ---------------------------------------------------
    def update_rules(self) -> list[tuple]:
        """Fire each `rules:` entry once, the first time its `if` holds."""
        events: list[tuple] = []
        for rule in self.d.get("rules", []):
            key = f"rule:{self.id}:{rule['id']}"
            if key not in self.state.flags and check(rule.get("if"), self.state):
                self.state.flags.add(key)
                events += apply_effects(rule.get("effects"), self.state, self.content)
        return events

    # ---- queries -------------------------------------------------------
    def live(self, e: Entity) -> bool:
        return e.alive and e.key not in self.state.taken

    def entity_at(self, x: int, y: int) -> Entity | None:
        for e in self.entities:
            if e.x == x and e.y == y and self.live(e):
                return e
        return None

    def get(self, eid: str) -> Entity | None:
        return next((e for e in self.entities if e.id == eid and self.live(e)), None)

    def is_wall(self, x: int, y: int) -> bool:
        return not (0 <= x < self.w and 0 <= y < self.h) or self.terrain[y][x] != FLOOR

    def door_open(self, e: Entity) -> bool:
        return check(e.data.get("open_if"), self.state)

    def enemy_awake(self, e: Entity) -> bool:
        return e.type == "enemy" and self.live(e) and check(e.data.get("wake_if"), self.state)

    def passable(self, e: Entity | None) -> bool:
        if e is None:
            return True
        if e.type == "door":
            return self.door_open(e)
        return e.type not in SOLID_TYPES and e.type != "door"

    def blocked(self, x: int, y: int) -> bool:
        return self.is_wall(x, y) or not self.passable(self.entity_at(x, y))

    def opaque(self, x: int, y: int) -> bool:
        if self.is_wall(x, y):
            return True
        e = self.entity_at(x, y)
        return e is not None and e.type == "door" and not self.door_open(e)

    def los(self, x0: int, y0: int, x1: int, y1: int) -> bool:
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err, x, y = dx + dy, x0, y0
        while (x, y) != (x1, y1):
            if (x, y) != (x0, y0) and self.opaque(x, y):
                return False
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
        return True

    def awake_enemies(self) -> list[Entity]:
        return [e for e in self.entities if self.enemy_awake(e)]

    # ---- player actions -----------------------------------------------
    def player_move(self, dx: int, dy: int) -> list[tuple]:
        px, py = self.state.pos
        nx, ny = px + dx, py + dy
        if self.is_wall(nx, ny):
            return []
        ent = self.entity_at(nx, ny)
        if ent is not None and not self.passable(ent):
            return self.interact(ent)
        old = list(self.state.pos)
        self.state.pos = [nx, ny]
        self.state.steps += 1
        if self.state.companion:
            self.state.companion_pos = old
        events: list[tuple] = []
        if ent is not None and ent.type == "trigger":
            once = f"{ent.key}:entered"
            if once not in self.state.flags and check(ent.data.get("if"), self.state):
                self.state.flags.add(once)
                events += apply_effects(ent.data.get("effects"), self.state, self.content)
        if ent is not None and ent.type == "door" and "to" in ent.data:
            once = f"{ent.key}:entered"
            if once not in self.state.flags:
                self.state.flags.add(once)
                events += apply_effects(ent.data.get("on_enter"), self.state, self.content)
            events.append(("exit", ent.data["to"]))
            return events
        rate = self.signal_rate
        if rate > 0:
            rate *= max(0.0, 1 + perks.mod(self.state, self.content, "signal_rate_pct") / 100)
        events += [("log", m) for m in self.state.add_signal(rate)]
        events += noise.at(self, nx, ny)
        events += self.check_aggro()
        return events

    def check_aggro(self) -> list[tuple]:
        px, py = self.state.pos
        for e in self.awake_enemies():
            if e.dist(px, py) <= e.data.get("aggro", 6) and self.los(e.x, e.y, px, py):
                return [("combat",)]
        return []

    def text_for(self, e: Entity) -> str | None:
        for v in e.data.get("texts", []):
            if check(v.get("if"), self.state):
                return v["text"]
        return e.data.get("text")

    def interact(self, e: Entity) -> list[tuple]:
        st, data = self.state, e.data
        st.flags.add("did:interact")
        events: list[tuple] = []
        text = self.text_for(e)
        if e.type == "item":
            if text:
                events.append(("log", text))
            for spec in data.get("items", [{"id": data.get("item"), "n": data.get("n", 1)}]):
                events += apply_effects([{"give": spec["id"], "n": spec.get("n", 1)}], st, self.content)
            events += apply_effects(data.get("effects"), st, self.content)
            e.alive = False
            st.taken.add(e.key)
        elif e.type == "object":
            if text:
                events.append(("log", text))
            used = f"{e.key}:used"
            if data.get("effects") and used not in st.flags:
                st.flags.add(used)
                events += apply_effects(data["effects"], st, self.content)
        elif e.type == "npc":
            if "dialogue" in data:
                events.append(("dialogue", data["dialogue"]))
            elif text:
                events.append(("log", text))
        elif e.type == "terminal":
            if check(data.get("done_if"), st) and data.get("done_if"):
                events.append(("log", data.get("done_text", "Terminal idle.")))
            else:
                if text:
                    events.append(("log", text))
                events += apply_effects(data.get("on_attempt"), st, self.content)
                events.append(("hack", e.id))
        elif e.type == "door":
            force = data.get("force")
            if force and check(force.get("if"), st):
                events.append(("log", force["text"]))
                events += apply_effects(force.get("effects"), st, self.content)
            else:
                events.append(("log", data.get("locked_text", "Locked.")))
        elif e.type == "enemy":
            if self.enemy_awake(e):
                events.append(("combat",))
            else:
                events.append(("log", data.get("asleep_text", f"{e.name}. Dormant. For now.")))
        events += self.check_aggro() if not any(ev[0] == "combat" for ev in events) else []
        return events

    def terminal_result(self, eid: str, success: bool, hit: dict | None = None) -> list[tuple]:
        if hit:
            return noise.follow(self.state, self.content, hit)
        e = self.get(eid)
        key = "on_success" if success else "on_fail"
        events = apply_effects(e.data.get(key), self.state, self.content) if e else []
        return events + self.check_aggro()

    # ---- pathing for enemies --------------------------------------------
    def step_toward(self, e: Entity, tx: int, ty: int) -> tuple[int, int] | None:
        """BFS one step from e toward any tile adjacent to (tx, ty)."""
        start = (e.x, e.y)
        prev = {start: None}
        q = deque([start])
        goal = None
        while q:
            cur = q.popleft()
            if max(abs(cur[0] - tx), abs(cur[1] - ty)) <= 1 and cur != start:
                goal = cur
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (cur[0] + dx, cur[1] + dy)
                if nxt in prev or (nxt[0], nxt[1]) == (tx, ty):
                    continue
                if self.blocked(*nxt):
                    continue
                prev[nxt] = cur
                q.append(nxt)
        if goal is None:
            return None
        while prev[goal] != start:
            goal = prev[goal]
        return goal
