# Changelog

## 0.2.0 — Quest 2: Last Mile (2026-11-24)

**Content**
- Three new locations: South End street, Dilworth · Freedom Park, Plaza Midwood · Moo & Brew.
- Biscuit joins as a companion. New enemies: Greeter (wakes at Signal 50) and Lawn Unit.
- New NPCs: Kayla R., Delia, Hollis (shop), Wade.
- Side quests *Your Order Has Shipped* and *Mow Better*. Quest 3 (*Analog Only*) gets its starting hook.
- The Lumen stairwell now leads to the South End street instead of straight to the city map. Dilworth and Plaza Midwood can be entered from the city map.

**Engine**
- Companions: follow the player, place themselves next to you when you change areas, take a turn in combat after yours, and are never targeted. Data lives in `data/companions.yaml`.
- `trigger` entity: an invisible tile that runs effects once when stepped on (used for the park ambush).
- Location `rules`: effects that run once, the first time a condition holds (quest completions, arriving somewhere).
- Enemy `on_death` effects.
- New conditions: `any` (OR), `cells_gte`. New effects: `companion`, `take_entity`.
- Dialogue text can show `{cells}`. Shops are built from dialogue options.
- Negative `signal_rate` lowers Signal (Plaza Midwood).
- New tutorial tip: companion.

**Balance**
- Lawn Unit: 4 AP per attack (one hit per turn), 2–5 damage. Across 24 simulated runs of quest 2, no deaths; HP at the end of the quest ranged 25–42 of 42.

**Tests**
- `test_engine.py`: quest 2 playthrough (fight route) and the yard-controller stealth route.
- `test_ui.py`: the headless 80×24 run continues through quest 2 (Biscuit, city travel, Kayla, hack, Delia, shop).

## 0.1.1 — Tutorial (2026-11-24)
- Quest 1 doubles as a 13-step orientation with one-time tips; switch it off with `O` on the character screen; `?` shows controls.

## 0.1.0 — Engine + opening act (2026-11-24)
- Title, character creation, intro, Unit 1412 and the 14th-floor hallway, dialogue, hacking, turn-based combat with aimed shots and surprises, WristLink, save/load, city map.
