# Changelog

## 0.8.0 — Chapter two, quest 1: Release Notes (2026-11-25)

**Content**
- **The shore** (`locations/ch2_lake_norman.yaml`, formerly a teaser) is now chapter two's start.
  - *Release Notes* begins on arrival.
  - The radio buoy carries **QA's first message, which depends on your chapter one rating** (one star, three stars, declined, or none on file).
  - The boat *SECOND CHAPTER* is a repair job.
  - A dormant **Rating Drone** (new enemy) wakes when the motor starts.
- **Cornelius Marina** (`locations/ch2_cornelius.yaml`), the chapter two hub:
  - Odette (quest giver), Dewey's shop, Ray (mechanic), a parts crate.
  - The whole marina counts as a workbench.
- New `key` item and recipe: the **Fuel Line Patch** (1 scrap + 1 duct tape; recipe unlocked by Odette's job).
- Quests: *Release Notes* (4 stages + done) and the *Known Issues* hook.
- **Map:**
  - Cornelius is reachable from the shore by road.
  - Every other lake place needs the boat (`has_boat`).
  - Lake travel encounters also need the boat, since they're about boats.
- Recipes whose only requirement is a story flag now say "You don't know what this is for yet."

**Tests**
- Engine: quest 1 from a full chapter-one playthrough, and from a minimal chapter-two save.
- Both check QA's rating-specific greeting.
- The UI and line runs play quest 1 after chapter one (Odette, crate, crafting the patch, the boat, the drone).
- **Balance:** 24 seeds from a minimal level-6 save: 0 deaths, ending at 34–57 of 57 HP.
- **Airtime:** the chapter one→two arrival was 1,085 B. QA's message moved from the arrival onto the buoy, bringing it to 967 B, in line with chapter one's largest scene changes. Mean is unchanged (164 B).

## 0.7.0 — Chapter two systems (2026-11-25)

No new quests. This build adds the systems chapter two (*Quality Assurance*, Lake Norman / McGuire Station) is built on. Every system works in both the Textual UI and line mode, and chapter one plays exactly as before.

**Systems**
- **Regions.** `city.yaml` gains `regions` (each with its own canvas, flavour line and encounter chance), `region:` per node, and gateway nodes (`goto:`).
  - Charlotte's LAKE NORMAN node opens a new Lake Norman map with seven places (placeholders for now) and a road back.
  - Travel rules live in one place, `engine/travel.py`, instead of being duplicated in both frontends.
- **Perks.** One point per level-up and 13 perks in `data/perks.yaml`: two per stat plus a level-6 capstone. `engine/perks.py` applies them to:
  - hit chance, damage, crits and Lock-On cost,
  - AP per turn, surprises and companion damage,
  - healing, Signal per step, and hack attempts and words.
  - Hacks are now built by the engine (`hack.for_terminal`), so both frontends agree.
  - Textual: a PERKS tab (Tab, ←). Line: `PERKS` / `PERK n`.
- **Crafting.** `data/recipes.yaml` has 4 consumables and 4 weapon mods.
  - Only at a workbench (a location tagged `workbench`; Ruth's safehouse for now).
  - Mods are stored per weapon (max 2) and applied through `crafting.weapon_stats`.
  - Junk items drop from machines; Hollis sells sugar and duct tape.
  - Textual: a CRAFT tab (Tab, ← ←). Line: `CRAFT` / `CRAFT n`.
- **Travel encounters.** `data/encounters.yaml` holds text events and ambushes per region.
  - Rolled on trips to a different node: the region's chance plus Signal/400, capped at 0.6.
  - Ambush maps reset every time, and their exit continues the trip (`{city: $dest}`).
  - Every current encounter needs `chapter2`, and an empty pool consumes no randomness.
- **The chapter one rating carries over.** The Crown's choices set `rating_one` / `rating_three` / `rating_declined`.

**Saves**
- `SAVE_VERSION` 3, with `GameState.migrate()`.
- Saves from 0.6 load: older saves get their rating flag inferred, and are back-paid one perk point per level already earned. New fields default sensibly.

**Tests**
- Engine (27 tests): every perk mod, every crafting rule, encounters (forced RNG), gateways, rating flags, migrations, a real v0.6 save.
- New guards: every spawn is walkable (it caught the lakeshore map spawning you in the water), and every map label fits its canvas.
- The UI and line playthroughs each take a perk, craft a mod, travel between regions and hit an encounter.
- All pass on Python 3.11 and 3.14. Line-mode airtime unchanged (mean 163 B per reply).

**Balance**
- Ambushes at post-chapter-one strength (24 seeds, level 6):

| Ambush | Deaths | HP after |
| --- | --- | --- |
| Roadside | 0 | 24–47 of 57 |
| Shoreline | 0 | 40–56 of 57 |

## 0.6.2 — Pre-OTA audit (2026-11-25)

**Fixes**
- **AX.25 writes (launch blocker, found in the loopback lab):** an AX.25 socket refuses any single write larger than the interface MTU, which `kissattach` sets from the axports paclen. The game wrote whole replies at once, got `EMSGSIZE` and exited before its title screen, so every real connection would have dropped instantly. Replies now go out in chunks of at most 128 bytes, halving automatically if the kernel still refuses. Socket errors that aren't hang-ups are logged.
- **Input sanitizing:** player input is reduced to printable ASCII and capped at 80 characters. Hack prompts echo the typed word, so control characters and ESC sequences could previously be sent back over the air.
- **Durable saves:** each save fsyncs the file and its directory, so it survives the Pi losing power.
- **Session cap:** `--max-sessions` / `QCTS_MAX_SESSIONS`, default 3. Extra callers get a polite "full" message.

**Station kit**
- New `deploy/pi-os/`: Raspberry Pi OS + direwolf + kernel AX.25 + ax25d for a Pi 4 / Digirig Mobile / UV-5R. It includes:
  - The direwolf config.
  - axports and ax25d.conf in the lab-proven format.
  - systemd units and the `qcts-on` / `qcts-off` kill switch.
  - `install-station.sh`, which never starts transmitting by itself.
  - A bench-guide README.
- DigiPi is now a radio-check card only. It's built as a read-only appliance, which conflicts with the game's saves.

**Audit (no RF)**

| Check | Result |
| --- | --- |
| Python | All suites pass on 3.11, 3.13 and 3.14 |
| Lint | pyflakes clean |
| Content | No profanity; ASCII-safe; no business names |
| Fuzzing | 60k hostile inputs plus 40 raw-byte streams: 0 failures |
| Load | 5 concurrent players at ~24 MB each |
| Installers | Pass in a clean Debian Bookworm container |

- **AX.25 loopback lab:** two direwolf modems over 1200-baud AFSK with kernel AX.25 and ax25d. Three connected sessions, save/resume, a dropped link keeps progress, and the node passes `%U` = callsign.
- **Measured round trips:** 2.5–4 s for short replies and ~18 s for the largest one-time scene change. `tests/test_line.py`'s `airtime()` is refitted to them.

## 0.6.1 — The Unsubscribe (2026-11-25)
- The Plaza Midwood bar is now **The Unsubscribe**, a fictional name, everywhere in the game and docs: the location name, menu board, city blurb, quest text, and Ruth's and Delia's lines. Delia explains the name.

## 0.6.0 — Quest 6: Rate Your Experience, chapter one finale (2026-11-25)

**Content**
- Two new locations in `locations/act6_rate_your_experience.yaml`: Loading Dock B, and the Crown (the boss arena).
- The safehouse back door now opens after "I'm ready." It's one-way into quest 6.
- **Final boss: the Concierge** (`concierge_avatar`). One heavy ranged hit per turn. It has two `phases`: a Greeter at 66% HP, then two Pickers at 33%. Each wave can be denied ahead of time:
  - Wave 1: hack the wellness desk at the dock, or decline to rate (**Wits ★★★★**).
  - Wave 2: give the three-star written review (**Charm ★★★★**).
- **The rating scene** (`dialogues/act6.yaml`): the Concierge speaks directly, shows Teo on its screens ("fine, very fine, extremely fine"), and asks Rater 4471 for a star rating. Five stars is the bad ending (game over, after a confirmation).
- Teo can be talked to before and after the fight. Freeing him completes *Pending Onboarding*.
- **Ending:** the freight elevator sets `chapter2`, completes the quest, and goes to the chapter two teaser area (`locations/ch2_lake_norman.yaml`). The Lake Norman city node now has a location.
- New `key` item: the Service Badge (opens the elevator to the Crown).

**Tests**
- `test_engine.py`:
  - Quest 6 with both waves, and with both denied.
  - The five-star bad ending (including the "No. Wait." back-out).
  - A guard that every enemy uses exactly one map cell. Two cells sharing an enemy character share one entity id and die together; this happened while building quest 6.
- `test_ui.py`: the headless run now plays all six quests to the chapter two area, denying wave 1 at the desk.
- `test_line.py`: line mode plays all six quests with both waves. 510 replies, mean 161 B.
- **Test bots now heal before attacking** when below 40% HP. Before this, they only checked after spending their AP, so with a 3-AP weapon they never healed. Quest 6 exposed it: the bot died with three Rocket Teas unused. Balance numbers for quests 2–5 were measured with the old bot, so they're conservative.

**Balance**
- Quest 6, 12 seeds per route: no deaths. Both waves: median lowest HP 23 of 62 over 8–13 rounds. Waves denied: median 39 over 5–7.
- Tuned from a first pass that killed the bot 12 times in 12:
  - Concierge HP 90 → 72.
  - One attack per turn (attack cost 3 → 4 AP), damage 3–6 → 4–7.
  - Wave 1 cut from two Greeters to one, and wave 2 changed from two drones to two Pickers.

## 0.5.0 — Quest 5: Scheduled Downtime (2026-11-25)

**Content**
- Two new locations in `locations/act5_scheduled_downtime.yaml`:
  - Third Ward Safehouse: the Opt-Outs' forward base on the Uptown edge. The **Uptown** city node now leads here.
  - Romare Bearden Park.
- A staging level before the quest 6 boss. New dialogue in `dialogues/act5.yaml`:
  - **Doc:** repeatable full heal, plus a one-time permanent +5 max HP.
  - **Priya:** one-time training, +1 to Aim, Wits, Brawn or Grit (can reach 6).
  - **Ruth:** builds Ruth's Nailer.
  - **Hollis:** a shop with Rocket Tea.
  - **Mags:** planning, and the end of the quest.
- Mags's NoDa `blind` node starts quest 5 and moves her to the safehouse.
- New items: Breaker Bar (melee), Ruth's Nailer (ranged, 3 AP), Rocket Tea (heals 25).
- Quests:
  - *Scheduled Downtime* is new.
  - *Pending Onboarding* gets stage 6.
  - The safehouse's back door toward the Crown stays locked until quest 6 is built.

**Engine**
- New effects:
  - `stat_up: <Stat>` (+`n`): permanent, capped at `STAT_CAP` = 6.
  - `max_hp: n`: a permanent bonus that survives level-ups. Stored as `Player.hp_bonus`; older saves load with 0.
- Both are documented in `content.py`.

**Tests**
- `test_engine.py`: the quest 5 playthrough (heal, tonic, training, upgrade, shop, park, ready), plus a test that the new effects cap, survive level-ups, and still load old saves.
- `test_ui.py`: the headless run continues through quest 5.
- `test_line.py`: the line run continues through quest 5. 429 replies, mean 158 B.
- Bot pass through quests 1–5: 0 deaths in 16. Quest 5 ends at full HP every time (Doc).

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
- Three new locations: South End street, Dilworth · Freedom Park, Plaza Midwood · The Unsubscribe.
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
