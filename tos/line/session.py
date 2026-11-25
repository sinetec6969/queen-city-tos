"""One player's line-mode game: a mode state machine around the engine.

`Session.handle(line)` takes one line of input and returns the whole reply as a
string ending in a prompt. It mirrors the Textual flow in `tos/ui/screens.py`
(LocationScreen.pump and the modal screens), with modals turned into modes:

  title -> profile -> intro -> explore <-> combat/lockon, dialogue, hack, city -> gameover
"""
from __future__ import annotations

import random
import re
from collections import deque

from ..engine import tutorial
from ..engine.combat import MAX_AP, Combat, use_aid
from ..engine.content import Content, check
from ..engine.dialogue import Dialogue
from ..engine.game import follow_exit, new_game, place
from ..engine.hack import Hack, attempts_for
from ..engine.state import STAT_BLURBS, STAT_BUDGET, STAT_MAX, STAT_MIN, STATS, has_save, load_game, save_game
from ..engine.world import Location
from . import render as R

DIRS = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0)}
MOVE_RE = re.compile(r"([nsew])\s*(\d{0,2})")
DEFAULT_STATS = {"Brawn": 3, "Grit": 3, "Aim": 3, "Wits": 2, "Charm": 2, "Luck": 2}
MAX_REPEAT = 12


class Session:
    def __init__(self, content: Content, rng: random.Random | None = None, slot: str = "save",
                 brief: bool = False):
        self.c = content
        self.rng = rng or random.Random()
        self.slot = slot
        self.brief = brief
        self.state = None
        self.loc: Location | None = None
        self.combat: Combat | None = None
        self.dlg: Dialogue | None = None
        self.hack: Hack | None = None
        self.hack_eid: str | None = None
        self.queue: deque = deque()
        self.out: list[str] = []
        self.mode = "title"
        self.stats = dict(DEFAULT_STATS)
        self.tut = True
        self.page = 0
        self.start_events: list = []
        self.confirm_new = False
        self.go_text = ""
        self.last_beside: tuple = ()
        self.done = False
        nodes = content.city["nodes"]
        self.city_order = sorted(nodes, key=lambda n: (nodes[n]["y"], nodes[n]["x"]))

    # ---- output -----------------------------------------------------------
    def say(self, text: str, log: bool = True) -> None:
        if log and self.state is not None:
            self.state.say(text)
        self.out += R.wrap(text)

    def lines(self, ls) -> None:
        self.out += [R.asciify(l) for l in ls]

    def flush(self) -> str:
        self.out.append(self.prompt())
        text = "\n".join(self.out)
        self.out = []
        return text

    def start(self) -> str:
        self.show_title()
        return self.flush()

    def handle(self, line: str) -> str:
        getattr(self, f"in_{self.mode}")(line.strip())
        return self.flush()

    def save(self) -> None:
        """Autosave on disconnect or idle timeout."""
        if self.state is not None and self.mode not in ("title", "profile", "gameover"):
            save_game(self.state, self.slot)

    def prompt(self) -> str:
        m = self.mode
        if self.done:
            return ""
        if m in ("explore", "city"):
            p = self.state.player
            return f"HP{p.hp}/{p.max_hp} SIG{int(p.signal)}" + (" go#>" if m == "city" else ">")
        if m in ("combat", "lockon"):
            return self.combat_status() + (" part#/x>" if m == "lockon" else ">")
        if m == "dialogue":
            return f"1-{len(self.dlg.options())}>"
        if m == "hack":
            return f"word ({self.hack.attempts} left)>"
        if m == "intro":
            return "Enter=next X=skip>"
        return ">"

    # ---- title / profile / intro -------------------------------------------
    def show_title(self) -> None:
        self.mode = "title"
        self.lines(["QUEEN CITY: TERMS OF SERVICE", self.c.text["tagline"], "Charlotte, NC - late 2027", ""])
        opts = (["C continue"] if has_save(self.slot) else []) + ["N new game", "Q quit"]
        self.lines(["   ".join(opts)])

    def in_title(self, cmd: str) -> None:
        k = cmd.lower()
        if k == "c" and has_save(self.slot):
            self.resume()
        elif k == "n" or (k == "new" and self.confirm_new):
            self.want_new(k == "new")
        elif k in ("q", "bye", "quit"):
            self.quit()
        else:
            self.show_title()

    def want_new(self, confirmed: bool = False) -> None:
        if has_save(self.slot) and not confirmed:
            self.confirm_new = True
            self.lines(["A new game replaces your saved game. Type NEW to confirm."])
            return
        self.confirm_new = False
        self.stats = dict(DEFAULT_STATS)
        self.tut = True
        self.mode = "profile"
        self.show_profile()

    def stars_left(self) -> int:
        return STAT_BUDGET - sum(self.stats.values())

    def show_profile(self) -> None:
        self.lines([f"RATING PROFILE - DEZ HARLAN ({STAT_BUDGET} stars, {STAT_MIN}-{STAT_MAX} each)"])
        self.lines([f" {s:<6}{self.stats[s]}  {STAT_BLURBS[s]}" for s in STATS])
        self.lines([f"Tutorial: {'ON' if self.tut else 'OFF'}. "
                    "Type 6 numbers in that order (e.g. 3 3 3 2 2 2), O = tutorial on/off, OK = start."])

    def in_profile(self, cmd: str) -> None:
        k = cmd.lower()
        if k == "ok":
            self.begin()
        elif k == "o":
            self.tut = not self.tut
            self.lines([f"Tutorial {'ON' if self.tut else 'OFF'}."])
        elif k in ("x", "back"):
            self.show_title()
        elif re.fullmatch(r"[\d\s,]+", k or "x"):
            vals = [int(v) for v in re.findall(r"\d", k)]
            if len(vals) == len(STATS) and all(STAT_MIN <= v <= STAT_MAX for v in vals) and sum(vals) == STAT_BUDGET:
                self.stats = dict(zip(STATS, vals))
                self.show_profile()
            else:
                self.lines([f"Need {len(STATS)} numbers, {STAT_MIN}-{STAT_MAX} each, totaling {STAT_BUDGET}."])
        else:
            self.show_profile()

    def begin(self) -> None:
        self.state, self.start_events = new_game(self.c, self.stats, self.tut)
        self.page = 0
        self.mode = "intro"
        self.show_intro()

    def show_intro(self) -> None:
        pages = self.c.text["intro"]
        self.say(pages[self.page], log=False)
        self.lines([f"[{self.page + 1}/{len(pages)}]"])

    def in_intro(self, cmd: str) -> None:
        self.page += 1
        if cmd.lower() in ("x", "skip") or self.page >= len(self.c.text["intro"]):
            save_game(self.state, self.slot)  # a death always has a save to load
            self.enter_world(self.start_events)
        else:
            self.show_intro()

    def resume(self) -> None:
        st = load_game(self.slot)
        if st is None:
            self.lines(["No readable save found."])
            self.show_title()
            return
        self.state = st
        self.lines(["Session restored."])
        self.enter_world()

    def quit(self) -> None:
        self.save()
        self.done = True
        self.lines(["Saved. 73." if self.state is not None else "73."])

    # ---- world -------------------------------------------------------------
    def back_mode(self) -> str:
        return "combat" if self.combat else "explore"

    def enter_world(self, events=()) -> None:
        if self.state.location.startswith("city:"):
            self.enter_city()
            return
        self.load_location()
        self.queue.extend(events)
        self.pump()

    def load_location(self) -> None:
        self.loc = Location(self.state.location, self.state, self.c)
        self.combat = None
        self.mode = "explore"
        self.last_beside = ()
        self.lines([f"== {self.loc.district} - {self.loc.name} =="])
        if self.brief:
            self.lines(R.look(self.loc))
        else:
            self.show_map(header=False)

    def show_map(self, header: bool = True) -> None:
        self.loc.place_companion()
        if header:
            self.lines([f"== {self.loc.name} =="])
        self.lines(R.render_map(self.loc))
        if header:
            self.lines(["@ you  # wall  + locked  > exit  L = what's what"])

    def pump(self) -> None:
        """Port of LocationScreen.pump: modal events switch mode and pause the queue."""
        while self.mode in ("explore", "combat", "lockon"):
            if not self.queue:
                self.queue.extend(self.loc.update_rules())
                self.queue.extend(tutorial.update(self.state, self.c))
                if not self.queue:
                    break
            ev = self.queue.popleft()
            kind = ev[0]
            if kind == "log":
                self.say(ev[1])
            elif kind == "tutorial_step":
                s = tutorial.steps(self.c)[ev[1] - 1]
                self.say(f"ORIENTATION {ev[1]}: {s.get('line', s['text'])}")
            elif kind == "tip":
                self.show_tip(ev[1])
            elif kind == "dialogue":
                self.open_dialogue(ev[1])
                return
            elif kind == "hack":
                if tutorial.take_tip(self.state, "hack"):
                    self.show_tip("hack")
                self.open_hack(ev[1])
                return
            elif kind == "combat":
                if not self.combat:
                    self.start_combat()
            elif kind == "exit":
                self.queue.clear()
                self.do_exit(ev[1])
                return
            elif kind == "game_over":
                self.queue.clear()
                self.game_over(ev[1])
                return

    def resume_after_modal(self, events) -> None:
        self.mode = self.back_mode()
        self.queue.extendleft(reversed(events or []))
        self.pump()

    def do_exit(self, to: dict) -> None:
        self.combat = None
        kind = follow_exit(self.state, self.c, to)
        save_game(self.state, self.slot)
        if kind == "city":
            self.enter_city()
        else:
            self.load_location()
            self.queue.extend(self.loc.check_aggro())
            self.pump()

    def game_over(self, text: str) -> None:
        self.mode = "gameover"
        self.combat = None
        self.go_text = text
        self.lines(["SESSION EXPIRED"])
        self.say(text, log=False)
        self.lines(["Thank you for choosing calm.",
                    ("L load last save   " if has_save(self.slot) else "") + "N new game   Q quit"])

    def in_gameover(self, cmd: str) -> None:
        k = cmd.lower()
        if k == "l" and has_save(self.slot):
            self.resume()
        elif k == "n" or (k == "new" and self.confirm_new):
            self.state = None
            self.want_new(k == "new")
        elif k in ("q", "bye", "quit"):
            self.state = None
            self.quit()
        else:
            self.game_over(self.go_text)

    def show_tip(self, tid: str) -> None:
        tut = self.c.tutorial
        tip = tut["controls"] if tid == "controls" else tut["tips"][tid]
        self.lines([f"-- {tip['title']} --"])
        self.say(tip.get("line", tip["text"]), log=False)

    # ---- explore -----------------------------------------------------------
    def in_explore(self, cmd: str) -> None:
        if not cmd:
            return
        verb, _, arg = cmd.lower().partition(" ")
        arg = arg.strip()
        m = MOVE_RE.fullmatch(cmd.lower())
        if m:
            self.walk(m.group(1), int(m.group(2) or 1))
        elif verb in ("l", "look"):
            self.lines(R.look(self.loc))
        elif verb in ("m", "map"):
            self.show_map()
        elif self.common(verb, arg):
            if self.mode == "explore":
                self.pump()
        else:
            self.lines(["Huh? ? for help."])

    def walk(self, d: str, n: int) -> None:
        dx, dy = DIRS[d]
        for i in range(max(1, min(n, MAX_REPEAT))):
            before = list(self.state.pos)
            events = self.loc.player_move(dx, dy)
            moved = self.state.pos != before
            self.queue.extend(events)
            if events or not moved:
                if not events and i == 0:
                    self.lines(["Can't go that way."])
                break
        had_output = bool(self.out)
        self.pump()
        if self.mode == "explore" and not had_output and not self.out:
            self.report_beside()

    def report_beside(self) -> None:
        """After a quiet move, name anything you're now next to (orthogonally)."""
        px, py = self.state.pos
        beside = []
        for e in R.visible_entities(self.loc):
            if abs(e.x - px) + abs(e.y - py) == 1:
                beside.append(f"{R.asciify(e.name)} {R.direction(e.x - px, e.y - py)}")
        key = tuple(beside)
        if beside and key != self.last_beside:
            self.lines(["Beside you: " + ", ".join(beside)])
        self.last_beside = key

    # ---- commands shared by explore and the city map ------------------------
    def common(self, verb: str, arg: str) -> bool:
        st = self.state
        if verb in ("i", "inv"):
            st.flags.add("did:wristlink")
            if arg:
                self.describe_item(arg)
            else:
                self.show_inventory()
        elif verb in ("use", "eq", "equip", "u"):
            st.flags.add("did:wristlink")
            self.use_item(arg)
        elif verb in ("st", "stat", "stats"):
            st.flags.add("did:wristlink")
            self.show_stats()
        elif verb in ("q", "quests"):
            st.flags.update({"did:wristlink", "did:quests_tab"})
            self.show_quests()
        elif verb in ("notes", "data"):
            st.flags.add("did:wristlink")
            self.show_notes(arg)
        elif verb == "save":
            st.flags.add("did:saved")
            save_game(st, self.slot)
            self.lines(["Saved."])
        elif verb in ("bye", "quit", "exit"):
            self.quit()
        elif verb in ("?", "h", "help"):
            self.show_tip("controls")
        elif verb in ("brief", "verbose"):
            self.brief = verb == "brief"
            self.lines([f"{verb.title()} mode: map on arrival {'off' if self.brief else 'on'}."])
        else:
            return False
        return True

    def items(self) -> list[str]:
        inv = self.state.player.inventory
        return sorted(inv, key=lambda i: (self.c.item(i).get("type", ""), i))

    def find_item(self, arg: str) -> str | None:
        items = self.items()
        if arg.isdigit():
            i = int(arg) - 1
            return items[i] if 0 <= i < len(items) else None
        arg = arg.lower()
        for iid in items:  # id or name prefix first ("med", "sweet tea"), then any word ("tea", "gummy")
            if iid.startswith(arg.replace(" ", "_")) or self.c.item(iid)["name"].lower().startswith(arg):
                return iid
        for iid in items:
            words = re.split(r"[^a-z0-9]+", self.c.item(iid)["name"].lower())
            if any(w.startswith(arg) for w in words if w):
                return iid
        return None

    def show_inventory(self) -> None:
        p = self.state.player
        items = self.items()
        if not items:
            self.lines(["Nothing. Not even lint."])
            return
        out = []
        for i, iid in enumerate(items, 1):
            eq = "*" if iid == p.weapon else ""
            out.append(f"{i} {self.c.item(iid)['name']}{eq} x{p.inventory[iid]}")
        self.lines(["  ".join(out) if sum(len(o) + 2 for o in out) <= R.WIDTH else "\n".join(out)])
        self.lines([f"Wielding {self.c.item(p.weapon)['name']}. USE n, EQ n, I n = details."])

    def describe_item(self, arg: str) -> None:
        iid = self.find_item(arg)
        if not iid:
            self.lines(["No such item."])
            return
        it = self.c.item(iid)
        self.say(f"{it['name']}: {it.get('desc', '')}", log=False)

    def use_item(self, arg: str) -> None:
        iid = self.find_item(arg) if arg else None
        if not iid:
            self.lines(["Use what? I lists your items."])
            return
        st, it = self.state, self.c.item(iid)
        if it.get("type") == "weapon":
            st.player.weapon = iid
            self.lines([f"Equipped {it['name']}."])
        elif it.get("type") == "aid":
            for m in use_aid(st, self.c, iid):
                self.say(m)
        else:
            self.lines([f"You can't use the {it['name']}."])

    def show_stats(self) -> None:
        st, p = self.state, self.state.player
        w = self.c.item(p.weapon)
        ammo = f" ({p.inventory.get(w['ammo'], 0)})" if w.get("ammo") else ""
        comp = ""
        if st.companion:
            comp = " | with " + self.c.companions.get(st.companion, {}).get("name", st.companion)
        self.lines([f"DEZ HARLAN LV{p.level} XP{p.xp}/{p.xp_to_next()} HP{p.hp}/{p.max_hp} "
                    f"SIG{int(p.signal)} cells {p.cells}",
                    " ".join(f"{s} {p.stats[s]}" for s in STATS),
                    f"{w['name']}{ammo}{comp}"])

    def show_quests(self) -> None:
        st = self.state
        cur = tutorial.current(st, self.c)
        if cur:
            self.say(f"ORIENTATION {cur[0]}/{len(tutorial.steps(self.c))}: {cur[1].get('line', cur[1]['text'])}",
                     log=False)
        if not st.quests:
            self.lines(["No quests yet."])
        done = []
        for qid, stage in reversed(list(st.quests.items())):
            q = self.c.quests[qid]
            if stage == "done":
                done.append(q["name"])
            else:
                self.say(f"* {q['name']}: {q['stages'][stage]}", log=False)
        if done:
            self.say("Done: " + ", ".join(done), log=False)

    def show_notes(self, arg: str) -> None:
        notes = self.state.notes
        if not notes:
            self.lines(["No data."])
        elif arg.isdigit() and 0 < int(arg) <= len(notes):
            title, body = notes[int(arg) - 1]
            self.say(f"{title}: {body}", log=False)
        else:
            self.lines([f"{i} {t}" for i, (t, _) in enumerate(notes, 1)] + ["NOTES n to read one."])

    # ---- combat ------------------------------------------------------------
    def start_combat(self) -> None:
        self.combat = Combat(self.loc, self.rng)
        self.mode = "combat"
        names = ", ".join(e.name for e in self.combat.enemies())
        self.say(f"COMBAT: {names}.")
        if tutorial.take_tip(self.state, "combat"):
            self.queue.appendleft(("tip", "combat"))

    def combat_status(self) -> str:
        cb, p = self.combat, self.state.player
        s = f"R{cb.round} AP{cb.ap}/{MAX_AP} HP{p.hp}/{p.max_hp}"
        t = cb.target()
        if t:
            px, py = self.state.pos
            s += (f" | {t.name} {max(0, t.hp)}/{t.max_hp} {R.direction(t.x - px, t.y - py)}"
                  f" {cb.hit_chance(t)}% {cb.attack_cost()}AP")
            if not cb.in_range(t):
                s += " OUT OF RANGE"
            if t.status:
                s += " [" + ",".join(t.status) + "]"
            others = len(cb.enemies()) - 1
            if others > 0:
                s += f" +{others}"
        return R.asciify(s)

    def show_parts(self) -> None:
        cb = self.combat
        t = cb.target()
        parts = [f"{i} {p['name']} {cb.hit_chance(t, p)}%" for i, p in enumerate(cb.parts(t), 1)]
        self.lines([f"LOCK-ON (+2 AP): " + "  ".join(parts) + "  x cancel"])

    def in_combat(self, cmd: str) -> None:
        cb = self.combat
        k = cmd.lower()
        msgs: list[str] = []
        m = MOVE_RE.fullmatch(k)
        if not k:
            return
        if m:
            dx, dy = DIRS[m.group(1)]
            for _ in range(max(1, min(int(m.group(2) or 1), MAX_AP))):
                ap = cb.ap
                events = cb.move(dx, dy)
                if any(e[0] == "exit" for e in events):
                    self.queue.extend(events)
                    self.pump()
                    return
                msgs += [e[1] for e in events]
                if events or cb.ap == ap:
                    break
        elif k == "f":
            msgs = cb.attack()
        elif re.fullmatch(r"a\s*\d", k):
            msgs = self.aimed(int(k[-1]))
        elif k == "a":
            if cb.target():
                self.mode = "lockon"
                self.show_parts()
            return
        elif k == "t":
            cb.cycle_target()
        elif k == "u":
            h = cb.best_heal()
            msgs = cb.use_item(h) if h else ["Nothing to heal with."]
        elif k in (".", "end"):
            self.say(f"-- Round {cb.round}: enemy turn --", log=False)
            msgs = cb.end_turn()
        elif k in ("m", "map"):
            self.show_map()
            return
        elif k in ("l", "look"):
            self.lines(R.look(self.loc))
            return
        elif k in ("?", "h", "help"):
            self.show_tip("controls")
            return
        elif k in ("bye", "quit"):
            self.quit()
            return
        elif k in ("i", "use", "eq", "save") or k.startswith(("use ", "eq ")):
            self.lines(["No time for that. U drinks your best heal (2 AP)."])
            return
        else:
            self.lines(["F fire, A aim, T target, U heal, N/S/E/W move, . end turn"])
            return
        self.after_action(msgs)

    def aimed(self, n: int) -> list[str]:
        cb = self.combat
        parts = cb.parts(cb.target()) if cb.target() else []
        if not 1 <= n <= len(parts):
            return ["No such part."]
        self.mode = "combat"
        return cb.attack(parts[n - 1]["id"])

    def in_lockon(self, cmd: str) -> None:
        k = cmd.lower()
        if k.isdigit():
            self.after_action(self.aimed(int(k)))
        elif k in ("x", "esc", "a"):
            self.mode = "combat"
        else:
            self.show_parts()

    def after_action(self, msgs: list[str]) -> None:
        for m in msgs:
            self.say(m)
        cb = self.combat
        if cb and cb.outcome == "won":
            self.say("Combat over. You're still unmanaged.")
            self.state.flags.add("did:won_combat")
            self.combat = None
            self.mode = "explore"
            save_game(self.state, self.slot)
        elif cb and cb.outcome == "lost":
            self.game_over(self.c.text["game_over_default"])
            return
        elif cb and cb.ap == 0 and self.mode != "lockon":
            self.lines(["Out of AP. '.' ends your turn."])
        self.pump()

    # ---- dialogue ----------------------------------------------------------
    def open_dialogue(self, did: str) -> None:
        self.dlg = Dialogue(did, self.state, self.c)
        self.mode = "dialogue"
        self.show_dialogue()

    def show_dialogue(self, options_only: bool = False) -> None:
        d = self.dlg
        if not options_only:
            self.lines([d.speaker.upper()])
            self.say(d.text, log=False)
        for i, (label, ok, _) in enumerate(d.options(), 1):
            self.out += R.wrap(f"{i}. {label}" + ("" if ok else " (not enough)"), indent="")

    def in_dialogue(self, cmd: str) -> None:
        d = self.dlg
        prev = d.node_id
        if not (cmd.isdigit() and d.choose(int(cmd) - 1)):
            self.show_dialogue(options_only=True)
            return
        if d.done:
            self.dlg = None
            self.resume_after_modal(d.events)
        elif d.node_id == prev:
            # shops loop back to the same node: skip the paragraph, it costs airtime
            self.lines([f"Done. You have {self.state.player.cells} cells."])
            self.show_dialogue(options_only=True)
        else:
            self.show_dialogue()

    # ---- hacking -----------------------------------------------------------
    def open_hack(self, eid: str) -> None:
        spec = self.loc.get(eid).data["hack"]
        pool = self.c.hack_words[spec.get("length", 5)]
        self.hack = Hack(pool, spec.get("words", 8), attempts_for(self.state.player.stats["Wits"]), self.rng)
        self.hack_eid = eid
        self.mode = "hack"
        self.lines(["ADMIN SHELL: type a word from the dump. Likeness = right letter, right spot. X = back out."])
        self.show_dump()

    def show_dump(self) -> None:
        self.lines([row.split("  ", 1)[-1] for row in self.hack.dump])  # drop the 0x addresses: saves airtime

    def in_hack(self, cmd: str) -> None:
        k = cmd.lower()
        if k in ("x", "esc"):
            self.finish_hack(None)
        elif k in ("d", "dump", ""):
            self.show_dump()
        else:
            self.lines(self.hack.guess(cmd).split("\n"))
            if self.hack.result is not None:
                self.finish_hack(self.hack.result)

    def finish_hack(self, ok: bool | None) -> None:
        events = [] if ok is None else self.loc.terminal_result(self.hack_eid, bool(ok))
        self.hack = None
        self.resume_after_modal(events)

    # ---- city map ----------------------------------------------------------
    def enter_city(self) -> None:
        self.mode = "city"
        self.loc = None
        self.combat = None
        if tutorial.take_tip(self.state, "city"):
            self.show_tip("city")
        self.show_city()

    def unlocked(self, nid: str) -> bool:
        return check(self.c.city["nodes"][nid].get("unlocked_if"), self.state)

    def show_city(self) -> None:
        here = self.state.location.split(":", 1)[1]
        nodes = self.c.city["nodes"]
        self.lines(["CHARLOTTE - CITY MAP"])
        for i, nid in enumerate(self.city_order, 1):
            n = nodes[nid]
            if nid == here:
                status = "you are here"
            elif not self.unlocked(nid):
                status = "locked"
            elif not n.get("location"):
                status = "not built yet"
            else:
                status = "open"
            self.lines([f"{i} {n['name'].title()} - {status}"])
        self.lines(["Number = travel, X n = about it. I Q ST SAVE BYE ? work here too."])

    def in_city(self, cmd: str) -> None:
        k = cmd.lower()
        verb, _, arg = k.partition(" ")
        nodes = self.c.city["nodes"]
        if k.isdigit() and 0 < int(k) <= len(self.city_order):
            nid = self.city_order[int(k) - 1]
            n = nodes[nid]
            if not self.unlocked(nid):
                self.lines(["SERVICE UNAVAILABLE IN YOUR AREA. The Concierge thanks you for your patience."])
            elif not n.get("location"):
                self.lines([f"{n['name'].title()} isn't built yet. The Concierge apologizes for the inconvenience."])
            else:
                place(self.state, self.c, n["location"], n["spawn"])
                save_game(self.state, self.slot)
                self.enter_world([("log", f"You head back to {n['name'].title()}.")])
        elif verb == "x" and arg.isdigit() and 0 < int(arg) <= len(self.city_order):
            n = nodes[self.city_order[int(arg) - 1]]
            self.say(f"{n['name'].title()}: {n.get('blurb', '')}", log=False)
        elif k in ("", "m", "map", "l", "look"):
            self.show_city()
        elif not self.common(verb, arg.strip()):
            self.lines(["Pick a number. ? for help."])
