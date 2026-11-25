"""Turns game state into Rich Text: the map, bars, the city canvas."""
from __future__ import annotations

from rich.text import Text

from ..engine.combat import Combat
from ..engine.world import WALL, Location

# (north, east, south, west) -> double-line box character
BOX = {
    (0, 0, 0, 0): "■", (1, 0, 0, 0): "║", (0, 0, 1, 0): "║", (1, 0, 1, 0): "║",
    (0, 1, 0, 0): "═", (0, 0, 0, 1): "═", (0, 1, 0, 1): "═",
    (1, 1, 0, 0): "╚", (1, 0, 0, 1): "╝", (0, 1, 1, 0): "╔", (0, 0, 1, 1): "╗",
    (1, 1, 1, 0): "╠", (1, 0, 1, 1): "╣", (0, 1, 1, 1): "╦", (1, 1, 0, 1): "╩", (1, 1, 1, 1): "╬",
}
DEFAULTS = {
    "item": ("¤", "bold cyan"),
    "object": ("▪", "grey70"),
    "npc": ("☺", "bold green"),
    "terminal": ("≡", "bold magenta"),
    "door": ("+", "yellow"),
}
WALL_STYLE = "grey50"
FLOOR_STYLE = "grey27"


def _wallish(loc: Location) -> set[tuple[int, int]]:
    """Entity cells that sit inside a wall line (doors in walls) connect to walls."""
    out = set()
    for e in loc.entities:
        w = lambda x, y: 0 <= x < loc.w and 0 <= y < loc.h and loc.terrain[y][x] == WALL
        if (w(e.x - 1, e.y) and w(e.x + 1, e.y)) or (w(e.x, e.y - 1) and w(e.x, e.y + 1)) \
                or e.y in (0, loc.h - 1) or e.x in (0, loc.w - 1):
            out.add((e.x, e.y))
    return out


def render_map(loc: Location, combat: Combat | None = None) -> Text:
    wallish = _wallish(loc)

    def conn(x: int, y: int) -> bool:
        if not (0 <= x < loc.w and 0 <= y < loc.h):
            return False
        return loc.terrain[y][x] == WALL or (x, y) in wallish

    px, py = loc.state.pos
    target = combat.target() if combat else None
    st = loc.state
    comp = tuple(st.companion_pos) if st.companion and st.companion_pos else None
    comp_glyph = loc.content.companions.get(st.companion, {}).get("glyph", "&") if comp else ""
    t = Text()
    for y in range(loc.h):
        for x in range(loc.w):
            filler = " "
            if conn(x, y) and conn(x + 1, y):
                filler = "═"
            if (x, y) == (px, py):
                t.append("@", style="bold bright_yellow")
                t.append(filler if loc.terrain[y][x] == WALL else " ")
                continue
            e = loc.entity_at(x, y)
            if e is not None and e.type == "trigger":
                e = None
            if (x, y) == comp and (e is None or e.type == "enemy" and not loc.enemy_awake(e)):
                t.append(comp_glyph, style="bold bright_cyan")
                t.append(" ")
                continue
            if e is not None:
                glyph, style = _entity_glyph(loc, e)
                if target is e:
                    style += " reverse"
                t.append(glyph, style=style)
                t.append(filler, style=WALL_STYLE)
                continue
            ch = loc.terrain[y][x]
            if ch == WALL:
                key = (int(conn(x, y - 1)), int(conn(x + 1, y)), int(conn(x, y + 1)), int(conn(x - 1, y)))
                t.append(BOX[key], style=WALL_STYLE)
                t.append(filler, style=WALL_STYLE)
            elif ch == ".":
                t.append("·", style=FLOOR_STYLE)
                t.append(" ")
            else:
                t.append("  ")
        if y < loc.h - 1:
            t.append("\n")
    return t


def _entity_glyph(loc: Location, e) -> tuple[str, str]:
    d = e.data
    if e.type == "enemy":
        g = e.template.get("glyph", "E")
        return g, ("bold red" if loc.enemy_awake(e) else "red dim")
    if e.type == "door":
        if loc.door_open(e):
            return d.get("glyph", "/"), d.get("color", "yellow")
        return d.get("glyph_closed", "+"), "bold yellow"
    g, style = DEFAULTS.get(e.type, ("?", "white"))
    return d.get("glyph", g), d.get("color", style)


def bar(value: float, maximum: float, width: int = 10, style: str = "green") -> Text:
    filled = 0 if maximum <= 0 else round(width * max(0, min(value, maximum)) / maximum)
    t = Text()
    t.append("█" * filled, style=style)
    t.append("░" * (width - filled), style="grey30")
    return t


def stars(n: int, of: int = 5) -> Text:
    t = Text()
    t.append("★" * n, style="bold yellow")
    t.append("☆" * (of - n), style="grey35")
    return t


def render_city(content, state, selected: str, unlocked, region_id: str = "charlotte") -> Text:
    from ..engine import travel
    reg = travel.region(content, region_id)
    w, h = reg["width"], reg["height"]
    grid = [[(" ", "")] * w for _ in range(h)]
    all_nodes = content.city["nodes"]
    nodes = {n: all_nodes[n] for n in travel.region_nodes(content, region_id)}
    for a, b in travel.region_links(content, region_id):
        x0, y0, x1, y1 = nodes[a]["x"], nodes[a]["y"], nodes[b]["x"], nodes[b]["y"]
        steps = max(abs(x1 - x0), abs(y1 - y0))
        for i in range(1, steps):
            x = round(x0 + (x1 - x0) * i / steps)
            y = round(y0 + (y1 - y0) * i / steps)
            grid[y][x] = ("·", "grey35")
    here = state.location.split(":", 1)[1] if state.location.startswith("city:") else None
    for nid, n in nodes.items():
        x, y = n["x"], n["y"]
        if nid == here:
            mark, style = "◉", "bold bright_yellow"
        elif unlocked(nid):
            mark, style = "◆", "bold white" if n.get("location") or n.get("goto") else "white"
        else:
            mark, style = "◇", "grey42"
        if nid == selected:
            style += " reverse"
        grid[y][x] = (mark, style)
        label = " " + n["name"]
        for i, ch in enumerate(label):
            if x + 1 + i < w:
                grid[y][x + 1 + i] = (ch, style.replace(" reverse", "") if ch != " " else "")
    t = Text()
    for y, row in enumerate(grid):
        for ch, style in row:
            t.append(ch, style=style or None)
        if y < h - 1:
            t.append("\n")
    return t
