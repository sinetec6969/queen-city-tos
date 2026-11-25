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
        p = loc.state.player
        if p.hp < p.max_hp * 0.4 and cb.best_heal() and cb.ap >= 2:
            cb.use_item(cb.best_heal())  # heal first, like a player would, before spending AP on attacks
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


def play_act5(rng):
    """Quest 5: the safehouse (heal, train, upgrade, shop), then scout Bearden Park."""
    from tos.engine.content import check
    from tos.engine.game import place
    st = play_act4(rng)
    talk("mags", st, 0, 0)  # "Where do we go in from?"
    assert st.quests["scheduled_downtime"] == 1 and "noda:mags" in st.taken
    node = C.city["nodes"]["uptown"]
    assert check(node.get("unlocked_if"), st)
    place(st, C, node["location"], node["spawn"])
    ward = Location(st.location, st, C)
    ward.update_rules()
    assert st.quests["scheduled_downtime"] == 2
    assert not ward.door_open(ward.get("crown_door"))
    p = st.player
    hp_max = p.max_hp
    talk("doc", st, 1, 0, 0, 0, 1)  # tonic, then patch up, then leave
    assert p.max_hp == hp_max + 5 and p.hp == p.max_hp and "doc_tonic" in st.flags
    aim = p.stats["Aim"]
    talk("priya_ward", st, 0, 0)
    assert p.stats["Aim"] == aim + 1 and "trained" in st.flags
    d = talk("priya_ward", st)
    assert d.node_id == "after", "one lesson only"
    talk("ruth_ward", st, 0 if p.has("nail_gun") else 1, 0)
    assert p.has("nailer_mk2") and not p.has("nail_gun")
    tea = p.inventory.get("rocket_tea", 0)
    talk("hollis_ward", st, 0, 7)
    assert p.inventory.get("rocket_tea", 0) == tea + 1
    p.weapon = "nailer_mk2"
    exit_via(ward, 22, 7, 1, 0, rng)
    assert st.location == "bearden_park"
    park = Location(st.location, st, C)
    park.update_rules()
    for target, move in (((13, 2), (0, -1)), ((2, 4), (1, 0)), ((21, 3), (1, 0))):
        for _ in range(4):
            events = []
            walk_to(park, *target, events)
            if ("combat",) in events or park.awake_enemies() and park.check_aggro():
                assert fight(park, rng) == "won", p.hp
                continue
            break
        events = park.player_move(*move)
        if ("hack", "parcel_lockers") in events:
            park.terminal_result("parcel_lockers", True)
    assert p.has("breaker_bar") and "lockers_open" in st.flags and p.has("rocket_tea")
    assert st.quests["scheduled_downtime"] == 3 and st.quests["teo"] == 6
    assert any(n[0] == "The shuttle route" for n in st.notes)
    place(st, C, "third_ward", "park")
    talk("mags_ward", st, 0, 0)  # "I'm ready."
    assert st.quests["scheduled_downtime"] == "done" and "ready_for_crown" in st.flags
    assert talk("mags_ward", st).node_id == "after"
    return st


def test_scheduled_downtime():
    st = play_act5(random.Random(5))
    p = st.player
    print("  act 5 end: HP", p.hp, "/", p.max_hp, "LV", p.level, "Aim", p.stats["Aim"], "weapon", p.weapon)


def play_act6(rng, deny_both=False):
    """Quest 6: Loading Dock B, then the Crown. deny_both: hack the wellness desk and give the
    Charm review, so neither reinforcement wave comes."""
    from tos.engine.content import check
    st = play_act5(rng)
    ward = Location(st.location, st, C)
    assert ward.door_open(ward.get("crown_door"))
    prep(st)
    assert exit_via(ward, 16, 1, 0, -1, rng) == "location" and st.location == "tower_dock"
    assert st.quests["rate_your_experience"] == 1
    dock = Location(st.location, st, C)
    dock.update_rules()
    assert not dock.door_open(dock.get("service_elevator"))
    for target, move in (((3, 4), (0, 1)), ((10, 4), (0, 1))):
        for _ in range(4):
            events = []
            walk_to(dock, *target, events)
            if ("combat",) in events or dock.check_aggro():
                assert fight(dock, rng) == "won", st.player.hp
                continue
            break
        events = dock.player_move(*move)
        if ("hack", "wellness_desk") in events and deny_both:
            dock.terminal_result("wellness_desk", True)
    assert st.player.has("service_badge") and dock.door_open(dock.get("service_elevator"))
    assert ("wellness_off" in st.flags) == deny_both
    prep(st)
    assert exit_via(dock, 22, 4, 1, 0, rng) == "location" and st.location == "the_crown"
    assert st.quests["rate_your_experience"] == 2
    crown = Location(st.location, st, C)
    crown.update_rules()
    assert not crown.door_open(crown.get("freight_elevator"))
    talk("teo", st, 0, 0)
    assert "extremely fine" in C.dialogues["teo"]["nodes"]["hello"]["text"]
    if deny_both:
        st.player.stats["Charm"] = 4  # as if trained for it
        talk("concierge", st, 1, 0, 2, 0)  # Teo on the screens, rate, three stars + review
        assert "concierge_rattled" in st.flags and "rating_three" in st.flags
    else:
        talk("concierge", st, 1, 0, 1, 0)  # one star
        assert "rating_one" in st.flags
    assert "rated" in st.flags
    crown.update_rules()
    assert st.quests["rate_your_experience"] == 3
    prep(st)
    st.player.hp = st.player.max_hp  # boss fights start from full: the bot can't pace itself
    for _ in range(4):
        events = []
        walk_to(crown, 11, 4, events)
        if crown.awake_enemies():
            assert fight(crown, rng) == "won", st.player.hp
        if "concierge_down" in st.flags:
            break
    assert "concierge_down" in st.flags
    adds = [k for k in ("the_crown:crown_greeter1", "the_crown:crown_picker1", "the_crown:crown_picker2")
            if k in st.taken]
    assert (not adds) if deny_both else len(adds) == 3, adds
    talk("teo", st, 0)
    assert st.quests["teo"] == "done"
    assert exit_via(crown, 22, 3, 1, 0, rng) == "location"
    assert st.location == "lake_norman" and "chapter2" in st.flags
    assert st.quests["rate_your_experience"] == "done"
    assert check(C.city["nodes"]["lake_norman"].get("unlocked_if"), st)
    return st


def test_rate_your_experience_full():
    st = play_act6(random.Random(5))
    print("  act 6 end (both waves): HP", st.player.hp, "/", st.player.max_hp, "LV", st.player.level)


def test_rate_your_experience_denied():
    st = play_act6(random.Random(9), deny_both=True)
    print("  act 6 end (waves denied): HP", st.player.hp, "/", st.player.max_hp, "LV", st.player.level)


def test_five_stars_is_game_over():
    from tos.engine.game import place
    st, _ = new_game(C, STATS)
    place(st, C, "the_crown", "elevator")
    d = talk("concierge", st, 1, 0, 0)
    assert d.node_id == "five" and not d.done
    d.choose(1)  # "No. Wait."
    assert d.node_id == "rate"
    d.choose(0)
    d.choose(0)  # "Five stars. It's done."
    assert d.done and any(e[0] == "game_over" for e in d.events)


def test_every_enemy_has_its_own_cell():
    """Map chars are entity ids: two cells sharing an enemy char would die together."""
    for lid, loc in C.locations.items():
        for ch, spec in loc.get("legend", {}).items():
            if spec["type"] == "enemy":
                assert loc["map"].count(ch) == 1, (lid, ch)


def test_regions_and_gateways():
    from tos.engine import travel
    st, _ = new_game(C, STATS)
    assert travel.region_nodes(C, "charlotte")[0] == "lake_norman"
    lake = travel.region_nodes(C, "lake_norman")
    assert "ln_shore" in lake and "south_end" not in lake
    st.location = "city:lake_norman"
    assert travel.go(st, C, "lake_norman")["kind"] == "locked", "needs chapter2"
    st.flags.add("chapter2")
    r = travel.go(st, C, "lake_norman")
    assert r["kind"] == "region" and st.location == "city:ln_shore"
    assert travel.region_of(C, travel.current_node(st)) == "lake_norman"
    assert travel.go(st, C, "mcguire")["kind"] == "unbuilt"
    r = travel.go(st, C, "ln_shore")
    assert r["kind"] == "location" and st.location == "lake_norman"
    st.location = "city:ln_shore"
    assert travel.go(st, C, "ln_charlotte")["kind"] == "region" and st.location == "city:lake_norman"
    for a, b in C.city["links"]:
        assert travel.region_of(C, a) == travel.region_of(C, b), ("links stay inside a region", a, b)


def test_rating_flags_and_save_migration():
    from tos.engine.game import place
    from tos.engine.state import RATING_FLAGS, GameState
    st, _ = new_game(C, {**STATS, "Wits": 4})
    place(st, C, "the_crown", "elevator")
    talk("concierge", st, 1, 0, 3, 0)  # decline to rate
    assert "rating_declined" in st.flags and "wellness_off" in st.flags
    old = st.to_json()
    old["version"] = 1
    for flags, expect in ((["rated", "concierge_rattled"], "rating_three"), (["rated"], "rating_one"), ([], None)):
        old["flags"] = flags
        got = set(GameState.from_json(old).flags) & set(RATING_FLAGS)
        assert got == ({expect} if expect else set()), (flags, got)
    assert GameState.from_json(st.to_json()).flags == st.flags, "v2 saves round-trip untouched"


def test_perks():
    from tos.engine import perks
    from tos.engine.combat import use_aid
    from tos.engine.game import place
    from tos.engine.hack import for_terminal
    from tos.engine.state import GameState
    st, _ = new_game(C, {**STATS, "Aim": 4, "Charm": 3})
    p = st.player
    assert p.perk_points == 0
    st.add_xp(150)  # level 2
    assert p.level == 2 and p.perk_points == 1
    ok, ev = perks.take(st, C, "heavy_hands")  # Brawn 3: allowed
    assert ok and "heavy_hands" in p.perks and p.perk_points == 0
    assert not perks.take(st, C, "steady")[0], "no points left"
    p.perk_points = 20
    assert not perks.take(st, C, "heavy_hands")[0], "only once"
    assert not perks.take(st, C, "overclocked")[0], "needs level 6"
    assert "LEVEL 6" in perks.requirement_text(C.perks["overclocked"])
    # combat numbers: a melee target in the tutorial apartment
    place(st, C, "lumen_1412", "start")
    st.flags.add("tidy_awake")
    loc = Location("lumen_1412", st, C)
    tidy = loc.get("tidy")
    p.weapon = "nail_gun"
    p.give("nail_gun")
    cb = Combat(loc, random.Random(1))
    ranged, lock_cost = cb.hit_chance(tidy), cb.attack_cost(cb.parts(tidy)[0])
    perks.take(st, C, "steady")
    perks.take(st, C, "quick_lock")  # Aim 4
    assert cb.hit_chance(tidy) == min(95, ranged + 10)
    assert cb.attack_cost(cb.parts(tidy)[0]) == lock_cost - 1
    p.level = 6
    p.recalc()
    perks.take(st, C, "overclocked")
    assert Combat(loc, random.Random(1)).max_ap == 7
    hp = p.max_hp
    perks.take(st, C, "thick_skin")
    assert p.max_hp == hp + 10
    spec = {"length": 5, "words": 8}
    before = for_terminal(st, C, spec, random.Random(2))
    perks.take(st, C, "prompt_engineer")
    perks.take(st, C, "pattern_match")
    after = for_terminal(st, C, spec, random.Random(2))
    assert after.max_attempts == before.max_attempts + 1 and len(after.words) == len(before.words) - 2
    perks.take(st, C, "bedside_manner")  # Charm 3
    p.hp = 1
    p.give("med_gummy")
    use_aid(st, C, "med_gummy")
    assert p.hp == 1 + 8 + 5
    perks.take(st, C, "off_the_grid")
    sig = p.signal
    place(st, C, "south_end_street", "lobby")
    street = Location("south_end_street", st, C)
    street.player_move(0, 1)
    assert abs((p.signal - sig) - C.locations["south_end_street"]["signal_rate"] * 0.75) < 1e-9
    # saves from before perks get one point per level already earned
    d = st.to_json()
    d["version"], d["player"]["perks"], d["player"]["level"] = 2, [], 4
    d["player"].pop("perk_points")
    assert GameState.from_json(d).player.perk_points == 3


def test_crafting_and_mods():
    from tos.engine import crafting
    from tos.engine.game import place
    from tos.engine.state import GameState
    st, _ = new_game(C, STATS)
    p = st.player
    p.give("scrap", 9)
    p.give("duct_tape", 6)
    p.give("wire", 3)
    p.give("sugar", 3)
    p.give("tire_iron")
    p.weapon = "tire_iron"
    assert crafting.check_recipe(st, C, "nails") == "You need a workbench."
    place(st, C, "third_ward", "city")
    ok, ev = crafting.craft(st, C, "nails")
    assert ok and p.inventory["nails"] == 12 and p.inventory["scrap"] == 7
    assert crafting.craft(st, C, "sweet_tea")[0] and p.has("sweet_tea")
    # mods on the equipped melee weapon
    st.flags.add("tidy_awake")
    place(st, C, "lumen_1412", "start")
    loc = Location("lumen_1412", st, C)
    cb = Combat(loc, random.Random(1))
    tidy = loc.get("tidy")
    hit = cb.hit_chance(tidy)
    st.location = "third_ward"
    assert "ranged" in crafting.check_recipe(st, C, "rail_sight"), "wrong weapon kind"
    assert crafting.craft(st, C, "grip_tape")[0]
    assert "already" in crafting.check_recipe(st, C, "grip_tape")
    assert crafting.craft(st, C, "weighted_head")[0]
    assert crafting.weapon_label(st, C, "tire_iron") == "Tire Iron +2"
    w = crafting.weapon_stats(st, C, "tire_iron")
    assert w["acc"] == C.item("tire_iron").get("acc", 0) + 5 and w["dmg"] == [6, 9]
    assert C.item("tire_iron")["dmg"] == [4, 7], "content itself is never modified"
    st.location = "lumen_1412"
    assert Combat(loc, random.Random(1)).hit_chance(tidy) == min(95, hit + 5)
    p.give("duct_tape", 4)
    st.location = "third_ward"
    assert crafting.check_recipe(st, C, "grip_tape")  # already has it
    p.mods["tire_iron"] = ["grip_tape", "weighted_head"]
    p.weapon = "fists"
    assert "Equip a weapon" in crafting.check_recipe(st, C, "grip_tape")
    assert crafting.craft(st, C, "rocket_tea")[0] and p.has("rocket_tea")
    assert "Missing" in crafting.check_recipe(st, C, "rocket_tea"), "sugar used up"
    assert GameState.from_json(st.to_json()).player.mods == p.mods, "mods survive a save"
    for rid, r in C.recipes.items():
        for item in r["inputs"]:
            assert item in C.items, (rid, item)
        if "output" in r:
            assert r["output"]["item"] in C.items, rid


class ForcedRng(random.Random):
    """random() returns `roll`; choices() picks the encounter with id `pick`; counts draws."""
    def __init__(self, roll=0.0, pick=None):
        super().__init__(3)
        self.roll, self.pick, self.draws = roll, pick, 0
    def random(self):
        self.draws += 1
        return self.roll
    def choices(self, pool, weights=None, k=1):
        return [next(e for e in pool if e["id"] == self.pick)] if self.pick else super().choices(pool, weights, k=k)


def test_travel_encounters():
    from tos.engine import travel
    st, _ = new_game(C, STATS)
    st.flags |= {"act1_done", "reached_midwood"}
    st.location = "city:south_end"
    rng = ForcedRng(0.0)
    r = travel.go(st, C, "dilworth", rng)
    assert r["kind"] == "location" and st.location == "dilworth" and rng.draws == 0, "chapter one: no rolls at all"
    st.flags.add("chapter2")
    st.location = "city:dilworth"
    assert travel.go(st, C, "dilworth", ForcedRng(0.0, "charlotte_vending"))["events"][0][1].startswith("You head"), \
        "re-entering where you are isn't travel"
    st.location = "city:south_end"
    assert travel.go(st, C, "dilworth", ForcedRng(0.99))["events"][0][1].startswith("You head"), "roll missed"
    st.location = "city:south_end"
    r = travel.go(st, C, "dilworth", ForcedRng(0.0, "charlotte_vending"))
    assert "On the way to Dilworth" in r["events"][0][1] and st.player.has("sugar") and st.location == "dilworth"
    # ambush: fight on the roadside, then the exit continues to the destination
    for attempt in range(2):
        st.location = "city:south_end"
        st.player.level, st.player.hp_bonus = 6, 0  # encounters happen after chapter one
        st.player.recalc()
        st.player.hp = st.player.max_hp
        st.player.give("nail_gun")
        st.player.give("nails", 40)
        st.player.weapon = "nail_gun"
        r = travel.go(st, C, "plaza_midwood", ForcedRng(0.0, "charlotte_wellness_check"))
        assert ("combat",) in r["events"] and st.location == "roadside" and st.travel_dest == "plaza_midwood"
        road = Location("roadside", st, C)
        assert len(road.awake_enemies()) == 2, "enemies reset for every ambush"
        assert fight(road, random.Random(attempt)) == "won", st.player.hp
        assert exit_via(road, 22, 3, 1, 0) == "location"
        assert st.location == "plaza_midwood" and st.travel_dest is None
    assert travel.encounter_chance(st, C, "lake_norman") > travel.encounter_chance(st, C, "charlotte")
    st.player.signal = 100
    assert travel.encounter_chance(st, C, "charlotte") == 0.4
    for e in C.encounters:
        assert e.get("region", "charlotte") in C.city["regions"], e["id"]
        if e.get("ambush"):
            assert e["ambush"]["location"] in C.locations, e["id"]


def test_every_spawn_is_walkable():
    st, _ = new_game(C, STATS)
    for lid, loc in C.locations.items():
        L = Location(lid, st, C)
        for name, (x, y) in L.spawns.items():
            e = L.entity_at(x, y)
            assert not L.is_wall(x, y) and (e is None or L.passable(e)), (lid, name, (x, y))


def test_v06_save_loads():
    """A save written by 0.6.x (no perks, mods, hp_bonus or travel_dest; version 1) still loads."""
    from tos.engine.state import GameState
    st = play_act1(random.Random(7))
    d = st.to_json()
    for k in ("perks", "perk_points", "mods", "hp_bonus"):
        d["player"].pop(k)
    d.pop("travel_dest")
    d["version"] = 1
    st2 = GameState.from_json(d)
    p = st2.player
    assert p.perks == [] and p.mods == {} and p.hp_bonus == 0 and st2.travel_dest is None
    assert p.perk_points == p.level - 1 and st2.location == st.location and st2.flags == st.flags


def test_city_labels_fit_their_canvas():
    from tos.engine import travel
    for rid in C.city.get("regions", {}):
        reg = travel.region(C, rid)
        for nid in travel.region_nodes(C, rid):
            n = C.city["nodes"][nid]
            assert 0 <= n["y"] < reg["height"] and n["x"] + 2 + len(n["name"]) <= reg["width"], (rid, nid)


def test_stat_and_max_hp_effects():
    from tos.engine.content import apply_effects
    from tos.engine.state import STAT_CAP, GameState
    st, _ = new_game(C, {**STATS, "Grit": 5})
    hp = st.player.max_hp
    apply_effects([{"stat_up": "Grit"}, {"stat_up": "Grit"}, {"max_hp": 5}], st, C)
    assert st.player.stats["Grit"] == STAT_CAP and st.player.max_hp == hp + 4 + 5
    st.player.level += 1
    st.player.recalc()
    assert st.player.max_hp == hp + 4 + 5 + 5, "bonus survives level-ups"
    d = st.to_json()
    d["player"].pop("hp_bonus")
    assert GameState.from_json(d).player.hp_bonus == 0, "pre-0.5 saves still load"


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
