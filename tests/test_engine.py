"""Engine tests, including a scripted run through the opening act.

Run: python -m pytest -q   (or: python tests/test_engine.py)
"""
import os
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["QCTS_SAVE_DIR"] = tempfile.mkdtemp()

from tos.engine.combat import Combat
from tos.engine.content import get_content
from tos.engine.dialogue import Dialogue
from tos.engine.game import follow_exit, new_game
from tos.engine.hack import Hack, likeness
from tos.engine.state import load_game, save_game
from tos.engine.world import Location

C = get_content()
STATS = {"Brawn": 3, "Grit": 3, "Aim": 3, "Wits": 3, "Charm": 2, "Luck": 1}


def walk_to(loc, tx, ty, events):
    """Greedy walk using BFS from the world (player isn't an entity, so borrow step_toward)."""
    for _ in range(80):
        px, py = loc.state.pos
        if (px, py) == (tx, ty):
            return
        class P:  # tiny stand-in with x/y for pathing
            x, y = px, py
        step = loc.step_toward(P, tx, ty) if max(abs(px - tx), abs(py - ty)) > 1 else (tx, ty)
        assert step, f"no path to {tx},{ty} from {px},{py}"
        dx, dy = step[0] - px, step[1] - py
        if dx and dy:  # diagonal adjacency: take the horizontal leg first
            dy = 0
        events += loc.player_move(dx, dy)
        if any(e[0] in ("combat", "exit") for e in events):
            return


def fight(loc, rng):
    cb = Combat(loc, rng)
    for _ in range(60):
        if cb.outcome:
            break
        t = cb.target()

        def can_shoot():
            px, py = loc.state.pos
            t = cb.target()
            return t and cb.in_range(t) and loc.los(px, py, t.x, t.y)
        while cb.target() and not can_shoot() and cb.ap > 0:
            px, py = loc.state.pos
            class P:
                x, y = px, py
            step = loc.step_toward(P, t.x, t.y)
            ap = cb.ap
            if not step:
                break
            cb.move(step[0] - px, step[1] - py)
            if cb.ap == ap:
                break
        while cb.target() and cb.ap >= cb.attack_cost() and can_shoot() and not cb.outcome:
            ap = cb.ap
            cb.attack()
            if cb.ap == ap:  # out of ammo etc.
                loc.state.player.weapon = "tire_iron"
                break
        if loc.state.player.hp < 12 and cb.best_heal() and cb.ap >= 2:
            cb.use_item(cb.best_heal())
        if not cb.outcome:
            cb.end_turn()
    return cb.outcome


def test_content_loads():
    for lid in C.locations:
        Location(lid, new_game(C, STATS)[0], C)
    for did in C.dialogues:
        Dialogue(did, new_game(C, STATS)[0], C)


def test_hack_likeness():
    assert likeness("AGREE", "TERMS") == 1
    assert likeness("RATES", "RESTS") == 2
    h = Hack(C.hack_words[5], 8, 4, random.Random(1))
    assert len(h.words) == 8 and h.password in h.words
    wrong = next(w for w in h.words if w != h.password)
    assert "Likeness" in h.guess(wrong)
    h.guess(h.password)
    assert h.result is True


def test_tutorial_toggle():
    from tos.engine import tutorial
    on, _ = new_game(C, STATS, tutorial=True)
    ev = tutorial.update(on, C)
    assert ("tip", "welcome") in ev and ("tutorial_step", 1) in ev
    off, _ = new_game(C, STATS, tutorial=False)
    assert tutorial.update(off, C) == [] and tutorial.current(off, C) is None


def test_accept_is_game_over():
    st, _ = new_game(C, STATS)
    d = Dialogue("lumen_home", st, C)
    d.choose(0)  # Accept
    d.choose(1)  # "...Okay. Yeah. Okay."
    assert any(e[0] == "game_over" for e in d.events) and d.done


def play_act1(rng):
    st, ev = new_game(C, STATS)
    assert st.quests["terms"] == 1
    loc = Location(st.location, st, C)
    events = []
    # read Teo's message (tablet at 3,3), grab the tire iron (6,1)
    walk_to(loc, 3, 2, events)
    events += loc.player_move(0, 1)
    assert st.quests["teo"] == 1
    walk_to(loc, 6, 2, events)
    events += loc.player_move(0, -1)
    assert st.player.has("tire_iron")
    st.player.weapon = "tire_iron"
    # hack the terminal at (20, 9): wakes TIDY
    walk_to(loc, 20, 8, events)
    events = loc.player_move(0, 1)
    assert ("hack", "door_terminal") in events and "tidy_awake" in st.flags
    events = loc.terminal_result("door_terminal", True)
    assert "door_unlocked" in st.flags
    assert ("combat",) in events
    assert fight(loc, rng) == "won"
    # out the door
    events = []
    walk_to(loc, 19, 9, events)
    events += loc.player_move(0, 1)
    ex = [e for e in events if e[0] == "exit"]
    assert ex and follow_exit(st, C, ex[0][1]) == "location"
    hall = Location(st.location, st, C)
    # talk to Pruitt at (3,2)
    d = Dialogue("pruitt", st, C)
    d.choose(0)  # "No. I didn't accept."
    d.choose(0)  # "Where would I even go?"
    assert st.quests["last_mile"] == 1
    # walk east, drone should aggro
    events = []
    walk_to(hall, 21, 4, events)
    if ("combat",) in events:
        assert fight(hall, rng) == "won"
        events = []
        walk_to(hall, 21, 4, events)
    events += hall.player_move(0, 1)
    ex = [e for e in events if e[0] == "exit"]
    assert ex and follow_exit(st, C, ex[0][1]) == "location"
    assert st.location == "south_end_street"
    assert st.quests["terms"] == "done" and "act1_done" in st.flags
    return st


def test_opening_act_playthrough():
    st = play_act1(random.Random(7))
    # save / load round trip
    save_game(st)
    st2 = load_game()
    assert st2.flags == st.flags and st2.player.inventory == st.player.inventory


def exit_via(loc, x, y, dx, dy, rng=None):
    for _ in range(5):
        events = []
        walk_to(loc, x, y, events)
        if ("combat",) in events:  # e.g. a Greeter noticed high Signal on the way
            assert fight(loc, rng or random.Random(0)) == "won", loc.state.player.hp
            continue
        events += loc.player_move(dx, dy)
        ex = [e for e in events if e[0] == "exit"]
        if ex:
            return follow_exit(loc.state, C, ex[0][1])
        if ("combat",) in events:
            assert fight(loc, rng or random.Random(0)) == "won", loc.state.player.hp
    raise AssertionError(f"could not exit at {loc.state.pos}")


def test_last_mile_playthrough():
    rng = random.Random(5)
    st = play_act1(rng)
    st.player.weapon = "nail_gun"
    street = Location(st.location, st, C)
    # use tinfoil early to keep Signal down, recruit Biscuit at (6,6) from (6,5)
    from tos.engine.combat import use_aid
    use_aid(st, C, "tinfoil")
    events = []
    walk_to(street, 6, 5, events)
    ev = street.player_move(0, 1)
    assert ("dialogue", "biscuit") in ev
    d = Dialogue("biscuit", st, C)
    d.choose(0)
    d.choose(0)
    assert st.companion == "biscuit" and st.quests["order_shipped"] == 1
    assert street.entity_at(6, 6) is None, "stuck robot removed from the map"
    street.place_companion()
    assert st.companion_pos
    if "combat" in [e[0] for e in events]:
        assert fight(street, rng) == "won"
    assert exit_via(street, 22, 5, 1, 0) == "city"
    assert st.quests["last_mile"] == 2
    # travel to Dilworth from the city map
    node = C.city["nodes"]["dilworth"]
    from tos.engine.game import place
    place(st, C, node["location"], node["spawn"])
    park = Location(st.location, st, C)
    # Kayla at (2,1): talk from (2,2)
    events = []
    walk_to(park, 2, 2, events)
    assert ("dialogue", "kayla") in park.player_move(0, -1)
    d = Dialogue("kayla", st, C)
    d.choose(0)  # what's wrong with the park
    assert st.quests["mow_better"] == 1
    d.choose(0)  # Biscuit delivery
    assert st.quests["order_shipped"] == "done"
    # cross the trigger line: mowers wake, fight them with Biscuit's help
    events = []
    walk_to(park, 9, 4, events)
    assert "mowers_awake" in st.flags
    for _ in range(4):
        if park.awake_enemies():
            assert fight(park, rng) == "won", st.player.hp
    assert park.update_rules() and st.quests["mow_better"] == 2
    d = Dialogue("kayla", st, C)
    labels = [o[0] for o in d.options()]
    assert "The mowers are handled." in labels
    d.choose(labels.index("The mowers are handled."))
    assert st.quests["mow_better"] == "done"
    assert exit_via(park, 22, 4, 1, 0) == "location"
    mid = Location(st.location, st, C)
    mid.update_rules()
    assert st.quests["last_mile"] == "done" and "reached_midwood" in st.flags
    d = Dialogue("delia", st, C)
    d.choose(1)  # brother
    assert st.quests["analog_only"] == 1 and st.quests["teo"] == 3
    # shop: buy a med-gummy
    cells = st.player.cells
    d = Dialogue("hollis", st, C)
    d.choose(1)
    assert st.player.cells == cells - 5
    print("  act 2 end: HP", st.player.hp, "/", st.player.max_hp, "LV", st.player.level, "cells", st.player.cells)


def test_yard_controller_stealth():
    st, _ = new_game(C, STATS)
    from tos.engine.game import place
    place(st, C, "dilworth", "west")
    park = Location("dilworth", st, C)
    park.terminal_result("yard_controller", True)
    assert "mowers_off" in st.flags
    events = []
    walk_to(park, 12, 4, events)
    assert "mowers_awake" not in st.flags and not park.awake_enemies()
    park.update_rules()
    assert st.quests["mow_better"] == 2


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
