# Changelog

## 0.4.1 — AX.25 playability audit (2026-11-25)

An audit of line mode at 0.4.0, without radio hardware:
- **Text:** no unmapped non-ASCII in anything the game can send, and no key-specific instructions without a `line:` variant.
- **Playthrough:** quests 1–4 play end to end through line mode.
- **Worst-case combat replies:** every enemy awake, Signal 80. The largest is 410 B (~3.7 s), at the mini boss's death; per-location means are 88–165 B.
- **Maps:** the five new line-mode maps are ~225 B each with no glyph clashes.
- **Python:** the engine and line test suites pass on Python 3.10.22 and 3.11.18 (Docker), not just 3.14.
- **Deploy:** the PyYAML-only deploy layout runs at HEAD without loading Textual.

**Fixes from the audit**
- `content.py` uses libyaml's `CSafeLoader` when PyYAML has it (falls back to `SafeLoader`). Content parse drops from 194 ms to 18 ms, and line-mode startup from 0.29 s to 0.11 s on the dev box. Every packet connection starts a fresh process, so on a Pi this is roughly 1–2 s saved per connect (estimated). The parse result is identical for every content file.
- `deploy/digipi/install.sh` stops with a clear message if `python3` is older than 3.10. Older DigiPi images may ship 3.9.
- The Fulfillment Unit's `on_death` line no longer repeats its death text: ~70 B less on that turn.

## 0.4.0 — Quest 4: Service Interruption (2026-11-25)

**Content**
- Two new locations in `locations/act4_service_interruption.yaml`: Central Avenue (the old car wash, Ruth, a street patrol) and the Relay Yard.
- **Mini boss: the Fulfillment Unit.** It hits once per turn but hard. At half HP it goes into **Overtime** and calls two **Pickers** (new enemy), unless you hacked the yard's **dock controller** first.
- New `key` item: the Thermite Charge. Ruth gives it to you; blowing the relay cabinet uses it.
- Dialogue:
  - Mags has a kickoff option, plus a new `blind` node once the relay is down. That node is where quest 5 will start.
  - Ruth has a new tree, `ruth_relay`, in `dialogues/act4.yaml`. It includes a **Wits ★★★** intel option that explains Overtime.
- Quests:
  - *Service Interruption*: stages 2, 3 and done.
  - *Pending Onboarding*: stage 5.
- City map:
  - Central Ave gets a location. It unlocks at *Service Interruption* stage 2, not on reaching Midwood.
  - Blowing the relay sets `relay_down`, which unlocks the Uptown node. Uptown is not built yet.

**Engine**
- New enemy-entity key, `phases: [{hp_below: 0.5, effects: [...]}]`. Each phase runs once, the first time the enemy is hurt below that fraction of its max HP. Its flag is `<loc>:<id>:phase:<i>`.
  - It's checked after every kind of damage: your attacks, the companion, and surprises.
  - Enemies woken by a phase's flags join the fight in progress.
  - Documented in `content.py` and `Combat.phases`.

**Line mode**
- Fix: `USE TEA` and `USE GUMMY` now work. Item lookup falls back to matching any word in the item name. The low-HP tip already told players to type exactly that, and before this it silently failed.

**Balance**
- Bot passes of 24 seeds per route, quests 1–4. The bot never aims at parts and only heals below 12 HP in combat; between fights it uses foil and heals to 60%.

| Route | Deaths | End-of-quest HP |
| --- | --- | --- |
| Overtime on | 1 in 24 | 12–36 of 52 (mean 24) |
| Overtime denied | 0 in 24 | 6–46 of 52 (mean 30) |

- The first tuning was far too lethal: 6 deaths in 24 with Overtime on, 2 with it denied. Changes to the Fulfillment Unit:
  - HP 72 → 64.
  - Attack cost 3 → 4 AP, so one swing per turn.
  - Damage 3–6 → 5–8.
- Side effect, kept on purpose: a Drive Track (slow) shot leaves it 3 AP, which is below its attack cost. Slowing it stops its attacks for 2 rounds.

**Tests**
- `test_engine.py`: quest 4 with Overtime on, quest 4 with Overtime denied, and a unit test that a phase fires exactly once and wakes the Pickers.
- `test_ui.py`: the headless run continues through quest 4 with Overtime on. A new `heal_up` helper uses the WristLink between fights.
- `test_line.py`: the run continues through quest 4 with Overtime denied (dock controller hack). New test that players can type item nicknames. 331 replies, mean 163 B.

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
