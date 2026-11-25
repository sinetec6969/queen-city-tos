"""Line-mode (packet radio) frontend: scripted playthrough of quests 1-6 using text
commands only, plus entry-point checks. Prints reply sizes and an airtime estimate.

Run: python tests/test_line.py
"""
import os
import random
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["QCTS_SAVE_DIR"] = tempfile.mkdtemp()

from tos.engine.content import get_content
from tos.line.__main__ import allowed, base_call
from tos.line.session import Session

C = get_content()
REPLIES: list[bytes] = []
DIRS = {(0, -1): "n", (0, 1): "s", (1, 0): "e", (-1, 0): "w"}


def send(sess, cmd):
    reply = sess.handle(cmd)
    data = reply.encode("utf-8")
    assert data.isascii(), f"non-ASCII reply to {cmd!r}: {reply!r}"
    assert b"\x1b" not in data and b"\r" not in data, repr(reply)
    for line in reply.split("\n"):
        assert len(line) <= 100, f"line too long ({len(line)}): {line!r}"
    REPLIES.append(data)
    return reply


def path(loc, start, goal):
    """Orthogonal BFS over passable tiles; the goal tile itself may be anything walkable."""
    prev, q = {start: None}, deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            break
        for d in DIRS:
            nxt = (cur[0] + d[0], cur[1] + d[1])
            if nxt not in prev and not loc.blocked(*nxt):
                prev[nxt] = cur
                q.append(nxt)
    if goal not in prev:
        return None
    steps, cur = [], goal
    while prev[cur] is not None:
        steps.append((cur[0] - prev[cur][0], cur[1] - prev[cur][1]))
        cur = prev[cur]
    return steps[::-1]


def walk(sess, tx, ty, limit=40):
    """Walk with run-length commands (e.g. E5), replanning after each one."""
    for _ in range(limit):
        if sess.mode != "explore" or tuple(sess.state.pos) == (tx, ty):
            return
        steps = path(sess.loc, tuple(sess.state.pos), (tx, ty))
        assert steps, f"no path to {tx},{ty} from {sess.state.pos} in {sess.loc.id}"
        n = 1
        while n < len(steps) and steps[n] == steps[0] and n < 9:
            n += 1
        send(sess, f"{DIRS[steps[0]]}{n if n > 1 else ''}")


def fight(sess, limit=80):
    for _ in range(limit):
        if sess.mode not in ("combat", "lockon"):
            return
        cb, p = sess.combat, sess.state.player
        t = cb.target()
        before = (cb.ap, cb.round, tuple(sess.state.pos), t.hp if t else 0)
        if p.hp < p.max_hp * 0.4 and cb.best_heal() and cb.ap >= 2:
            send(sess, "u")
        elif t and cb.in_range(t) and cb.ap >= cb.attack_cost():
            send(sess, "f")
        elif t and not cb.in_range(t) and cb.ap >= 1:
            px, py = sess.state.pos
            dx = (t.x > px) - (t.x < px)
            dy = (t.y > py) - (t.y < py)
            move = (dx, 0) if dx and not sess.loc.blocked(px + dx, py) else (0, dy or 1)
            send(sess, DIRS[move])
        else:
            send(sess, ".")
        if sess.mode == "combat" and sess.combat is cb:
            t2 = cb.target()
            if (cb.ap, cb.round, tuple(sess.state.pos), t2.hp if t2 else 0) == before:
                send(sess, ".")  # the action didn't take (blocked, out of ammo): end the turn
    raise AssertionError("fight did not finish")


def talk(sess, *choices):
    for ch in choices:
        if sess.mode != "dialogue":
            return
        send(sess, str(ch))


def leave(sess):
    """Pick the last option until the conversation ends."""
    for _ in range(6):
        if sess.mode != "dialogue":
            return
        send(sess, str(len(sess.dlg.options())))


def heal(sess, frac=0.6):
    p = sess.state.player
    for iid in ("med_gummy", "sweet_tea"):
        for _ in range(10):
            if p.hp >= p.max_hp * frac or not p.has(iid):
                break
            n = p.inventory[iid]
            send(sess, f"use {iid}")
            assert p.inventory.get(iid, 0) < n, f"use {iid} did nothing"


def new_session(seed=11, slot="TEST1"):
    s = Session(C, random.Random(seed), slot=slot)
    REPLIES.append(s.start().encode())
    return s


def test_quests_1_to_6():
    s = new_session()
    send(s, "n")
    assert s.mode == "profile"
    send(s, "9 9 9 9 9 9")  # rejected
    send(s, "3 3 3 2 2 2")
    send(s, "ok")
    assert s.mode == "intro"
    send(s, "")
    send(s, "x")
    assert s.mode == "explore" and s.loc.id == "lumen_1412"
    send(s, "m")
    send(s, "l")
    send(s, "zork")  # unknown command
    # tablet (3,3), closet (6,1)
    walk(s, 3, 2)
    send(s, "s")
    assert s.state.quests["teo"] == 1
    walk(s, 6, 2)
    send(s, "n")
    assert s.state.player.has("tire_iron")
    send(s, "i")
    send(s, "eq tire")
    assert s.state.player.weapon == "tire_iron"
    send(s, "q")
    # supplies: fridge (8,1), drawer (13,1)
    walk(s, 8, 2)
    send(s, "n")
    walk(s, 13, 2)
    send(s, "n")
    assert s.state.player.has("sweet_tea") and s.state.player.has("tinfoil")
    send(s, "?")
    # LUMEN HOME (11,9)
    walk(s, 11, 8)
    send(s, "s")
    assert s.mode == "dialogue"
    send(s, "3")  # Wits-locked option: refused, options reprinted
    assert s.mode == "dialogue"
    leave(s)
    assert s.mode == "explore"
    # terminal (20,9): wrong word, then the password
    walk(s, 20, 8)
    send(s, "s")
    assert s.mode == "hack"
    h = s.hack
    send(s, "notaword")
    send(s, next(w for w in h.words if w != h.password).lower())
    send(s, "d")
    send(s, h.password)
    assert "door_unlocked" in s.state.flags
    assert s.mode == "combat", "TIDY should attack"
    send(s, "a")
    assert s.mode == "lockon"
    send(s, "x")
    send(s, "i")  # refused in combat
    fight(s)
    assert s.state.player.hp > 0 and s.mode == "explore"
    send(s, "save")
    walk(s, 19, 9)
    send(s, "s")
    assert s.state.location == "lumen_hall"
    assert "tutorial_done" in s.state.flags, sorted(f for f in s.state.flags if f.startswith("tut:"))
    # Pruitt (3,2) from (4,2)
    walk(s, 9, 1)
    walk(s, 4, 1)
    walk(s, 4, 2)
    send(s, "w")
    talk(s, 1, 1, 2)
    leave(s)
    assert s.state.quests["last_mile"] == 1
    # stairwell (21,5) from (21,4); fight the drone on the way
    for _ in range(4):
        walk(s, 21, 4)
        fight(s)
    send(s, "s")
    assert s.state.location == "south_end_street", s.state.location
    assert s.state.quests["terms"] == "done"
    # perks: a point per level, spent with PERK
    r = send(s, "perks")
    assert "Perk points: " in r and s.state.player.perk_points >= 1
    send(s, "perks all")
    send(s, "perk thick")
    assert "thick_skin" in s.state.player.perks

    # ---- quest 2: Last Mile ----
    send(s, "use tinfoil")
    walk(s, 6, 5)
    fight(s)
    walk(s, 6, 5)
    send(s, "s")
    assert s.mode == "dialogue"
    talk(s, 1, 1)
    assert s.state.companion == "biscuit"
    walk(s, 10, 6)
    for _ in range(4):
        walk(s, 22, 5)
        fight(s)
    send(s, "e")
    assert s.mode == "city"
    send(s, "x 2")
    send(s, str(s.city_order.index("speedway") + 1))  # not built yet
    send(s, str(s.city_order.index("dilworth") + 1))
    assert s.state.location == "dilworth", s.state.location
    # Kayla (2,1)
    walk(s, 2, 2)
    send(s, "n")
    talk(s, 1, 1, 1, 1)
    assert s.state.quests["order_shipped"] == "done"
    # stealth route: yard controller (2,6)
    walk(s, 2, 5)
    send(s, "s")
    assert s.mode == "hack"
    send(s, s.hack.password)
    assert "mowers_off" in s.state.flags and s.state.quests["mow_better"] == 2
    walk(s, 2, 2)
    send(s, "n")
    talk(s, 1, 1, 1)
    assert s.state.quests["mow_better"] == "done"
    walk(s, 12, 4)
    walk(s, 22, 4)
    send(s, "e")
    assert s.state.location == "plaza_midwood"
    assert s.state.quests["last_mile"] == "done"
    # Delia (6,1), Hollis's shop (13,2)
    walk(s, 6, 2)
    send(s, "n")
    talk(s, 2, 1)
    leave(s)
    assert s.state.quests["analog_only"] == 1
    walk(s, 13, 3)
    send(s, "n")
    cells = s.state.player.cells
    talk(s, 2)
    leave(s)
    assert s.state.player.cells == cells - 5

    # ---- quest 3: Analog Only (stealth route: both terminals) ----
    walk(s, 22, 7)
    send(s, "e")
    assert s.mode == "city"
    send(s, str(s.city_order.index("noda") + 1))
    assert s.state.location == "noda"
    walk(s, 6, 4)
    send(s, "s")
    talk(s, 1, 1)  # Delia vouches
    assert "ruth_ok" in s.state.flags
    walk(s, 10, 3)
    send(s, "e")
    talk(s, 1, 1, 1)
    assert s.state.quests["analog_only"] == 2
    walk(s, 3, 4)
    send(s, "n")
    send(s, "use tinfoil")
    walk(s, 1, 4)
    send(s, "w")
    send(s, str(s.city_order.index("blue_line") + 1))
    assert s.state.location == "lynx_36th"
    for _ in range(5):  # station control (20,5) from (19,5); the platform fight comes to you
        walk(s, 19, 5)
        fight(s)
    send(s, "e")
    assert s.mode == "hack"
    send(s, s.hack.password)
    assert "train_open" in s.state.flags
    for _ in range(3):
        walk(s, 12, 6)
        fight(s)
    send(s, "s")
    assert s.state.location == "lynx_train"
    send(s, "l")
    walk(s, 20, 5)  # operator console (21,5)
    send(s, "e")
    assert s.mode == "hack"
    send(s, s.hack.password)
    assert "service_ended" in s.state.flags
    walk(s, 9, 6)  # Dante (9,7)
    send(s, "s")
    talk(s, 1, 1, 1)
    assert s.state.player.has("faraday_drive")
    walk(s, 1, 2)
    assert s.mode == "explore", "PXU-1 stays off shift"
    send(s, "w")
    walk(s, 1, 3)
    send(s, "w")
    send(s, str(s.city_order.index("noda") + 1))
    walk(s, 10, 3)
    send(s, "e")
    talk(s, 1, 1, 1, 1)
    assert s.state.quests["analog_only"] == "done" and s.state.quests["service_interruption"] == 1
    assert "lynx_train:pxu" not in s.state.taken

    # ---- quest 4: Service Interruption (overtime denied at the dock controller) ----
    send(s, "e")  # Mags again
    talk(s, 1, 1)
    assert s.state.quests["service_interruption"] == 2
    heal(s)
    walk(s, 1, 4)
    send(s, "w")
    send(s, str(s.city_order.index("central_ave") + 1))
    assert s.state.location == "central_ave"
    for _ in range(4):
        walk(s, 17, 4)
        fight(s)
    send(s, "e")  # Ruth
    talk(s, 1, 1, 1)
    assert s.state.player.has("thermite")
    send(s, "n")  # stash
    heal(s)
    for _ in range(3):
        walk(s, 22, 4)
        fight(s)
    send(s, "e")
    assert s.state.location == "relay_yard"
    walk(s, 2, 7)
    send(s, "e")  # dock controller
    assert s.mode == "hack"
    send(s, s.hack.password)
    assert "pickers_off" in s.state.flags
    heal(s, 0.9)
    for _ in range(6):
        walk(s, 12, 5)
        fight(s)
        if "relay_yard:fulfillment" in s.state.taken:
            break
    assert "relay_yard:fulfillment" in s.state.taken
    walk(s, 12, 3)
    send(s, "n")  # the cabinet
    assert "relay_down" in s.state.flags and s.state.quests["service_interruption"] == "done"
    walk(s, 1, 4)
    send(s, "w")
    for _ in range(3):
        walk(s, 1, 3)
        fight(s)
    send(s, "w")
    send(s, str(s.city_order.index("noda") + 1))
    walk(s, 10, 3)
    send(s, "e")
    assert s.mode == "dialogue" and s.dlg.node_id == "blind"

    # ---- quest 5: Scheduled Downtime (prep level) ----
    talk(s, 1, 1)  # "Where do we go in from?"
    assert s.state.quests["scheduled_downtime"] == 1
    walk(s, 1, 4)
    send(s, "w")
    send(s, str(s.city_order.index("uptown") + 1))
    assert s.state.location == "third_ward" and s.state.quests["scheduled_downtime"] == 2
    p = s.state.player
    hp_max = p.max_hp
    walk(s, 10, 4)
    send(s, "s")  # Doc
    talk(s, 2, 1, 1, 1, 2)
    assert p.max_hp == hp_max + 5 and p.hp == p.max_hp
    walk(s, 18, 4)
    send(s, "e")  # Priya
    talk(s, 2, 1)  # listening: Wits +1
    assert "trained" in s.state.flags
    walk(s, 19, 1)
    send(s, "e")  # Ruth
    talk(s, 1 if p.has("nail_gun") else 2, 1)
    assert p.has("nailer_mk2")
    send(s, "eq ruth")
    assert p.weapon == "nailer_mk2"
    walk(s, 3, 3)
    send(s, "s")  # Hollis
    talk(s, 1, 1, 6)  # two Rocket Teas, leave
    walk(s, 22, 7)
    send(s, "e")
    assert s.state.location == "bearden_park"
    for target, cmd in (((13, 2), "n"), ((2, 4), "e"), ((21, 3), "e")):
        for _ in range(4):
            walk(s, *target)
            fight(s)
        send(s, cmd)
        if s.mode == "hack":
            send(s, s.hack.password)
    assert p.has("breaker_bar") and "lockers_open" in s.state.flags
    assert s.state.quests["scheduled_downtime"] == 3
    walk(s, 1, 3)
    send(s, "w")
    walk(s, 10, 2)
    send(s, "n")  # Mags
    talk(s, 1, 1)
    assert s.state.quests["scheduled_downtime"] == "done"

    # ---- quest 6: Rate Your Experience (both waves, one star) ----
    heal(s, 0.95)
    walk(s, 16, 1)
    send(s, "n")  # the back door
    assert s.state.location == "tower_dock"
    for _ in range(4):
        walk(s, 3, 4)
        fight(s)
    send(s, "s")  # dock office: badge
    assert p.has("service_badge")
    heal(s, 0.95)
    for _ in range(4):
        walk(s, 22, 4)
        fight(s)
    send(s, "e")
    assert s.state.location == "the_crown"
    walk(s, 10, 4)
    send(s, "s")  # Teo
    talk(s, 1, 1)
    walk(s, 11, 2)
    send(s, "n")  # the screens
    talk(s, 2, 1, 2, 1)  # Teo on the screens, rate, one star
    assert "rated" in s.state.flags
    heal(s, 0.95)
    for _ in range(6):
        walk(s, 11, 4)
        fight(s)
        if "concierge_down" in s.state.flags:
            break
    assert "concierge_down" in s.state.flags
    walk(s, 10, 4)
    send(s, "s")
    talk(s, 1)  # Teo, freed
    assert s.state.quests["teo"] == "done"
    walk(s, 22, 3)
    send(s, "e")  # freight elevator
    assert s.state.location == "lake_norman" and s.state.quests["rate_your_experience"] == "done"
    # the chapter-two road: teaser -> lake map -> back to Charlotte
    walk(s, 1, 2)
    r = send(s, "w")
    assert s.mode == "city" and "LAKE NORMAN - MAP" in r
    r = send(s, str(s.city_order.index("mcguire") + 1))
    assert "isn't built yet" in r
    r = send(s, str(s.city_order.index("ln_charlotte") + 1))
    assert "CHARLOTTE - MAP" in r and s.state.location == "city:lake_norman"
    send(s, str(s.city_order.index("lake_norman") + 1))
    send(s, str(s.city_order.index("ln_shore") + 1))
    assert s.state.location == "lake_norman"
    send(s, "st")
    send(s, "notes")
    send(s, "notes 1")
    p = s.state.player
    print(f"  quest 6 end: HP {p.hp}/{p.max_hp} LV {p.level} cells {p.cells}")
    send(s, "bye")
    assert s.done
    # reconnect: same callsign resumes where chapter one ended
    s2 = new_session(slot="TEST1")
    send(s2, "c")
    assert s2.mode == "explore" and s2.state.location == "lake_norman"


def test_accept_game_over_and_reload():
    s = new_session(slot="TEST2")
    send(s, "n")
    send(s, "ok")
    send(s, "x")
    walk(s, 11, 8)
    send(s, "s")
    send(s, "1")  # Accept
    send(s, "2")
    assert s.mode == "gameover"
    send(s, "l")
    assert s.mode == "explore" and s.state.location == "lumen_1412"


def test_tutorial_off_and_new_game_confirm():
    s = new_session(slot="TEST3")
    send(s, "n")
    send(s, "o")
    send(s, "ok")
    send(s, "x")
    assert "tutorial" not in s.state.flags
    send(s, "bye")
    s = new_session(slot="TEST3")
    send(s, "n")
    assert s.mode == "title", "a new game over a save needs confirmation"
    send(s, "new")
    assert s.mode == "profile"


def test_item_names_players_type():
    s = new_session(slot="TEST4")
    send(s, "n")
    send(s, "ok")
    send(s, "x")
    p = s.state.player
    p.give("sweet_tea")
    p.give("med_gummy")
    p.hp = 5
    for cmd, iid in (("use tea", "sweet_tea"), ("use gummy", "med_gummy")):
        n = p.inventory[iid]
        send(s, cmd)
        assert p.inventory.get(iid, 0) == n - 1, cmd


def test_control_chars_never_echo():
    """Hack prompts echo the typed word: control chars and ESC must never reach the air."""
    s = new_session(slot="TEST5")
    send(s, "n")
    send(s, "ok")
    send(s, "x")
    walk(s, 20, 8)
    send(s, "s")
    assert s.mode == "hack"
    for evil in ("\x1b[2J\x07agree", "\x00\x08\x7f" + "A" * 5000, "\x1b]0;pwned\x07", "caf\xe9\x9b\x1b"):
        reply = s.handle(evil)
        assert all(" " <= ch <= "~" or ch == "\n" for ch in reply), repr(reply)
        assert len(max(reply.split("\n"), key=len)) <= 100


def test_session_cap():
    import time
    sdir = tempfile.mkdtemp()
    env = dict(os.environ, QCTS_SAVE_DIR=sdir, QCTS_MAX_SESSIONS="2")
    holders = [subprocess.Popen([sys.executable, "-m", "tos.line", call], cwd=ROOT, env=env,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
               for call in ("KN4AAA", "KN4BBB")]
    try:
        for _ in range(100):
            if all((Path(sdir) / f"{c}.lock").exists() for c in ("KN4AAA", "KN4BBB")):
                break
            time.sleep(0.05)
        time.sleep(0.3)
        r = subprocess.run([sys.executable, "-m", "tos.line", "KN4CCC"], cwd=ROOT, env=env,
                           input=b"n\r", capture_output=True, timeout=30)
        assert b"is full" in r.stdout and b"RATING" not in r.stdout, r.stdout
    finally:
        for h in holders:
            h.stdin.write(b"bye\r")
            h.stdin.close()
            h.wait(timeout=10)
    r = subprocess.run([sys.executable, "-m", "tos.line", "KN4CCC"], cwd=ROOT, env=env,
                       input=b"q\r", capture_output=True, timeout=30)
    assert b"hello KN4CCC" in r.stdout, "room again once the others hang up"


def test_output_fits_ax25_mtu():
    """AX.25 sockets refuse writes larger than the interface MTU (kissattach sets it from the
    axports paclen). Found in the loopback lab: the game exited before its title screen."""
    import errno
    import tos.line.__main__ as M
    sent, real = [], M.os.write
    def mtu_write(fd, data, mtu=64):
        if len(data) > mtu:
            raise OSError(errno.EMSGSIZE, "Message too long")
        sent.append(bytes(data))
        return len(data)
    M.os.write = mtu_write
    try:
        out = M.Out(b"\r", 0)
        text = "x" * 50 + "\n" + "y" * 900 + "\nprompt>"
        out.write(text)
    finally:
        M.os.write = real
    assert b"".join(sent) == text.replace("\n", "\r").encode() + b" "
    assert max(len(c) for c in sent) <= 64 and out.chunk == 64


def test_callsigns_and_allowlist():
    assert base_call("kn4abc-7") == "KN4ABC"
    assert base_call("../etc") == "" and base_call("A") == ""
    f = Path(os.environ["QCTS_SAVE_DIR"]) / "allow.txt"
    f.write_text("KN4ABC  # James\nw1aw\n")
    assert allowed("KN4ABC", str(f)) and allowed("W1AW", str(f)) and not allowed("K1XYZ", str(f))
    assert not allowed("KN4ABC", str(f) + ".missing")
    assert allowed("ANY", None)


def run_cli(*args, stdin=b""):
    env = dict(os.environ, QCTS_SAVE_DIR=tempfile.mkdtemp())
    return subprocess.run([sys.executable, "-m", "tos.line", *args], input=stdin, cwd=ROOT,
                          env=env, capture_output=True, timeout=30)


def test_cli_cr_endings():
    r = run_cli("N0CALL-3", stdin=b"n\rok\r\nx\rl\rbye\r")
    out = r.stdout
    assert r.returncode == 0 and not r.stderr, r.stderr
    assert out.isascii() and b"\n" not in out and out.count(b"\r") > 10
    assert b"hello N0CALL" in out and b"Saved. 73." in out


def test_cli_allowlist_rejects():
    f = Path(tempfile.mkdtemp()) / "allow"
    f.write_text("KN4ABC\n")
    r = run_cli("K1XYZ", "--allow", str(f), stdin=b"n\r")
    assert b"invite-only" in r.stdout and b"RATING" not in r.stdout


def test_cli_hangup_saves():
    """The node hangs up (SIGHUP) mid-game: the unsaved move must still be on disk."""
    import json
    import signal
    import time
    sdir = tempfile.mkdtemp()
    env = dict(os.environ, QCTS_SAVE_DIR=sdir)
    p = subprocess.Popen([sys.executable, "-m", "tos.line", "KN4HUP"], cwd=ROOT, env=env,
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.stdin.write(b"n\rok\rx\r")
    p.stdin.flush()
    save = Path(sdir) / "KN4HUP.json"
    for _ in range(100):
        if save.exists():
            break
        time.sleep(0.05)
    start = json.loads(save.read_text())["pos"]
    p.stdin.write(b"e\r")
    p.stdin.flush()
    time.sleep(0.5)
    p.send_signal(signal.SIGHUP)
    _, err = p.communicate(timeout=10)
    assert not err, err
    assert json.loads(save.read_text())["pos"] == [start[0] + 1, start[1]]


def test_cli_broken_pipe_is_quiet():
    r = subprocess.run(f"printf 'n\\rok\\rx\\rbye\\r' | {sys.executable} -m tos.line KN4BRK | head -c 20",
                       shell=True, cwd=ROOT, capture_output=True, timeout=30,
                       env=dict(os.environ, QCTS_SAVE_DIR=tempfile.mkdtemp()))
    assert b"Traceback" not in r.stderr, r.stderr


def airtime(n: int) -> float:
    """Seconds from Enter to a complete reply over AX.25 connected mode at 1200 baud.
    Fitted to the loopback lab (2026-11-25: two direwolf modems, paclen 128, maxframe 4,
    TXDELAY 400 ms): 40 B -> 2.7 s, 174 B -> 3.8 s, 378 B -> 8.3 s, 945 B -> 18.1 s.
    Real UV-5R turnaround will add a little."""
    return 2.0 + 0.017 * n


def report():
    sizes = sorted(len(r) for r in REPLIES)
    p95 = sizes[int(len(sizes) * 0.95)]
    mean = sum(sizes) / len(sizes)
    print(f"  replies: {len(sizes)}  bytes mean {mean:.0f}  p95 {p95}  max {sizes[-1]}")
    print(f"  est. airtime @1200: mean {airtime(int(mean)):.1f}s  p95 {airtime(p95):.1f}s  max {airtime(sizes[-1]):.1f}s"
          f"  total {sum(airtime(n) for n in sizes) / 60:.1f} min")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    report()
