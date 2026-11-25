# Queen City: Terms of Service

A turn-based terminal RPG in the Fallout 4 mold, set in Charlotte, NC in late 2027, after a polite customer-service AI took over the city.

**Build 0.4 — quests 1 to 4.** About 70–80 minutes of play: *Terms and Conditions* (the tutorial), *Last Mile* (South End → Freedom Park → Plaza Midwood), *Analog Only* (NoDa → the Blue Line) and *Service Interruption* (Central Avenue; mini boss), plus two side quests. Other city stops are on the map but not built yet.

**How to play each level:** `docs/LEVEL_GUIDE.md` (spoilers). **What changed per build:** `docs/CHANGELOG.md`.

The first quest doubles as the tutorial: a 13-step "New Resident Orientation" checklist (walking, using things, searching, the WristLink, equipping, supplies, objectives, talking, hacking, combat, saving, leaving) plus one-time tips for combat, hacking, Signal, low HP, leveling and the city map. Switch it off with `O` on the character screen. Steps and tips live in `tos/data/tutorial.yaml`.

## Run it

Needs Python 3.10+ and a UTF-8 terminal at least **80×24**.

```bash
cd qcts
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m tos
```

Over SSH it's the same: SSH in, then run `python -m tos`. Saves go to `~/.qcts/save.json` (change with `QCTS_SAVE_DIR`).

Or install it as a command: `pip install -e .` then run `qcts`.

## Play over packet radio

`python -m tos.line [CALLSIGN]` runs a plain-ASCII, line-at-a-time version of the game for 1200-baud AX.25 (and anything else that's just a text pipe). An AX.25 node launches it per connection. Saves are per callsign. It needs only PyYAML. Commands are in `docs/LEVEL_GUIDE.md`. Setting it up on a DigiPi node is covered in `deploy/digipi/README.md`.

Try it locally: `python -m tos.line --eol lf`, or over telnet at real packet speed with `socat TCP-LISTEN:7300,reuseaddr,fork EXEC:"python -m tos.line N0CALL --eol crlf --baud 1200"` and `telnet localhost 7300`.

## Controls

| Where | Keys |
| --- | --- |
| Exploring | arrows or `hjkl` move · walk into things to use them · `Tab` WristLink · `s` save · `q` save and quit to title · `?` controls |
| Combat | arrows move (1 AP) · `f` attack · `a` aim (Lock-On, +2 AP, then `1`–`4` pick a part) · `t` next target · `u` drink best heal (2 AP) · `Space` end turn |
| Talking | `1`–`9` or arrows + `Enter` |
| Hacking | type a word from the dump, `Enter`; `Esc` backs out |
| WristLink | `←→` tabs · `↑↓` select · `Enter` use or equip · `Tab`/`Esc` close |

## Layout

| Path | What's in it |
| --- | --- |
| `tos/engine/` | Game logic, no UI: state + saves, content loader and the condition/effect language, grid world, combat, hacking, dialogue |
| `tos/ui/` | Textual screens and rendering |
| `tos/line/` | Line-mode (packet radio) frontend: plain ASCII, no Textual |
| `deploy/digipi/` | Installing line mode on an AX.25 node |
| `tos/data/` | All story content in YAML: locations (ASCII maps), dialogue, items, enemies, quests, surprises, city map |
| `tests/` | `test_engine.py` (logic + scripted playthrough), `test_ui.py` (headless 80×24 UI playthrough), `test_line.py` (line-mode playthrough + airtime report) |

## Writing content

Maps are plain ASCII: `#` wall (drawn with box lines automatically), `.` floor, any other letter is looked up in that location's `legend`. Entity types: `item`, `object`, `npc`, `terminal`, `door`, `enemy`. Dialogue, terminals, doors and objects all use the same small condition/effect language, documented at the top of `tos/engine/content.py`.

## Tests

```bash
python tests/test_engine.py
python tests/test_ui.py            # add --shots DIR to save SVG screenshots
python tests/test_line.py          # line mode; prints reply sizes and airtime
```
