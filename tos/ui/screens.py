"""All Textual screens."""
from __future__ import annotations

import random
from collections import deque

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Input, RichLog, Static

from ..engine import tutorial
from ..engine.combat import MAX_AP, Combat, use_aid
from ..engine.content import check
from ..engine.dialogue import Dialogue
from ..engine.game import follow_exit, new_game, place
from ..engine.hack import Hack, attempts_for
from ..engine.state import STAT_BLURBS, STAT_BUDGET, STAT_MAX, STAT_MIN, STATS, has_save, load_game, save_game
from ..engine.world import Location
from .render import bar, render_city, render_map, stars

MOVES = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0),
         "k": (0, -1), "j": (0, 1), "h": (-1, 0), "l": (1, 0)}


def active_quest(state, content):
    for qid in reversed(list(state.quests)):
        stage = state.quests[qid]
        if stage != "done":
            q = content.quests[qid]
            return q["name"], q["stages"][stage]
    return None


# =========================================================================
class TitleScreen(Screen):
    BINDINGS = [Binding("up,k", "cursor(-1)", show=False), Binding("down,j", "cursor(1)", show=False),
                Binding("enter", "choose", show=False), Binding("n", "new", show=False),
                Binding("c", "cont", show=False), Binding("q", "app.quit", show=False)]

    def compose(self) -> ComposeResult:
        with Vertical(id="title-box"):
            yield Static(id="title-art")
            yield Static(id="title-menu")

    def on_mount(self) -> None:
        self.items = [("New Game", "new")]
        if has_save():
            self.items.insert(0, ("Continue", "cont"))
        self.items.append(("Quit", "quit"))
        self.cursor = 0
        art = Text((self.app.content.root / "title.txt").read_text(encoding="utf-8").rstrip("\n"), style="bold #e8c35a")
        art.append("\n\n" + "T E R M S   O F   S E R V I C E".center(77) + "\n", style="bold white")
        art.append(self.app.content.text["tagline"].center(77), style="grey62")
        self.query_one("#title-art", Static).update(art)
        self.draw()

    def draw(self) -> None:
        t = Text()
        for i, (label, _) in enumerate(self.items):
            sel = i == self.cursor
            t.append(("▶ " if sel else "  ") + label + "\n", style="bold reverse" if sel else "white")
        t.append("\nCharlotte, NC · late 2027", style="grey42")
        self.query_one("#title-menu", Static).update(t)

    def action_cursor(self, d: int) -> None:
        self.cursor = (self.cursor + d) % len(self.items)
        self.draw()

    def action_choose(self) -> None:
        getattr(self, f"action_{self.items[self.cursor][1]}", self.app.exit)()

    def action_new(self) -> None:
        self.app.switch_screen(ProfileScreen())

    def action_cont(self) -> None:
        st = load_game()
        if st is None:
            self.notify("No readable save found.", severity="warning")
            return
        self.app.state = st
        self.app.goto_current()

    def action_quit(self) -> None:
        self.app.exit()


# =========================================================================
class ProfileScreen(Screen):
    BINDINGS = [Binding("up,k", "cursor(-1)", show=False), Binding("down,j", "cursor(1)", show=False),
                Binding("left,h,minus", "adjust(-1)", show=False), Binding("right,l,plus,equals_sign", "adjust(1)", show=False),
                Binding("enter", "confirm", show=False), Binding("escape", "back", show=False),
                Binding("o", "toggle_tutorial", show=False)]

    def compose(self) -> ComposeResult:
        yield Static(id="profile", classes="panel")

    def on_mount(self) -> None:
        self.stats = {"Brawn": 3, "Grit": 3, "Aim": 3, "Wits": 2, "Charm": 2, "Luck": 2}
        self.tutorial = True
        self.cursor = 0
        self.draw()

    @property
    def left(self) -> int:
        return STAT_BUDGET - sum(self.stats.values())

    def draw(self) -> None:
        t = Text()
        t.append("RATING PROFILE · DEZ HARLAN\n", style="bold bright_yellow")
        t.append("Rater 4471. Thirty-one. Professional critic of machines.\n\n", style="grey62")
        for i, s in enumerate(STATS):
            sel = i == self.cursor
            t.append("▶ " if sel else "  ", style="bold")
            t.append(f"{s:<6} ", style="bold reverse" if sel else "bold")
            t.append_text(stars(self.stats[s]))
            t.append(f"   {STAT_BLURBS[s]}\n", style="white" if sel else "grey50")
        t.append(f"\nStars left to spend: {self.left}\n", style="bold green" if self.left == 0 else "bold yellow")
        t.append("Orientation (tutorial): ", style="bold")
        t.append("ON" if self.tutorial else "OFF", style="bold green" if self.tutorial else "bold red")
        t.append("  · press O to switch\n", style="grey50")
        t.append("\n↑↓ choose   ←→ adjust   ENTER confirm   ESC back", style="grey50")
        self.query_one("#profile", Static).update(t)

    def action_cursor(self, d: int) -> None:
        self.cursor = (self.cursor + d) % len(STATS)
        self.draw()

    def action_adjust(self, d: int) -> None:
        s = STATS[self.cursor]
        v = self.stats[s] + d
        if STAT_MIN <= v <= STAT_MAX and (d < 0 or self.left > 0):
            self.stats[s] = v
            self.draw()

    def action_confirm(self) -> None:
        if self.left != 0:
            self.notify(f"Spend all {STAT_BUDGET} stars first ({self.left} left).", severity="warning")
            return
        state, events = new_game(self.app.content, self.stats, self.tutorial)
        self.app.state = state
        self.app.switch_screen(IntroScreen(events))

    def action_toggle_tutorial(self) -> None:
        self.tutorial = not self.tutorial
        self.draw()

    def action_back(self) -> None:
        self.app.switch_screen(TitleScreen())


# =========================================================================
class IntroScreen(Screen):
    BINDINGS = [Binding("enter,space", "next", show=False), Binding("escape", "skip", show=False)]

    def __init__(self, start_events: list):
        super().__init__()
        self.start_events = start_events
        self.page = 0

    def compose(self) -> ComposeResult:
        yield Static(id="intro", classes="panel")

    def on_mount(self) -> None:
        self.draw()

    def draw(self) -> None:
        pages = self.app.content.text["intro"]
        t = Text(pages[self.page].strip() + "\n\n", style="white")
        t.append(f"[{self.page + 1}/{len(pages)}]  ENTER continue · ESC skip", style="grey50")
        self.query_one("#intro", Static).update(t)

    def action_next(self) -> None:
        self.page += 1
        if self.page >= len(self.app.content.text["intro"]):
            self.action_skip()
        else:
            self.draw()

    def action_skip(self) -> None:
        save_game(self.app.state)  # autosave at the start so a death always has a save to load
        self.app.switch_screen(LocationScreen(self.start_events))


# =========================================================================
class LocationScreen(Screen):
    BINDINGS = [Binding("tab", "wristlink", "WristLink", priority=True, show=False)]

    def __init__(self, events: list | None = None):
        super().__init__()
        self.queue: deque = deque(events or [])
        self.combat: Combat | None = None
        self.lockon = False
        self.busy = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield Static(id="map", classes="panel")
                yield RichLog(id="log", wrap=True, markup=False, min_width=20, classes="panel")
            yield Static(id="side", classes="panel")
        yield Static(id="help")

    def on_mount(self) -> None:
        log = self.query_one("#log", RichLog)
        log.can_focus = False
        for line in self.app.state.log[-6:]:
            log.write(Text(line, style="grey50"))
        self.load_location()
        self.pump()

    # ---- plumbing -------------------------------------------------------
    @property
    def state(self):
        return self.app.state

    def load_location(self) -> None:
        self.loc = Location(self.state.location, self.state, self.app.content)
        m = self.query_one("#map", Static)
        m.border_title = f"{self.loc.district} · {self.loc.name}"
        self.refresh_view()

    def say(self, text: str, style: str = "white") -> None:
        self.state.say(text)
        self.query_one("#log", RichLog).write(Text("› " + text, style=style))

    def refresh_view(self) -> None:
        self.loc.place_companion()
        self.query_one("#map", Static).update(render_map(self.loc, self.combat))
        self.query_one("#side", Static).update(self.side_panel())
        if self.combat and self.lockon:
            h = "1-4 pick a part · ESC cancel"
        elif self.combat:
            h = "←↑↓→ move · F attack · A aim · T target · U heal · SPACE end turn · ? help"
        else:
            h = "←↑↓→/hjkl move · walk into things · TAB WristLink · S save · Q quit · ? help"
        self.query_one("#help", Static).update(Text(h, style="grey62"))

    def side_panel(self) -> Text:
        st, p = self.state, self.state.player
        t = Text()
        t.append("DEZ HARLAN", style="bold bright_yellow")
        t.append(f"   LV {p.level}\n", style="bold")
        t.append("HP  ")
        t.append_text(bar(p.hp, p.max_hp, 10, "green" if p.hp > p.max_hp / 3 else "red"))
        t.append(f" {p.hp}/{p.max_hp}\n")
        t.append("SIG ")
        t.append_text(bar(p.signal, 100, 10, "magenta" if p.signal < 75 else "bold red"))
        t.append(f" {int(p.signal)}\n")
        t.append("XP  ")
        t.append_text(bar(p.xp, p.xp_to_next(), 10, "yellow"))
        t.append(f" {p.xp}\n")
        w = self.app.content.item(p.weapon)
        ammo = f" ({p.inventory.get(w['ammo'], 0)})" if w.get("ammo") else ""
        t.append(f"cells {p.cells}\n", style="cyan")
        t.append(f"{w['name']}{ammo}\n", style="white")
        if st.companion:
            cname = self.app.content.companions.get(st.companion, {}).get("name", st.companion)
            t.append(f"with {cname}\n", style="bright_cyan")
        t.append("─" * 24 + "\n", style="grey30")
        if self.combat:
            t.append_text(self.combat_panel())
        else:
            cur = tutorial.current(st, self.app.content)
            if cur:
                n = len(tutorial.steps(self.app.content))
                t.append(f"ORIENTATION {cur[0]}/{n}\n", style="bold black on #e8c35a")
                t.append(cur[1]["text"] + "\n", style="#e8c35a")
                t.append("─" * 24 + "\n", style="grey30")
            q = active_quest(st, self.app.content)
            if q:
                t.append(q[0].upper() + "\n", style="bold")
                t.append(q[1], style="grey70")
        return t

    def combat_panel(self) -> Text:
        cb = self.combat
        t = Text()
        t.append(f"COMBAT · ROUND {cb.round}\n", style="bold red")
        t.append("AP ")
        t.append("●" * cb.ap, style="bold bright_cyan")
        t.append("○" * (MAX_AP - cb.ap) + "\n", style="grey35")
        e = cb.target()
        if not e:
            return t
        t.append(f"▶ {e.name}\n", style="bold")
        t.append("HP ")
        t.append_text(bar(e.hp, e.max_hp, 10, "red"))
        t.append(f" {max(0, e.hp)}/{e.max_hp}\n")
        status = ", ".join(e.status) or "—"
        t.append(f"status: {status}\n", style="grey62")
        t.append(f"Hit {cb.hit_chance(e)}% · {cb.attack_cost()} AP\n")
        t.append("in range\n" if cb.in_range(e) else "OUT OF RANGE\n", style="grey62" if cb.in_range(e) else "bold red")
        if self.lockon:
            t.append("LOCK-ON (+2 AP)\n", style="bold magenta")
            for i, part in enumerate(cb.parts(e), 1):
                t.append(f"{i} {part['name']:<13}{cb.hit_chance(e, part):>3}%\n")
        others = len(cb.enemies()) - 1
        if others > 0:
            t.append(f"+{others} more hostile", style="grey62")
        return t

    def pump(self) -> None:
        """Process queued events; modal events pause the queue until they return."""
        while not self.busy:
            if not self.queue:
                self.queue.extend(self.loc.update_rules())
                self.queue.extend(tutorial.update(self.state, self.app.content))
                if not self.queue:
                    break
            ev = self.queue.popleft()
            kind = ev[0]
            if kind == "log":
                self.say(ev[1], "bold green" if ev[1].startswith("✓") else "white")
            elif kind == "tutorial_step":
                s = tutorial.steps(self.app.content)[ev[1] - 1]
                self.say(f"ORIENTATION {ev[1]}: {s['text']}", "bold #e8c35a")
            elif kind == "tip":
                self.busy = True
                self.app.push_screen(TipScreen(ev[1]), self._modal_done)
            elif kind == "dialogue":
                self.busy = True
                self.app.push_screen(DialogueScreen(ev[1]), self._modal_done)
            elif kind == "hack":
                if tutorial.take_tip(self.state, "hack"):
                    self.queue.appendleft(ev)
                    self.queue.appendleft(("tip", "hack"))
                    continue
                self.busy = True
                eid = ev[1]
                spec = self.loc.get(eid).data["hack"]
                self.app.push_screen(HackScreen(spec), lambda hack, eid=eid: self._hack_done(eid, hack))
            elif kind == "combat":
                if not self.combat:
                    self.start_combat()
            elif kind == "exit":
                self.queue.clear()
                self.do_exit(ev[1])
                return
            elif kind == "game_over":
                self.queue.clear()
                self.app.switch_screen(GameOverScreen(ev[1]))
                return
        self.refresh_view()

    def _modal_done(self, events) -> None:
        self.busy = False
        self.queue.extendleft(reversed(events or []))
        self.pump()

    def _hack_done(self, eid: str, hack) -> None:
        events = [] if hack is None else self.loc.terminal_result(eid, bool(hack.result), hack.hit)
        self._modal_done(events)

    def do_exit(self, to: dict) -> None:
        self.combat = None
        kind = follow_exit(self.state, self.app.content, to)
        save_game(self.state)
        if kind == "city":
            self.app.switch_screen(CityScreen())
        else:
            self.load_location()
            self.queue.extend(self.loc.check_aggro())
            self.pump()

    # ---- input ----------------------------------------------------------
    def on_key(self, event) -> None:
        if self.busy:
            return
        key = event.key
        if key in ("question_mark", "?"):
            event.stop()
            self.busy = True
            self.app.push_screen(TipScreen("controls"), self._modal_done)
            return
        if self.combat:
            self.combat_key(key)
        elif key in MOVES:
            self.queue.extend(self.loc.player_move(*MOVES[key]))
            self.pump()
        elif key in ("s", "S"):
            self.state.flags.add("did:saved")
            save_game(self.state)
            self.say("Saved.", "grey62")
            self.pump()
        elif key in ("q", "Q"):
            save_game(self.state)
            self.app.switch_screen(TitleScreen())
        else:
            return
        event.stop()

    def action_wristlink(self) -> None:
        if self.busy:
            return
        if self.combat:
            self.say("No time to scroll. U drinks your best healing item (2 AP).", "grey62")
            return
        self.app.push_screen(WristLinkScreen(), lambda _: self.pump())

    # ---- combat ---------------------------------------------------------
    def start_combat(self) -> None:
        self.combat = Combat(self.loc, self.app.rng)
        names = ", ".join(e.name for e in self.combat.enemies())
        self.say(f"COMBAT: {names}.", "bold red")
        self.lockon = False
        if tutorial.take_tip(self.state, "combat"):
            self.queue.appendleft(("tip", "combat"))

    def combat_key(self, key: str) -> None:
        cb = self.combat
        msgs: list = []
        if self.lockon:
            if key == "escape":
                self.lockon = False
            elif key.isdigit():
                parts = cb.parts(cb.target()) if cb.target() else []
                i = int(key) - 1
                if 0 <= i < len(parts):
                    self.lockon = False
                    msgs = cb.attack(parts[i]["id"])
            self.after_action(msgs)
            return
        if key in MOVES:
            events = cb.move(*MOVES[key])
            if any(e[0] == "exit" for e in events):
                self.queue.extend(events)
                self.pump()
                return
            msgs = [e[1] for e in events]
        elif key in ("f", "F"):
            msgs = cb.attack()
        elif key in ("a", "A"):
            if cb.target():
                self.lockon = True
        elif key in ("t", "T"):
            cb.cycle_target()
        elif key in ("u", "U"):
            h = cb.best_heal()
            msgs = cb.use_item(h) if h else ["Nothing to heal with."]
        elif key in ("space", "enter"):
            self.say(f"— Round {cb.round}: enemy turn —", "grey50")
            msgs = cb.end_turn()
        self.after_action(msgs)

    def after_action(self, msgs: list[str]) -> None:
        for m in msgs:
            self.say(m, "bold yellow" if m.startswith("SURPRISE") else "white")
        cb = self.combat
        if cb and cb.outcome == "won":
            self.say("Combat over. You're still unmanaged.", "bold green")
            self.state.flags.add("did:won_combat")
            self.combat = None
            save_game(self.state)
        elif cb and cb.outcome == "lost":
            self.app.switch_screen(GameOverScreen(self.app.content.text["game_over_default"]))
            return
        elif cb and cb.ap == 0 and not self.lockon:
            self.say("Out of AP. SPACE to end your turn.", "grey62")
        self.pump()


# =========================================================================
class DialogueScreen(ModalScreen):
    BINDINGS = [Binding("up,k", "cursor(-1)", show=False), Binding("down,j", "cursor(1)", show=False),
                Binding("enter", "pick", show=False)]

    def __init__(self, did: str):
        super().__init__()
        self.did = did
        self.cursor = 0

    def compose(self) -> ComposeResult:
        yield Static(id="dialogue", classes="panel modal")

    def on_mount(self) -> None:
        self.dlg = Dialogue(self.did, self.app.state, self.app.content)
        self.draw()

    def draw(self) -> None:
        d = self.dlg
        t = Text()
        t.append(d.speaker + "\n\n", style="bold bright_green")
        t.append(d.text + "\n\n", style="white")
        for i, (label, ok, _) in enumerate(d.options()):
            sel = i == self.cursor
            style = ("bold reverse" if sel else "bold white") if ok else "grey42"
            t.append(f"{'▶' if sel else ' '} {i + 1}. {label}" + ("" if ok else "  (not enough)") + "\n", style=style)
        box = self.query_one("#dialogue", Static)
        box.border_title = "TALK"
        box.update(t)

    def on_key(self, event) -> None:
        if event.key.isdigit():
            event.stop()
            self.choose(int(event.key) - 1)

    def action_cursor(self, d: int) -> None:
        self.cursor = (self.cursor + d) % max(1, len(self.dlg.options()))
        self.draw()

    def action_pick(self) -> None:
        self.choose(self.cursor)

    def choose(self, i: int) -> None:
        if not self.dlg.choose(i):
            return
        if self.dlg.done:
            self.dismiss(self.dlg.events)
        else:
            self.cursor = 0
            self.draw()


# =========================================================================
class HackScreen(ModalScreen):
    BINDINGS = [Binding("escape", "abort", show=False)]

    def __init__(self, spec: dict):
        super().__init__()
        self.spec = spec

    def compose(self) -> ComposeResult:
        with Vertical(id="hack", classes="panel modal"):
            yield Static(id="hack-head")
            with Horizontal(id="hack-cols"):
                yield Static(id="hack-dump")
                yield Static(id="hack-hist")
            yield Input(placeholder="type a word, press ENTER", id="hack-input")

    def on_mount(self) -> None:
        app = self.app
        pool = app.content.hack_words[self.spec.get("length", 5)]
        self.hack = Hack(pool, self.spec.get("words", 8), attempts_for(app.state.player.stats["Wits"]), app.rng)
        self.lines: list[str] = []
        self.query_one("#hack", Vertical).border_title = "CONCIERGE ADMIN SHELL · PROMPT INJECTION"
        self.draw()
        self.query_one("#hack-input", Input).focus()

    def draw(self) -> None:
        h = self.hack
        head = Text("Find the passphrase. LIKENESS = letters right, in the right spot.\n", style="grey62")
        head.append("ATTEMPTS ", style="bold")
        head.append("■ " * h.attempts, style="bold bright_green")
        head.append("□ " * (h.max_attempts - h.attempts), style="grey35")
        head.append("   ESC back out", style="grey42")
        self.query_one("#hack-head", Static).update(head)
        self.query_one("#hack-dump", Static).update(Text("\n".join(h.dump), style="green"))
        hist = Text()
        for line in self.lines[-9:]:
            hist.append(line + "\n", style="bright_green")
        if h.result is not None:
            hist.append("[press any key]", style="bold")
        self.query_one("#hack-hist", Static).update(hist)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.hack.result is not None:
            return
        self.lines += self.hack.guess(event.value).split("\n")
        event.input.value = ""
        if self.hack.result is not None:
            event.input.disabled = True
            self.focus()
        self.draw()

    def on_key(self, event) -> None:
        if self.hack.result is not None:
            event.stop()
            self.dismiss(self.hack)

    def action_abort(self) -> None:
        if self.hack.result is None:
            self.dismiss(None)


# =========================================================================
class WristLinkScreen(ModalScreen):
    TABS = ["STATUS", "ITEMS", "QUESTS", "DATA"]
    BINDINGS = [Binding("tab,escape", "close", priority=True, show=False),
                Binding("left,h", "tab(-1)", show=False), Binding("right,l", "tab(1)", show=False),
                Binding("up,k", "cursor(-1)", show=False), Binding("down,j", "cursor(1)", show=False),
                Binding("enter", "use", show=False)]

    def compose(self) -> ComposeResult:
        yield Static(id="wrist", classes="panel modal")

    def on_mount(self) -> None:
        self.app.state.flags.add("did:wristlink")
        self.tab = 0
        self.cursor = 0
        self.flash = ""
        self.draw()

    def items(self) -> list[str]:
        inv = self.app.state.player.inventory
        return sorted(inv, key=lambda i: (self.app.content.item(i).get("type", ""), i))

    def draw(self) -> None:
        st, p, c = self.app.state, self.app.state.player, self.app.content
        t = Text()
        for i, name in enumerate(self.TABS):
            t.append(f" {name} ", style="bold reverse" if i == self.tab else "grey62")
            t.append(" ")
        t.append("\n" + "─" * 60 + "\n", style="grey30")
        tab = self.TABS[self.tab]
        if tab == "STATUS":
            t.append(f"DEZ HARLAN · Level {p.level} · XP {p.xp}/{p.xp_to_next()}\n", style="bold")
            t.append(f"HP {p.hp}/{p.max_hp} · Signal {int(p.signal)} · {p.cells} cells\n\n")
            t.append("RATING PROFILE\n", style="bold bright_yellow")
            for s in STATS:
                t.append(f"  {s:<6} ")
                t.append_text(stars(p.stats[s]))
                t.append(f"  {STAT_BLURBS[s]}\n", style="grey50")
        elif tab == "ITEMS":
            items = self.items()
            if not items:
                t.append("Nothing. Not even lint.\n", style="grey50")
            self.cursor = min(self.cursor, max(0, len(items) - 1))
            for i, iid in enumerate(items):
                it = c.item(iid)
                sel = i == self.cursor
                eq = " [equipped]" if iid == p.weapon else ""
                t.append(f"{'▶' if sel else ' '} {it['name']} x{p.inventory[iid]}{eq}\n",
                         style="bold reverse" if sel else "white")
            if items:
                it = c.item(items[self.cursor])
                t.append("\n" + it.get("desc", "") + "\n", style="grey62")
                verb = {"weapon": "ENTER equip", "aid": "ENTER use"}.get(it.get("type"), "")
                t.append(verb + "\n", style="grey50")
            if p.weapon == "fists":
                t.append("\nWielding: Fists\n", style="grey50")
        elif tab == "QUESTS":
            if not st.quests:
                t.append("No quests yet.\n", style="grey50")
            for qid, stage in reversed(list(st.quests.items())):
                q = c.quests[qid]
                done = stage == "done"
                t.append(("✓ " if done else "• ") + q["name"] + "\n", style="grey50" if done else "bold")
                if not done:
                    t.append("  " + q["stages"][stage] + "\n\n", style="grey70")
        else:
            if not st.notes:
                t.append("No data.\n", style="grey50")
            for title, body in st.notes:
                t.append(title + "\n", style="bold cyan")
                t.append(body + "\n\n", style="grey70")
        if self.flash:
            t.append("\n" + self.flash, style="bold green")
        t.append("\n←→ tabs · ↑↓ select · ENTER use · TAB/ESC close", style="grey42")
        box = self.query_one("#wrist", Static)
        box.border_title = "WRISTLINK"
        box.update(t)

    def action_close(self) -> None:
        self.dismiss(None)

    def action_tab(self, d: int) -> None:
        self.tab = (self.tab + d) % len(self.TABS)
        if self.TABS[self.tab] == "QUESTS":
            self.app.state.flags.add("did:quests_tab")
        self.flash = ""
        self.draw()

    def action_cursor(self, d: int) -> None:
        if self.TABS[self.tab] == "ITEMS" and self.items():
            self.cursor = (self.cursor + d) % len(self.items())
            self.flash = ""
            self.draw()

    def action_use(self) -> None:
        if self.TABS[self.tab] != "ITEMS" or not self.items():
            return
        iid = self.items()[self.cursor]
        st, it = self.app.state, self.app.content.item(iid)
        if it.get("type") == "weapon":
            st.player.weapon = iid
            self.flash = f"Equipped {it['name']}."
        elif it.get("type") == "aid":
            msgs = use_aid(st, self.app.content, iid)
            for m in msgs:
                st.say(m)
            self.flash = " ".join(msgs)
        self.draw()


# =========================================================================
class TipScreen(ModalScreen):
    """A one-screen explainer: tutorial tips and the controls list."""
    BINDINGS = [Binding("enter,space,escape", "close", priority=True, show=False)]

    def __init__(self, tid: str):
        super().__init__()
        self.tid = tid

    def compose(self) -> ComposeResult:
        yield Static(id="tip", classes="panel modal")

    def on_mount(self) -> None:
        tut = self.app.content.tutorial
        tip = tut["controls"] if self.tid == "controls" else tut["tips"][self.tid]
        t = Text(tip["text"].rstrip() + "\n\n", style="white")
        t.append("ENTER to continue", style="bold #e8c35a")
        box = self.query_one("#tip", Static)
        box.border_title = tip["title"]
        box.update(t)

    def action_close(self) -> None:
        self.dismiss([])


# =========================================================================
class CityScreen(Screen):
    BINDINGS = [Binding("tab", "wristlink", priority=True, show=False),
                Binding("up,k,left,h", "cursor(-1)", show=False), Binding("down,j,right,l", "cursor(1)", show=False),
                Binding("enter", "travel", show=False), Binding("s", "save", show=False),
                Binding("q", "quit_title", show=False)]

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="cityleft"):
                yield Static(id="citymap", classes="panel")
                yield Static(id="citymsg", classes="panel")
            yield Static(id="cityside", classes="panel")
        yield Static(id="help")

    def on_mount(self) -> None:
        city = self.app.content.city
        self.order = sorted(city["nodes"], key=lambda n: (city["nodes"][n]["y"], city["nodes"][n]["x"]))
        here = self.app.state.location.split(":", 1)[1]
        self.cursor = self.order.index(here) if here in self.order else 0
        self.query_one("#citymap", Static).border_title = "CHARLOTTE · CITY MAP"
        self.query_one("#help", Static).update(Text("↑↓ choose destination · ENTER travel · TAB WristLink · S save · Q quit", style="grey62"))
        self.msg = "You're on the street. The air smells like ozone and somebody's grill."
        self.draw()
        if tutorial.take_tip(self.app.state, "city"):
            self.app.push_screen(TipScreen("city"))

    def unlocked(self, nid: str) -> bool:
        return check(self.app.content.city["nodes"][nid].get("unlocked_if"), self.app.state)

    def draw(self) -> None:
        city = self.app.content.city
        sel = self.order[self.cursor]
        self.query_one("#citymap", Static).update(render_city(city, self.app.state, sel, self.unlocked))
        n = city["nodes"][sel]
        t = Text()
        t.append(n["name"] + "\n", style="bold bright_yellow")
        if not self.unlocked(sel):
            t.append("SERVICE UNAVAILABLE\nIN YOUR AREA\n\n", style="bold red")
        elif not n.get("location"):
            t.append("Not built yet\n\n", style="yellow")
        else:
            t.append("Open\n\n", style="bold green")
        t.append(n.get("blurb", ""), style="grey70")
        q = active_quest(self.app.state, self.app.content)
        if q:
            t.append("\n\n" + q[0].upper() + "\n", style="bold")
            t.append(q[1], style="grey62")
        self.query_one("#cityside", Static).update(t)
        self.query_one("#citymsg", Static).update(Text(self.msg, style="white"))

    def action_cursor(self, d: int) -> None:
        self.cursor = (self.cursor + d) % len(self.order)
        self.draw()

    def action_travel(self) -> None:
        nid = self.order[self.cursor]
        n = self.app.content.city["nodes"][nid]
        if not self.unlocked(nid):
            self.msg = "SERVICE UNAVAILABLE IN YOUR AREA. The Concierge thanks you for your patience."
        elif not n.get("location"):
            self.msg = f"{n['name']} isn't built yet. (Next build phase.) The Concierge apologizes for the inconvenience."
        else:
            place(self.app.state, self.app.content, n["location"], n["spawn"])
            save_game(self.app.state)
            self.app.switch_screen(LocationScreen([("log", f"You head back to {n['name'].title()}.")]))
            return
        self.draw()

    def action_save(self) -> None:
        save_game(self.app.state)
        self.msg = "Saved."
        self.draw()

    def action_quit_title(self) -> None:
        save_game(self.app.state)
        self.app.switch_screen(TitleScreen())

    def action_wristlink(self) -> None:
        self.app.push_screen(WristLinkScreen(), lambda _: self.draw())


# =========================================================================
class GameOverScreen(Screen):
    BINDINGS = [Binding("l", "load", show=False), Binding("t,escape", "title", show=False)]

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def compose(self) -> ComposeResult:
        yield Static(id="gameover", classes="panel")

    def on_mount(self) -> None:
        t = Text("SESSION EXPIRED\n\n", style="bold red")
        t.append(self.text + "\n\n", style="white")
        t.append("Thank you for choosing calm.\n\n", style="grey50")
        t.append(("L load last save · " if has_save() else "") + "T title screen", style="grey62")
        self.query_one("#gameover", Static).update(t)

    def action_load(self) -> None:
        st = load_game()
        if st:
            self.app.state = st
            self.app.goto_current()

    def action_title(self) -> None:
        self.app.switch_screen(TitleScreen())
