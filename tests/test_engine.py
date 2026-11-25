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


def play_act2(rng):
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
    return st


def test_last_mile_playthrough():
    st = play_act2(random.Random(5))
    print("  act 2 end: HP", st.player.hp, "/", st.player.max_hp, "LV", st.player.level, "cells", st.player.cells)


def talk(did, st, *choices):
    d = Dialogue(did, st, C)
    for c in choices:
        assert d.choose(c), (did, d.node_id, c, [o[0] for o in d.options()])
    return d


def prep(st):
    """Between fights: foil off high Signal, heal up to 60% HP (what a careful player does)."""
    from tos.engine.combat import use_aid
    p = st.player
    if p.signal >= 40 and p.has("tinfoil"):
        use_aid(st, C, "tinfoil")
    for item in ("med_gummy", "sweet_tea"):
        while p.hp < p.max_hp * 0.6 and p.has(item):
            use_aid(st, C, item)


def play_act3(rng, stealth=False):
    """Quest 3. stealth=True: hack station control and the cab console (no boss fight)."""
    from tos.engine.content import check
    from tos.engine.game import place
    st = play_act2(rng)
    node = C.city["nodes"]["noda"]
    assert check(node.get("unlocked_if"), st)
    assert not check(C.city["nodes"]["blue_line"].get("unlocked_if"), st), "Blue Line opens with the job"
    place(st, C, node["location"], node["spawn"])
    noda = Location(st.location, st, C)
    noda.update_rules()
    # Ruth (6,5) from (6,4): the brewery door is shut until she lets you in
    assert not noda.door_open(noda.get("brewery_door"))
    events = []
    walk_to(noda, 6, 4, events)
    assert ("dialogue", "ruth") in noda.player_move(0, 1)
    talk("ruth", st, 0)  # Delia vouches
    assert "ruth_ok" in st.flags and noda.door_open(noda.get("brewery_door"))
    # Mags (11,3) from (10,3)
    walk_to(noda, 10, 3, events)
    assert ("dialogue", "mags") in noda.player_move(1, 0)
    talk("mags", st, 0, 0, 0)
    assert st.quests["analog_only"] == 2
    talk("bev", st, 0, 0, 2)
    # little free library (3,3): tinfoil + med-gummy, then prep like a player would
    walk_to(noda, 3, 4, events)
    noda.player_move(0, -1)
    assert "noda:book_box" in st.taken
    prep(st)
    # 36th Street station
    node = C.city["nodes"]["blue_line"]
    assert check(node.get("unlocked_if"), st)
    place(st, C, node["location"], node["spawn"])
    station = Location(st.location, st, C)
    if stealth:
        station.terminal_result("station_control", True)
        assert "train_open" in st.flags
    assert exit_via(station, 12, 6, 0, 1, rng) == "location", "force or walk through the train door"
    assert st.location == "lynx_train"
    if not stealth:
        assert "train_open" in st.flags  # forced with the tire iron
    train = Location(st.location, st, C)
    prep(st)
    if stealth:
        events = []
        walk_to(train, 20, 5, events)
        assert ("hack", "cab_console") in train.player_move(1, 0)
        train.terminal_result("cab_console", True)
        assert "service_ended" in st.flags
    # Dante (9,7) from (9,6)
    events = []
    walk_to(train, 9, 6, events)
    assert ("dialogue", "dante") in train.player_move(0, 1)
    talk("dante", st, 0, 0, 0)
    assert st.player.has("faraday_drive") and st.quests["analog_only"] == 3
    logs = [e[1] for e in train.update_rules()]
    if stealth:
        assert not train.awake_enemies() and any("Off shift" in m for m in logs)
    else:
        assert train.awake_enemies() and any("unfolds" in m for m in logs)
        events = []
        walk_to(train, 8, 6, events)
        assert ("combat",) in events
        assert fight(train, rng) == "won", st.player.hp
        assert "lynx_train:pxu" in st.taken
    assert exit_via(train, 1, 2, -1, 0, rng) == "location"
    assert st.location == "lynx_36th"
    # back to Mags
    place(st, C, "noda", "city")
    talk("mags", st, 0, 0, 0, 0)
    assert st.quests["analog_only"] == "done" and "optout_trusted" in st.flags
    assert st.quests["service_interruption"] == 1 and st.quests["teo"] == 4
    assert not st.player.has("faraday_drive")
    return st


def test_analog_only_fight():
    st = play_act3(random.Random(5))
    print("  act 3 end (fight): HP", st.player.hp, "/", st.player.max_hp, "LV", st.player.level, "cells", st.player.cells)


def test_analog_only_stealth():
    st = play_act3(random.Random(9), stealth=True)
    assert "lynx_train:pxu" not in st.taken
    print("  act 3 end (stealth): HP", st.player.hp, "/", st.player.max_hp, "LV", st.player.level)


def play_act4(rng, deny_overtime=False, prep_between=True):
    """Quest 4 on top of quest 3 (fight route). deny_overtime: hack the dock controller first."""
    from tos.engine.content import check
    from tos.engine.game import place
    st = play_act3(rng)
    assert not check(C.city["nodes"]["central_ave"].get("unlocked_if"), st)
    talk("mags", st, 0, 0)  # "Let's take down the relay."
    assert st.quests["service_interruption"] == 2
    node = C.city["nodes"]["central_ave"]
    assert check(node.get("unlocked_if"), st)
    if prep_between:
        prep(st)
    place(st, C, node["location"], node["spawn"])
    ave = Location(st.location, st, C)
    assert not ave.door_open(ave.get("yard_gate"))
    for _ in range(4):  # the street drone is awake; Ruth is at (18,4)
        events = []
        walk_to(ave, 17, 4, events)
        if ("combat",) in events:
            assert fight(ave, rng) == "won", st.player.hp
            continue
        break
    assert ("dialogue", "ruth_relay") in ave.player_move(1, 0)
    talk("ruth_relay", st, 1, 0, 0)  # Wits 3: the intel, then the plan
    assert "fence_cut" in st.flags and st.player.has("thermite") and st.quests["service_interruption"] == 3
    assert any(n[0] == "Relay yard intel" for n in st.notes)
    ave.player_move(0, -1)  # Ruth's stash (17,3)
    assert "central_ave:optout_stash" in st.taken
    if prep_between:
        prep(st)
    assert exit_via(ave, 22, 4, 1, 0, rng) == "location" and st.location == "relay_yard"
    yard = Location(st.location, st, C)
    yard.update_rules()
    if deny_overtime:
        events = []
        walk_to(yard, 2, 7, events)
        assert ("combat",) not in events, "the dock controller is outside the boss's aggro"
        assert ("hack", "dock_controller") in yard.player_move(1, 0)
        yard.terminal_result("dock_controller", True)
        assert "pickers_off" in st.flags
    if prep_between:
        prep(st)
    for _ in range(4):
        events = []
        walk_to(yard, 12, 5, events)
        if yard.awake_enemies() and ("combat",) in events or yard.awake_enemies():
            assert fight(yard, rng) == "won", st.player.hp
        if "relay_yard:fulfillment" in st.taken:
            break
    assert "relay_yard:fulfillment" in st.taken
    assert "overtime" in st.flags, "the boss passed half HP"
    pickers = [k for k in ("relay_yard:picker1", "relay_yard:picker2") if k in st.taken]
    assert (not pickers) if deny_overtime else len(pickers) == 2
    # the cabinet (12,2): stand where the boss stood
    events = []
    walk_to(yard, 12, 3, events)
    yard.player_move(0, -1)
    assert "relay_down" in st.flags and not st.player.has("thermite")
    assert st.quests["service_interruption"] == "done" and st.quests["teo"] == 5
    assert check(C.city["nodes"]["uptown"].get("unlocked_if"), st)
    place(st, C, "noda", "city")
    d = talk("mags", st)
    assert d.node_id == "blind"
    return st


def test_service_interruption_overtime():
    st = play_act4(random.Random(5))
    print("  act 4 end (overtime): HP", st.player.hp, "/", st.player.max_hp, "LV", st.player.level)


def test_service_interruption_denied():
    st = play_act4(random.Random(9), deny_overtime=True)
    print("  act 4 end (overtime denied): HP", st.player.hp, "/", st.player.max_hp, "LV", st.player.level)


def test_boss_phase_fires_once():
    from tos.engine.game import place
    st, _ = new_game(C, STATS)
    place(st, C, "relay_yard", "gate")
    yard = Location("relay_yard", st, C)
    cb = Combat(yard, random.Random(1))
    boss = yard.get("fulfillment")
    boss.hp = boss.max_hp // 2 + 1
    assert cb.phases(boss) == [] and "overtime" not in st.flags
    boss.hp = boss.max_hp // 2 - 1
    msgs = cb.phases(boss)
    assert "overtime" in st.flags and any("overtime" in m for m in msgs)
    assert {e.id for e in yard.awake_enemies()} >= {"picker1", "picker2"}, "pickers join mid-fight"
    assert cb.phases(boss) == [], "a phase fires only once"


def test_ruth_needs_a_voucher():
    from tos.engine.game import place
    st, _ = new_game(C, {**STATS, "Charm": 2})
    place(st, C, "noda", "city")
    d = Dialogue("ruth", st, C)
    labels = [(o[0], o[1]) for o in d.options()]
    assert not any("Delia" in l for l, _ in labels), "no Delia option without meeting her"
    assert any("CHARM" in l and not ok for l, ok in labels), "Charm option shown but locked"
    d.choose(1)  # "South End."
    assert "ruth_ok" not in st.flags


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
