# Level Guide — Queen City: Terms of Service

**Spoilers.** This is the cheat sheet: how each level works, where everything is, every stat check, and how to beat each fight. Play first, look here when stuck.

Map coordinates are `(x, y)` from the top-left corner of each map, starting at 0.

---

## Controls (quick reference)

| Where | Keys |
| --- | --- |
| Exploring | arrows / `hjkl` move · walk into things to use them · `Tab` WristLink · `s` save · `q` save + quit · `?` controls |
| Combat | arrows move (1 AP) · `f` attack · `a` aim, then `1`–`4` for a part (+2 AP) · `t` next target · `u` best heal (2 AP) · `Space` end turn |
| Talking | `1`–`9`, or arrows + `Enter` |
| Hacking | type a word from the dump + `Enter` · `Esc` backs out |
| WristLink | `←→` tabs · `↑↓` select · `Enter` use/equip · `Tab`/`Esc` close |

**Map symbols:** `@` you · `b` Biscuit · red letters are enemies (dim = asleep/docked) · `☺` people · `≡` terminal · `¤`/`▤`/`▥`/`▦` things to search · `+` locked door · `/` `▲` `▼` `»` exits.

### Packet radio / line mode (`python -m tos.line`)

Same game and same saves format, but typed commands instead of keys. Saves are per callsign. Everything in this guide applies; only the controls and map symbols differ.

| Where | Commands |
| --- | --- |
| Exploring | `N` `S` `E` `W` move (`N3` = three steps, stops when something happens) · walk into things to use them · `L` what's around you and which way · `M` map · `I` items (`I 2` details) · `USE n`/`EQ n` (number or name: `EQ TIRE`) · `ST` status · `Q` quests + orientation step · `NOTES` (`NOTES 1`) · `SAVE` · `BYE` save + disconnect · `BRIEF`/`VERBOSE` · `?` |
| Combat | `N` `S` `E` `W` move (1 AP) · `F` attack · `A` then `1`–`4`, or `A2` in one go (+2 AP) · `T` next target · `U` best heal (2 AP) · `.` end turn. The prompt shows round, AP, HP, then the target's HP, direction, hit % and AP cost. |
| Talking | reply with the option number |
| Hacking | type a word · `D` reprint the dump · `X` back out |
| City map | the destination's number · `X n` about it |

**Line-mode map symbols:** `@` you · `#` wall · `$` things to search · `o` objects to examine · `N` people · `T` terminal · enemy letters as above · `+` locked door · `/` `>` exits. `L` names everything with its direction from you, e.g. `Closet $ 1N 4E`.

**Airtime:** ordinary replies are 50–250 bytes (1–3 s at 1200 baud). The map (~300 bytes) only appears when you arrive somewhere (off with `BRIEF`) or type `M`. First-time tips and hack dumps are the biggest sends (up to ~900 bytes, ~8 s).

---

## Quest 1 — Terms and Conditions (tutorial)

**Goal:** get out of Unit 1412 and out of The Lumen. **Time:** 10–15 min. **Tutorial:** 13 orientation steps run in the side panel (turn off with `O` on the character screen).

### Unit 1412

```
########################
#b....K#F....O#M.......#     b bed        K closet (tire iron)
#......#......#........#     F fridge (2 sweet tea)
#..P...#......#........#     O junk drawer (tinfoil)
#R.....#......#........#     M mirror     P tablet (Teo's message)
###.#######.#######.####     R rating rig (lore note)
#......................#     S couch      W window
#.S..................c.#     H LUMEN HOME panel (talk)
#......................#     c TIDY-3 (cleaning robot, docked)
#W.........H........T..#     T door terminal (hack)
###################D####     D front door
```

**Fastest route:** tablet (3,3) → closet (6,1) → equip the Tire Iron (WristLink → ITEMS → Enter) → fridge (8,1) and drawer (13,1) → terminal (20,9).

**Opening the door (two ways):**

| Method | Needs | Notes |
| --- | --- | --- |
| Hack the terminal (20,9) | nothing | 5-letter words, 8 in the dump. Attempts: 3, +1 at Wits 3, +1 at Wits 5. A failed hack gives +15 Signal and the terminal reboots, so you can always retry. |
| Pry the door (19,10) | Tire Iron in inventory **and** Brawn 3+ | Walk into the locked door. |

Either way **TIDY-3 wakes up** and the fight starts.

**LUMEN HOME dialogue:**
- *Accept the Terms* → it gives you one chance: pick **CANCEL. CANCEL. CANCEL.** Picking "Okay. Yeah. Okay." is a **game over** (on purpose).
- `[WITS 3]` diagnostic → tells you about the door terminal.
- `[CHARM 3]` Teo → info on Teo + a WristLink note.

**Fight: TIDY-3** — HP 22, melee only, 5 AP, hits for 2–4.
- Equip the Tire Iron first; fists do 1–3.
- Aim (`a`) at **Drive Wheels** to slow it, or **Eye Sensor** to make it miss more.
- You get two Tire Iron swings per turn (3 AP each). Usually done in two turns.

### 14th floor hallway

```
#####A#####U#####B######     A, B neighbor doors (lore)    U back to your unit
#......................#     p Mr. Pruitt (talk)
#..p...................#     d Courier Drone (awake, notices you within 4 tiles)
#...............d......#     G maintenance closet (Nail Gun + 24 nails)
#......................#     E elevator (joke)
####G#########E######X##     X stairwell → outside
```

- **Maintenance closet (4,5):** grab the Nail Gun before the drone fight. It's ranged (6 tiles), so you don't have to chase the drone.
- **Mr. Pruitt:** "No, I didn't accept" → "Where would I even go?" starts *Last Mile*. `[CHARM 2]` lets you lie to him. Asking about Teo updates *Pending Onboarding*.
- **Fight: Courier Drone** — HP 16, ranged 5, evasive. Aim at the **Rotor** to slow it, or just out-shoot it with the Nail Gun.
- **Stairwell (21,5):** completes the quest (+50 XP).

---

## Quest 2 — Last Mile

**Goal:** reach Plaza Midwood. **Time:** ~20 min. **Side quests:** *Your Order Has Shipped*, *Mow Better*.

### South End street (outside The Lumen)

```
####L###################     L back into The Lumen
#......................#     o, O Onboarded people (lore)
#.o.........K..........#     K wellness kiosk (2 med-gummies)
#.....................g#     g Greeter (security bot, asleep until Signal 50)
#TTTTTTTTT.............#     T stalled Lynx train    R robotaxi (joke)
#..........R...........E     b Biscuit, stuck on the curb (talk)
#.....b................#     f emergency blanket (tinfoil)
#..........O.....f.....#     E » to the city map
########################
```

- **Signal rises fast here** (1.2 per step). At **Signal 50 the Greeter wakes up** and comes for you.
  - To sneak past: use Tinfoil (−30) before you walk out, and grab the second one at (17,7).
  - To fight: Greeter has HP 22, taser range 4, hits for 3–5. Aim at **Leg Servos** to slow it. Drops cells, often a med-gummy.
- **Biscuit (6,6):** walk into it. "Push it free" always works. `[WITS 3]` "Reroute its delivery" gives extra XP. Biscuit joins as your companion and starts *Your Order Has Shipped*.
- **Exit (23,5)** → city map → pick **Dilworth**.

**Biscuit in combat:** after each of your turns it rolls up to 3 tiles toward the nearest enemy and rams it (2–4 damage, 70% hit). Enemies never target it.

### Dilworth · Freedom Park

```
########################
#.K.#...!........~~....#     K Kayla R. (talk; both side quests)
#...#...!...1....~~....#     Y yard controller (hack) by her fence
#.......!........~~..2.#     1 2 3 Lawn Units (docked)
#.......!..............E     ~ pond      S shed (18 nails + med-gummy)
#.......!......3.......#     ! the park edge: an invisible tripwire column
#.Y.....!.........S....#     E » east to Plaza Midwood
#.......!..............#
########################
```

**Kayla (2,1):**
- "What's wrong with the park?" starts *Mow Better*.
- With Biscuit along, "Biscuit has a delivery for you" finishes *Your Order Has Shipped* (+40 XP).
- Once the park is clear, "The mowers are handled" pays 25 cells + a sweet tea + XP.

**Getting across the park (two ways):**

| Method | How | Result |
| --- | --- | --- |
| Stealth | Hack the **yard controller (2,6)** before stepping onto the grass. 6-letter words. Failure = +15 Signal, retry allowed. | Mowers stay docked for good. The park counts as cleared. No fight. |
| Fight | Walk past the tripwire column at x=8 | All three Lawn Units wake at once. |

**Fight: 3 Lawn Units** — HP 14 each, melee, one hit per turn for 2–5.
- Back up against the fence or the west wall so only one or two can reach you.
- Let Biscuit soften them. Aim at **Drive Wheels** on the one closest to you.
- Killing all three counts as clearing the park, same as hacking. Then go back to Kayla to get paid.

**Exit (23,4)** walks you straight into Plaza Midwood.

### Plaza Midwood · Moo & Brew

```
########################
#.M...D..#.............#     M menu board     D Delia (bartender; talk)
#.BBBB.BB#...H.........#     B bar (gap at (6,2) to reach Delia)
#........#..s....s.....#     H Hollis (shop)   s stalls
#.p...J..#.............#     p Wade (lore)     J jukebox
#........#.............#     N notice board
####.#####.............#     E » to the city map
#......................E
#..N...................#
########################
```

- **Arriving completes *Last Mile*** (+60 XP). **Signal drops here** (−0.5 per step): this is the safe zone.
- **Delia (6,1):** stand in the bar gap at (6,2) and walk up. "They took my brother Uptown" starts **Analog Only** (quest 3) and updates *Pending Onboarding*.
- **Hollis (13,2) shop:**

| Item | Price (cells) |
| --- | --- |
| Sweet tea (heals 15) | 8 |
| Med-gummy (heals 8) | 5 |
| Nails ×12 | 6 |
| Tinfoil (−30 Signal) | 10 |

- **Next:** NoDa is on the city map but not built yet (quest 3).

---

## Quest 3 — Analog Only

*Not built yet.*
