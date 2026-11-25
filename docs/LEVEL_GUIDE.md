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
| Exploring | `N` `S` `E` `W` move (`N3` = three steps, stops when something happens) · walk into things to use them · `L` what's around you and which way · `M` map · `I` items (`I 2` details) · `USE n`/`EQ n` (number or name: `EQ TIRE`) · `ST` status · `Q` quests + orientation step · `NOTES` (`NOTES 1`) · `PERKS` / `PERK n` · `CRAFT` / `CRAFT n` (at a workbench) · `SAVE` · `BYE` save + disconnect · `BRIEF`/`VERBOSE` · `?` |
| Combat | `N` `S` `E` `W` move (1 AP) · `F` attack · `A` then `1`–`4`, or `A2` in one go (+2 AP) · `T` next target · `U` best heal (2 AP) · `.` end turn. The prompt shows round, AP, HP, then the target's HP, direction, hit % and AP cost. |
| Talking | reply with the option number |
| Hacking | type a word · `D` reprint the dump · `X` back out |
| City map | the destination's number · `X n` about it |

**Line-mode map symbols:** `@` you · `#` wall · `$` things to search · `o` objects to examine · `N` people · `T` terminal · enemy letters as above · `+` locked door · `/` `>` exits. `L` names everything with its direction from you, e.g. `Closet $ 1N 4E`.

**Airtime:** ordinary replies are 50–250 bytes (1–3 s at 1200 baud). The map (~300 bytes) only appears when you arrive somewhere (off with `BRIEF`) or type `M`. First-time tips and hack dumps are the biggest sends (up to ~900 bytes, ~8 s).

---

## Systems (v0.7)

### Perks
You get **one perk point per level-up** (saves from before v0.7 are back-paid one point per level already earned). Spend it in the WristLink: **Tab, then ←** to PERKS. In line mode: `PERKS`, `PERKS ALL`, `PERK n`.

| Perk | Needs | Effect |
| --- | --- | --- |
| Heavy Hands | [BRAWN ★★★] | Melee hits do +2 damage. |
| Follow Through | [BRAWN ★★★★] | +10% melee hit chance. |
| Steady | [AIM ★★★] | +10% ranged hit chance. |
| Quick Lock | [AIM ★★★★] | Lock-On costs 1 AP less. |
| Thick Skin | [GRIT ★★★] | +10 max HP. |
| Off the Grid | [GRIT ★★] | Signal builds 25% slower as you move. |
| Prompt Engineer | [WITS ★★★] | +1 attempt on every hack. |
| Pattern Match | [WITS ★★] | Hack dumps show 2 fewer decoy words. |
| Delivery Partner | [CHARM ★★] | Biscuit hits for +2 damage. |
| Bedside Manner | [CHARM ★★★] | Healing items restore +5 HP. |
| Lucky Break | [LUCK ★★★] | +5% critical hit chance. |
| Happy Accident | [LUCK ★★] | Combat surprises break your way 15% more often. |
| Overclocked | [LEVEL 6] | +1 AP every combat turn. |

### Crafting
You need a **workbench**: a location tagged for one. So far that's **Ruth's bench in the Third Ward safehouse**. WristLink **Tab, ← ←** to CRAFT, or `CRAFT` / `CRAFT n` in line mode.

**Ingredients:**
- Scrap, wire and duct tape drop from machines.
- Both Hollis stalls sell sugar (4 cells) and duct tape (6 cells).

**Mods** go on the equipped weapon: one of each kind, at most 2 per weapon. A modded weapon shows as e.g. "Tire Iron +2".

| Recipe | Ingredients | Result | Needs |
| --- | --- | --- | --- |
| Nails x12 | 2 Scrap | Gives Nails x12 | — |
| Sweet Tea | 2 Sugar | Gives Sweet Tea (gallon) | — |
| Rocket Tea | 1 Sweet Tea (gallon), 1 Sugar | Gives Rocket Tea | — |
| Tinfoil Hat | 1 Tinfoil, 1 Duct Tape | Gives Tinfoil Hat | — |
| Mod: Grip Tape | 2 Duct Tape | Melee weapon: +5% hit. | — |
| Mod: Weighted Head | 3 Scrap, 1 Duct Tape | Melee weapon: +2 damage. | [BRAWN ★★] |
| Mod: Rail Sight | 2 Scrap, 1 Wire | Ranged weapon: +10% hit. | [AIM ★★] |
| Mod: Overcharged Coil | 2 Wire, 2 Scrap | Ranged weapon: +2 damage. | [WITS ★★★] |

### Travel encounters
- Travelling **to a different node** on a map can trigger an encounter. Re-entering the node you're on never does.
- **Chance per trip:** the region's base (Charlotte 15%, Lake Norman 25%) plus Signal ÷ 4 (%), capped at 60%. Tinfoil helps here too.
- Every current encounter needs **chapter two**, so chapter one never rolls.
- **Charlotte:** two text events (one gives sugar and duct tape) and a **wellness-check ambush**: a Greeter and a Courier Drone on the roadside.
- **Lake Norman:** two text events (one lowers Signal, one gives wire and scrap) and a **shoreline ambush**: two Lawn Units.
- Win an ambush and walk out the exit (») to carry on to where you were going.
- Bot balance (24 seeds, level 6, tire iron): roadside 0 deaths, ending at 24–47 of 57 HP; shoreline 0 deaths, ending at 40–56.

### Regions
- The city map now has regions. **LAKE NORMAN** on the Charlotte map opens the Lake Norman map; **CHARLOTTE (I-77)** there brings you back.
- Lake nodes other than THE SHORE are "not built yet". They're chapter two.

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

### Plaza Midwood · The Unsubscribe

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

- **Next:** NoDa opens on the city map once you've reached Midwood (quest 3).

---

## Quest 3 — Analog Only

**Goal:** earn the Opt-Outs' trust by recovering their courier's drive from a stalled train. **Time:** about 20 min. **Route:** city map → **NoDa** → (job) → city map → **Lynx Blue Line** (36th Street) → Train 112 → back to NoDa.

The **Lynx Blue Line** node stays locked until Mags gives you the job.

### NoDa · North Davidson Street

```
########################
#..m...#..FFF......n...#     m murals (lore)        F fermenters (photos)
#......#..........h....#     x little free library (tinfoil + med-gummy)
#..x...#...M...........#     r Ruth, outside the door (talk)
E......D...........t...#     D brewery door (locked until Ruth lets you in)
#.....r#..........c....#     M Mags (talk; quest giver)   h Bev (radios; lore)
#..m...#..bbb..........#     t Ossie (typewriter)   c Priya (camera)
#......#.......k.......#     n photo wall   b tap wall   k darkroom (lore)
########################     E » west to the city map
```

- **Signal falls here** (−0.3 per step), like Midwood.
- **Ruth (6,5):** talk from (6,4). She opens the door if:
  - you've met **Delia** (option "Delia at The Unsubscribe sent me"), or
  - you have **Charm ★★★** ("I declined the Terms ninety-four times...", +25 XP).
  - Otherwise she sends you to find someone to vouch for you. Go talk to Delia.
- **Mags (11,3):** talk from (10,3). "They took my brother..." → "So how do I prove it's a miracle?" sets the job. *Analog Only* moves to stage 2 and the Blue Line node unlocks.
- **Grab the library (3,3)** before you go: the **tinfoil** helps a lot at the station.

### 36th Street Station

```
########################
#..m...#...............#     m route map   C fare machine (lore)
#......=.......1.......#     k maintenance locker (12 nails + sweet tea)
E......................#     = turnstiles: the gap at (7,3) is the way through
#..C...=.........f.....#     1 2 Track Crawlers (awake)   f Fare Inspector (awake)
#......#.....2......K..#     K station control (hack: opens the train)
#...k..#...............#     T Train 112   D train door (12,7)
#......#TTTTDTTTTTTTTTT#     E » west to the city map
########################
```

- **Signal rises here** (+0.6 per step). Foil first if you're above about 40. At 75, enemies get +10 to hit.
- **The platform fight can't be skipped.** Once anything notices you, all three join: 2 Track Crawlers (HP 10, melee, two bites a turn for 1–3) and a Fare Inspector (HP 24, range 4, 2–5).
  - Kill the crawlers first. They're fragile but fast.
  - Then close on the inspector, or shoot it.
  - The turnstile gap is a good choke point.
- **Opening the train (two ways):**

| Method | How |
| --- | --- |
| Force | Walk into the train door (12,7) with the **Tire Iron** equipped (or Brawn ★★★★). +15 XP. |
| Hack | **Station control (20,5)**: 6-letter words. +30 XP. Failure = +15 Signal, retry allowed. |

### Train 112

```
########################
#h.h.o.h.h.h.o.h.h.h.ha#     h seats   o Onboarded riders (lore)   a ad panel
D......................#     D door back to the platform
#h.h.h.h.o.h.h.h.h.o...#     gangway to the second car at (20,4)
####################.###
#h.h.h.o.h.h.h.h..#..K.#     K operator console (hack: PXU-1 goes off shift)
#......................#     S Dante, the courier (talk; has the pouch)
#h.h.h.h.S.h.o.h.P#..L.#     P PXU-1, dormant in the vestibule   L lost and found (tinfoil + med-gummy)
########################
```

- **Dante (9,7):** talk from (9,6). "Mags sent me" → "Can I take the pouch to her?" gives you the **Faraday Pouch** (stage 3).
  - **Charm ★★★** option: "The darkroom. Priya's red light." +25 XP and a note. Lore only; he stays onboarded.
- **Taking the pouch wakes PXU-1**, unless you hacked the console first. It attacks on your next step.

| Route | How | Result |
| --- | --- | --- |
| Stealth | Hack the **operator console (21,5)** *before* talking to Dante: walk the top car to the gangway (20,4), then down. 6-letter words. +35 XP. Failure = +15 Signal, retry allowed. | PXU-1 stays off shift. No boss fight. |
| Fight | Take the pouch first. | Boss fight. |

**Boss: PXU-1** (Passenger Experience Unit): HP 48, range 3, 2 attacks a turn for 3–6. Drops a sweet tea, 10–16 cells, 120 XP.
- Heal to full before you talk to Dante, and grab the lost and found (21,7).
- **Rail Bogies** (slow) halves its AP: one attack a turn instead of two. Do it early.
- **Smile Screen** (blind) is −40 to its hit chance for 2 rounds.
- Biscuit helps.
- Bot runs (24 seeds, a player who heals between fights): no deaths, finishing at 11–34 of 47 HP. Never healing or foiling: 2 deaths in 24.

### Back to Mags

Talk to Mags with the pouch to finish *Analog Only*:
- Rewards: +100 XP and 30 cells.
- *Pending Onboarding* moves to stage 4.
- **Service Interruption** (quest 4) begins: a relay on Central Avenue.
- After this, Ruth, Ossie, Priya, Bev and the photo wall all have new lines.

---

## Quest 4 — Service Interruption

**Goal:** take down the relay on Central Avenue so Uptown goes blind. **Mini boss:** the Fulfillment Unit. **Time:** about 20–25 min. **Route:** NoDa (Mags) → city map → **Central Ave** → relay yard → back to NoDa.

**Starting it:** talk to Mags again after *Analog Only* and pick "Let's take down the relay." That moves the quest to stage 2 and unlocks Central Ave on the city map.

### Central Avenue

```
########################
#.t...........wwwwww...#     t taco truck (sweet tea + med-gummy)
#.............w....w...#     w old car wash   x Ruth's stash, inside the bay (18 nails, tinfoil, sweet tea)
E.............w..x.w...#     r Ruth (talk)
#.................r....G     G relay yard fence (opens after talking to Ruth)
#..........d...........#     d Courier Drone (awake)   g Greeter (wakes at Signal 50)
#......g...............#     c bus shelter, s pile of wristbands (lore)
#..c......s............#     E » west to the city map
########################
```

- **Signal rises** here (+0.8 per step). The drone notices you within 5 tiles. The Greeter joins if you're at Signal 50 or more. Foil before coming if you can.
- **Ruth (18,4):** talk from (17,4).
  - "What's the plan?" → "Cut it." cuts the fence and gives you the **Thermite Charge**.
  - **Wits ★★★** option ("The drive mentioned the yard"): +25 XP and a note explaining the yard's overtime mechanic and the dock controller.
- **Ruth's stash (17,3):** walk up from where you talked to her. Take it before going in.

### Relay Yard (mini boss)

```
########################
#..........RRR.........#     R relay tower   C relay cabinet (12,2)
#..........RCR.........#     U Fulfillment Unit (12,3), parked in front of the cabinet
#...........U..........#     1 2 Pickers, docked (wake in Overtime)
G......................#     K dock controller (3,7): hack to deny Overtime
#..1................2..#     x undelivered parcels (2 med-gummies)
#.....##........##.....#     ## pallet stacks (block line of sight)
#..K...............x...#     G gate back to Central Ave
########################
```

- **Signal rises fast** here (+1.0 per step).
- The Fulfillment Unit notices you within 6 tiles with line of sight. The west side is safe: you can reach the dock controller from (2,7) without starting the fight.

**Before the fight (optional but strong):** hack the **dock controller (3,7)**. 6-letter words. +35 XP. Failure = +15 Signal, retry allowed. Overtime is then denied and the Pickers never activate.

**Fulfillment Unit:**

| Stat | Value |
| --- | --- |
| HP | 64 |
| Reach | 2 tiles |
| Attack | One heavy swing per turn: 5–8 damage, 60% to hit |
| Evade | None. It's huge. |
| Drops | Sweet tea, 15–25 cells, 180 XP |

- **Overtime:** the first time it drops below half HP (32), it calls the two **Pickers**, unless you hacked the dock controller. Pickers: HP 9, melee, two grabs a turn for 1–3.
- **The trick:** aim at the **Drive Track** (Lock-On, part 2). Slowed, it only has 3 AP, which is less than its swing costs, so **it can't attack at all for 2 rounds**. Do it on round 1, and again when it wears off.
- **Optical Mast** (blind) is −40 to its hit chance for 2 rounds. Good if you can't land the track shot.
- Pallet stacks block line of sight: break away behind one to heal.
- Bot runs (24 seeds; the bot never aims at parts and only heals below 12 HP):

| Route | Deaths | End HP |
| --- | --- | --- |
| Overtime on | 1 in 24 | 12–36 of 52 |
| Overtime denied | 0 in 24 | 6–46 of 52 |

**Blowing the relay:** with the Unit down, stand where it stood (12,3) and walk into the **cabinet (12,2)**. The thermite does the rest:
- *Service Interruption* is complete. +80 XP.
- *Pending Onboarding* moves to stage 5.
- The **Uptown** node unlocks on the city map. It's still "not built yet": that's quest 5.

**Afterwards:** Ruth on Central Avenue and Mags in NoDa both have new lines. Mags is where quest 5 starts.

---

## Quest 5 — Scheduled Downtime

**Goal:** get ready for the tower. This is a staging level: heal, upgrade, scout. **Time:** about 15 min. **Route:** NoDa (Mags) → city map → **Uptown** (Third Ward safehouse) → Romare Bearden Park → back to the safehouse.

**Starting it:** talk to Mags in NoDa after the relay is down and pick "Where do we go in from?" Mags leaves NoDa for the safehouse, and **Uptown** on the city map takes you there.

### Third Ward Safehouse

```
################X#######
#......#..M.........R..#     M Mags (planning; ends the quest)   R Ruth (gear)
#..k...#....ttt.....w..#     k Concierge kiosk (hack; flavour only)   t planning table   w workbench
E......D...............#     D print shop door (open)   E » west to the city map
#..h...#...........p...#     h Hollis (shop, on the sidewalk)   p Priya (training)
#......#..C...nnn......#     C Doc (healing)   n cots
#......#####.###########     X back door toward the Crown: locked (quest 6 isn't built yet)
#......................P     P » east to Romare Bearden Park
########################
```

- **Signal falls here** (−0.4 per step).
- **Doc (10,5), from (10,4):**
  - "Patch me up": full heal. **Repeatable, free.**
  - "Got anything stronger?": **+5 max HP, permanently.** One time.
- **Priya (19,4), from (18,4):** one lesson, **+1 to one stat, permanently**. Pick one: Aim (steady hands), Wits (listening), Brawn (lifting), or Grit (breathing; also raises max HP). Training can take a stat to 6.
- **Ruth (20,1), from (19,1):** **Ruth's Nailer**: ranged, range 6, 3 AP per shot (the stock nail gun is 4), 5–8 damage, +10 accuracy, uses nails.
  - Free if you hand over your nail gun.
  - 25 cells if you never found one.
- **Hollis (3,4), from (3,3):**

| Item | Price (cells) |
| --- | --- |
| Rocket Tea (heals 25) | 14 |
| Sweet tea | 8 |
| Med-gummy | 5 |
| Nails ×12 | 6 |
| Tinfoil | 10 |

### Romare Bearden Park

```
########################
#.~~~~.......c.........#     ~ waterfall wall   c groundskeeper's cart (Breaker Bar)
#..........b....g......#     b bench   g Greeter (asleep unless Signal 50+)
W.........ooo.........S#     o folding chairs   S onboarding shuttle (12,3 → 22,3)
#..L.......o...........#     L parcel lockers (hack)
#...........o.......d..#     d Courier Drone (awake)
#......f...............#     f hot dog cart (sweet tea + 2 med-gummies)
#...............T......#     T ballpark gate (lore)   W « back to the safehouse
########################
```

- **Breaker Bar** in the cart (13,1), from (13,2): melee, 6–9 damage, +5 accuracy. The best close-range weapon so far.
- **Parcel lockers (3,4),** from (2,4): 6-letter hack. +24 nails, a Rocket Tea, 20 cells, 35 XP. Failure = +15 Signal, retry allowed.
- **Fights are light:** one drone, plus the Greeter only if your Signal is high.
- **The shuttle (22,3),** from (21,3): reading its route card advances the quest (stage 3) and *Pending Onboarding* (stage 6).

**Finishing:** go back to **Mags (10,1)** and say "I'm ready." That completes *Scheduled Downtime* and opens the safehouse's back door (16,0). That door is quest 6, and there is no way back from it: heal and stock up first.

**Recommended loadout for quest 6:**
- Full HP after Doc, and the tonic taken.
- Ruth's Nailer with 30+ nails, or the Breaker Bar.
- Two or more Rocket Teas, and some tinfoil.

Bot runs through quests 1–5 (16 seeds): no deaths, and everyone finishes quest 5 at full HP.

---

## Quest 6 — Rate Your Experience (chapter one finale)

**Goal:** get to the top of the Bank of America Corporate Center, face the Concierge, free Teo. **Final boss:** the Concierge. **Time:** about 15–20 min. **Route:** safehouse back door → Loading Dock B → the Crown → (chapter two).

**No retreat:** once you walk through the safehouse back door, you can't return to the city until it's over. The elevator to the Crown only goes up. Arrive healed and stocked.

### Loading Dock B

```
########################
#SSSS..#....o.o.o......#     S the shuttle you arrived on   o new residents (lore)
#......#...............#     D dock door (open)
#......D.........g.....#     g h two Greeters (awake, notice you within 5)
#......#...............E     b dock office locker (3,5): SERVICE BADGE + Rocket Tea + 12 nails
#..b...#..k........h...#     k wellness desk (10,5): hack to deny the boss's first wave
#......#...............#     E service elevator (23,4): needs the badge
########################
```

- **Get the badge** from the dock office (3,5), from (3,4). The elevator won't open without it.
- **Wellness desk (10,5),** from (10,4): 6-letter hack. +40 XP. Failure = +15 Signal, retry allowed. Success means the Greeter in the Crown **never wakes**.
- The two Greeters here are awake. Fight them on the west side of the dock door so they come to you one at a time.

### The Crown

```
########################
#oo.......SSSS.......oo#     S the Concierge's screens (talk)   o onboarded residents
#o..........C.........o#     C the Concierge (avatar; dormant until you rate it)
#....##..........##....X     ## pillars (block line of sight)
#......................#     T Teo (talk)
#.g.......T............#     g Greeter: wave 1
#....##..........##....#     d q Pickers: wave 2
#.d..................q.#     X freight elevator (23,3): opens when the Concierge is down
#......................#     e the elevator you came up in (one-way)
###########e############
```

**Teo (10,5)**, from (10,4): talk to him before the fight if you want to see what onboarding did to him.

**The screens (10–13,1)**, from (11,2): the Concierge talks. "Where's Teo?" shows him on the screens, then it asks you to **rate your experience**:

| Rating | Needs | Result |
| --- | --- | --- |
| ★★★★★ | — | **Bad ending (game over),** after one confirmation. "No. Wait." backs out. |
| ★ "Too eager to please..." | — | The fight starts. Both reinforcement waves will come. |
| ★★★ detailed review | **Charm ★★★★** | The fight starts. **Wave 2 (the Pickers) never comes.** |
| Decline to rate | **Wits ★★★★** | The fight starts. **Wave 1 (the Greeter) never comes.** |
| Not yet | — | Leave and come back. |

The Charm and Wits options are where Priya's training in quest 5 pays off.

**Boss: the Concierge**

| Stat | Value |
| --- | --- |
| HP | 72 |
| Range | 4 |
| Attack | One heavy hit per turn: 4–7 damage, 60% to hit |
| Rewards | 300 XP and 30–40 cells (the XP levels you up, which heals you) |

- **Wave 1, below 66% HP:** a Greeter joins, unless you hacked the wellness desk or declined to rate.
- **Wave 2, below 33% HP:** two Pickers drop from the ceiling, unless you gave the three-star review.
- **The trick:** Lock-On its **Uplink Spine** (slow). Slowed, it has 3 AP, which is less than its attack costs, so it can't hit you for 2 rounds. **Face Light** (blind) is −40 to its hit chance.
- The pillars block line of sight, so break away behind one to drink a Rocket Tea.
- Bot runs (12 seeds, quests 1–5 played first; the bot heals below 40% HP and never aims at parts):

| Route | Deaths | Lowest HP during the fight | Rounds |
| --- | --- | --- | --- |
| Both waves | 0 in 12 | median 23 of 62 (lowest 14) | 8–13 |
| Both waves denied | 0 in 12 | median 39 of 62 | 5–7 |

**After the fight:**
- Talk to **Teo** again (*Pending Onboarding* complete, +100 XP).
- The **freight elevator (23,3)** opens. Taking it completes *Rate Your Experience* and ends chapter one. It leads to the chapter two teaser area, and Lake Norman unlocks on the city map.

