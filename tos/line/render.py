"""Plain-ASCII text for the line frontend: maps, status lines, wrapping."""
from __future__ import annotations

import textwrap

from ..engine.world import FLOOR, WALL, Location

WIDTH = 78  # most packet terminals are 80 columns; leave room for the cursor

TRANSLIT = {
    "✓": "+", "—": "--", "–": "-", "…": "...",
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "·": "-", "→": "->", "←": "<-", "↑": "^", "↓": "v",
    "●": "*", "○": "o", "★": "*", "☆": ".", "▶": ">", "•": "*",
    "¤": "$", "≈": "~", "é": "e", "×": "x",
}

# ASCII map glyphs by entity type, used when the content glyph isn't plain ASCII
TYPE_GLYPH = {"item": "$", "object": "o", "npc": "N", "terminal": "T"}


def asciify(s: str) -> str:
    s = "".join(TRANSLIT.get(ch, ch) for ch in s)
    return s.encode("ascii", "replace").decode("ascii")


def wrap(text: str, indent: str = "") -> list[str]:
    """Wrap each paragraph to WIDTH; keeps blank lines and pre-indented lines as-is."""
    out: list[str] = []
    for para in asciify(text).rstrip().split("\n"):
        if not para.strip():
            out.append("")
        elif para.startswith("  ") or len(para) <= WIDTH:
            out.append(indent + para)
        else:
            out += textwrap.wrap(para, WIDTH, initial_indent=indent, subsequent_indent=indent)
    return out


def glyph(loc: Location, e) -> str:
    if e.type == "enemy":
        return e.template.get("glyph", "E")  # `look` says whether it's awake
    d = e.data
    if e.type == "door":
        if not loc.door_open(e):
            return "+"
        g = d.get("glyph", "/")
        if g.isascii() and g.strip():
            return g
        return ">" if "to" in d else "/"
    g = d.get("glyph", "")
    if len(g) == 1 and g.isascii() and g.strip():
        return g
    return TYPE_GLYPH.get(e.type, "?")


def visible_entities(loc: Location) -> list:
    return [e for e in loc.entities if loc.live(e) and e.type != "trigger"]


def render_map(loc: Location) -> list[str]:
    """One character per tile. About 24x11 tiles, so roughly 300 bytes."""
    px, py = loc.state.pos
    st = loc.state
    comp = tuple(st.companion_pos) if st.companion and st.companion_pos else None
    comp_g = loc.content.companions.get(st.companion, {}).get("glyph", "&") if comp else ""
    rows = []
    for y in range(loc.h):
        row = []
        for x in range(loc.w):
            if (x, y) == (px, py):
                row.append("@")
                continue
            e = loc.entity_at(x, y)
            if e is not None and e.type == "trigger":
                e = None
            if (x, y) == comp and (e is None or e.type == "enemy" and not loc.enemy_awake(e)):
                row.append(comp_g)
            elif e is not None:
                row.append(glyph(loc, e))
            else:
                ch = loc.terrain[y][x]
                row.append("#" if ch == WALL else "." if ch == FLOOR else " ")
        rows.append("".join(row).rstrip())
    return rows


def direction(dx: int, dy: int) -> str:
    parts = []
    if dy:
        parts.append(f"{abs(dy)}{'S' if dy > 0 else 'N'}")
    if dx:
        parts.append(f"{abs(dx)}{'E' if dx > 0 else 'W'}")
    return " ".join(parts) or "here"


def look(loc: Location, limit: int = 8) -> list[str]:
    """Nearby things, nearest first: `Bed o 1N 2W`."""
    px, py = loc.state.pos
    ents = sorted(visible_entities(loc), key=lambda e: (e.dist(px, py), e.y, e.x))
    out = []
    for e in ents[:limit]:
        tag = ""
        if e.type == "enemy":
            tag = " AWAKE" if loc.enemy_awake(e) else " dormant"
        elif e.type == "door" and not loc.door_open(e):
            tag = " locked"
        out.append(f"{asciify(e.name)} {glyph(loc, e)} {direction(e.x - px, e.y - py)}{tag}")
    if len(ents) > limit:
        out.append(f"(+{len(ents) - limit} more; M for map)")
    return out
