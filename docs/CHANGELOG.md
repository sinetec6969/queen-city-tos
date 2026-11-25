# Changelog

## 0.3.0 — Quest 3: Analog Only (2026-11-25)

**Content**
- Three new locations in `locations/act3_analog_only.yaml`:
  - NoDa · North Davidson Street: the street, plus the Opt-Outs' brewery behind a door Ruth guards.
  - 36th Street Station.
  - Train 112: two cars and the operator cab.
- City map: NoDa now has a location. The Lynx Blue Line node opens once Mags gives you the job (`analog_only` stage 2), not on reaching Midwood.
- New NPCs, in `dialogues/act3.yaml`: Ruth, Mags, Bev, Dante. Ossie and Priya have line variations once you're trusted.
- New enemies: Track Crawler, Fare Inspector, and the boss PXU-1.
- New item type `key` (the Faraday Pouch). WristLink lists it; it can't be used or equipped.
- *Analog Only* has stages 2, 3 and done. *Pending Onboarding* gets stage 4. *Service Interruption* (quest 4) gets its starting hook.
- Two ways through each lock:
  - Train doors: force them with the tire iron (or Brawn ★★★★), or hack station control.
  - The boss: hack the operator console before taking the pouch and it never wakes.
- Charm ★★★ options with Ruth and with Dante.

**Engine**
- No changes. Everything uses existing mechanics: door `force`, terminals, `wake_if`, rules, dialogue `starts`.

**Balance**
- Bot passes of 24 seeds per route, quests 1–3, with the bot using foil at Signal 40+ and healing to 60% between fights:

| Route | Deaths | End-of-quest HP |
| --- | --- | --- |
| Fight | 0 | 11–34 of 47 (mean 22) |
| Stealth | 0 | 47 of 47 (the level-4 level-up heals) |

- With no between-fight prep, the fight route has 2 deaths in 24.
- Tuned down after the first pass, which had 3 deaths in 24:
  - Fare Inspector: HP 26 → 24, hit 60 → 55, damage 3–6 → 2–5.
  - Track Crawler: hit 50 → 45.
  - Station Signal rate: 0.8 → 0.6.
  - The NoDa library now gives tinfoil.

**Tests**
- `test_engine.py`:
  - `play_act2` is factored out of the quest 2 test.
  - New: quest 3 fight route, quest 3 stealth route, and Ruth's voucher gate.
  - The test bot can now `prep()` between fights.
- `test_ui.py`: the headless run continues through quest 3 on the fight route (Ruth, Mags, platform fight, forced doors, PXU-1, turn-in).
- `test_line.py`: the line-mode run continues through quest 3 on the stealth route (both terminals). Airtime: 237 replies, mean 171 B, p95 462 B.

## 0.2.1 — Line mode for packet radio (2026-11-25)

**Frontend**
- New `tos/line/` frontend: plain ASCII, one line in, one reply out, built for 1200-baud AX.25. Run `python -m tos.line [CALLSIGN]` or `qcts-line`. It imports only the engine and PyYAML, never Textual.
- `Session` (`tos/line/session.py`) mirrors the Textual flow as modes: title, profile, intro, explore, combat/lock-on, dialogue, hack, city, game over. `pump()` is a port of `LocationScreen.pump`; modal screens become modes; tips print inline.
- Commands: `N`/`S`/`E`/`W` with counts (`E5`), `L` look, `M` map, `I`/`USE`/`EQ`/`ST`/`Q`/`NOTES`, `SAVE`, `BYE`, `BRIEF`/`VERBOSE`. Combat: `F`, `A`/`A2`, `T`, `U`, `.`. The prompt carries HP/Signal, or the full combat status. Full table in `docs/LEVEL_GUIDE.md`.
- Built for airtime: the map only on arrival or `M`; a shop purchase sends only the options again; the hack dump drops its address column; `Beside you:` names what you just walked up to.
- Entry point (`tos/line/__main__.py`):
  - Input lines end in CR, LF or CRLF. Output ends lines with CR by default (`--eol crlf` for telnet).
  - Saves per callsign, with the SSID stripped.
  - Optional allowlist (`--allow` / `QCTS_ALLOW`); an unreadable list lets nobody in.
  - One connection per callsign at a time (file lock).
  - Idle timeout, 600 s by default.
  - Saves on EOF, dropped link, SIGHUP/SIGTERM and errors. Tracebacks go to `line-errors.log`, never over the air.
  - `--baud N` throttles output so you can feel the airtime over telnet.
- `deploy/digipi/`: install script (`/opt/qcts`, PyYAML-only venv, `qcts` user, `/var/lib/qcts`, `/etc/qcts/allow`), wrapper, and ax25d/URONode wiring notes. Node config syntax is not yet verified on a DigiPi image.

**Content**
- `tutorial.yaml`: optional `line:` text on steps, tips and `controls`, because `text` names keys and glyphs line mode doesn't have. The Textual UI ignores it.

**Tests**
- New `tests/test_line.py`:
  - Quests 1–2 played entirely through text commands, on the same route as `test_ui.py`.
  - The Accept game-over plus reload; tutorial off; confirmation before a new game replaces a save.
  - Callsign parsing and the allowlist.
  - CLI checks: CR endings and ASCII only, allowlist refusal, SIGHUP saves an unsaved move, broken pipe stays quiet.
- Each run prints reply sizes and an airtime estimate. Current: 154 replies, mean 178 B (~1.8 s), p95 495 B (~4.3 s), max 931 B (~8.1 s, the first combat tip plus the hack result).

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
