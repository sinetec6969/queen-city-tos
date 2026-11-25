"""Headless UI playthrough of the opening act at 80x24.

Run: python tests/test_ui.py [--shots DIR]   (saves SVG screenshots when --shots is given)
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["QCTS_SAVE_DIR"] = tempfile.mkdtemp()

from tos.ui.app import QCApp
from tos.ui.screens import (CityScreen, DialogueScreen, HackScreen, LocationScreen,
                            ProfileScreen, TipScreen, WristLinkScreen)

TIPS_SEEN = []

SHOTS = None
if "--shots" in sys.argv:
    SHOTS = Path(sys.argv[sys.argv.index("--shots") + 1])
    SHOTS.mkdir(parents=True, exist_ok=True)


async def shot(app, name):
    if SHOTS:
        app.save_screenshot(filename=f"{name}.svg", path=str(SHOTS))


async def press(pilot, app, *keys):
    await pilot.press(*keys)
    await pilot.pause()
    while isinstance(app.screen, TipScreen):
        TIPS_SEEN.append(app.screen.tid)
        if SHOTS and app.screen.tid in ("welcome", "combat", "complete"):
            await shot(app, f"tip_{app.screen.tid}")
        await pilot.press("enter")
        await pilot.pause()


async def walk(pilot, app, tx, ty, limit=60):
    """Walk to a tile with arrow keys, pathing with the engine's BFS."""
    for _ in range(limit):
        scr = app.screen
        if not isinstance(scr, LocationScreen) or scr.combat or scr.busy:
            return
        px, py = app.state.pos
        if (px, py) == (tx, ty):
            return

        class P:
            x, y = px, py
        step = scr.loc.step_toward(P, tx, ty) if max(abs(px - tx), abs(py - ty)) > 1 else (tx, ty)
        if step is None:
            return
        dx, dy = step[0] - px, step[1] - py
        if dx and dy:
            if not scr.loc.blocked(px + dx, py):
                dy = 0
            else:
                dx = 0
        key = {(1, 0): "right", (-1, 0): "left", (0, 1): "down", (0, -1): "up"}[(dx, dy)]
        await press(pilot, app, key)


async def fight(pilot, app):
    for _ in range(40):
        scr = app.screen
        if not isinstance(scr, LocationScreen) or not scr.combat:
            return
        cb = scr.combat
        t = cb.target()
        if app.state.player.hp < 12 and cb.best_heal() and cb.ap >= 2:
            await press(pilot, app, "u")
        elif t and cb.in_range(t) and cb.ap >= cb.attack_cost():
            await press(pilot, app, "f")
        elif t and not cb.in_range(t) and cb.ap >= 1:
            px, py = app.state.pos
            dx = (t.x > px) - (t.x < px)
            dy = (t.y > py) - (t.y < py)
            await press(pilot, app, ("right" if dx > 0 else "left") if dx and not scr.loc.blocked(px + dx, py) else ("down" if dy > 0 else "up"))
        else:
            await press(pilot, app, "space")
        await pilot.pause()


async def main():
    app = QCApp(seed=11)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        await shot(app, "01_title")
        await press(pilot, app, "n")
        await pilot.pause()
        assert isinstance(app.screen, ProfileScreen)
        await shot(app, "02_profile")
        await press(pilot, app, "enter")
        await pilot.pause()
        await shot(app, "03_intro")
        await press(pilot, app, "escape")
        await pilot.pause()
        assert isinstance(app.screen, LocationScreen)
        await shot(app, "04_apartment")
        # tablet, then tire iron
        await walk(pilot, app, 3, 2)
        await press(pilot, app, "down")
        await walk(pilot, app, 6, 2)
        await press(pilot, app, "up")
        await pilot.pause()
        assert app.state.player.has("tire_iron")
        # equip via WristLink
        await press(pilot, app, "tab")
        await pilot.pause()
        assert isinstance(app.screen, WristLinkScreen)
        await press(pilot, app, "right")
        await pilot.pause()
        await shot(app, "05_wristlink")
        scr = app.screen
        idx = scr.items().index("tire_iron")
        for _ in range(idx):
            await press(pilot, app, "down")
        await press(pilot, app, "enter")
        await press(pilot, app, "right")  # QUESTS tab
        await shot(app, "05b_quests")
        await press(pilot, app, "tab")
        await pilot.pause()
        assert app.state.player.weapon == "tire_iron"
        # supplies: fridge (8,1) and drawer (13,1)
        await walk(pilot, app, 8, 2)
        await press(pilot, app, "up")
        await walk(pilot, app, 13, 2)
        await press(pilot, app, "up")
        assert app.state.player.has("sweet_tea") and app.state.player.has("tinfoil")
        await press(pilot, app, "question_mark")
        assert not isinstance(app.screen, TipScreen)
        # talk to LUMEN HOME (11,9) from (11,8)
        await walk(pilot, app, 11, 8)
        await press(pilot, app, "down")
        await pilot.pause()
        assert isinstance(app.screen, DialogueScreen)
        await shot(app, "06_dialogue")
        await press(pilot, app, "3")  # leave (Wits 2: diag locked) -> options: accept, decline, diag(locked), teo(locked), where, leave
        await pilot.pause()
        if isinstance(app.screen, DialogueScreen):
            await press(pilot, app, "6")
            await pilot.pause()
        assert isinstance(app.screen, LocationScreen)
        # terminal (20,9) from (20,8)
        await walk(pilot, app, 20, 8)
        await press(pilot, app, "down")
        await pilot.pause()
        assert isinstance(app.screen, HackScreen)
        hs = app.screen
        wrong = next(w for w in hs.hack.words if w != hs.hack.password)
        await press(pilot, app, *wrong.lower(), "enter")
        await pilot.pause()
        await shot(app, "07_hack")
        await press(pilot, app, *hs.hack.password.lower(), "enter")
        await pilot.pause()
        await press(pilot, app, "space")
        await pilot.pause()
        assert "door_unlocked" in app.state.flags
        scr = app.screen
        assert isinstance(scr, LocationScreen) and scr.combat, "TIDY should attack"
        await press(pilot, app, "a")
        await pilot.pause()
        await shot(app, "08_combat_lockon")
        await press(pilot, app, "escape")
        await fight(pilot, app)
        await shot(app, "09_after_fight")
        assert app.state.player.hp > 0, "died to TIDY"
        await press(pilot, app, "s")
        # out the front door
        await walk(pilot, app, 19, 9)
        await press(pilot, app, "down")
        await pilot.pause()
        assert app.state.location == "lumen_hall"
        assert "tutorial_done" in app.state.flags, sorted(f for f in app.state.flags if f.startswith("tut:"))
        await shot(app, "10_hallway")
        # Pruitt at (3,2): approach from (4,2)
        await walk(pilot, app, 9, 1)
        await walk(pilot, app, 4, 1)
        await walk(pilot, app, 4, 2)
        await press(pilot, app, "left")
        await pilot.pause()
        if isinstance(app.screen, DialogueScreen):
            await press(pilot, app, "1")
            await press(pilot, app, "1")
            await pilot.pause()
            await shot(app, "11_pruitt")
            await press(pilot, app, "2")
            await pilot.pause()
        # stairs (21,5) from (21,4), fighting the drone on the way
        for _ in range(4):
            await walk(pilot, app, 21, 4)
            await fight(pilot, app)
        await press(pilot, app, "down")
        assert app.state.location == "south_end_street", app.state.location
        assert app.state.quests["terms"] == "done"
        await shot(app, "12_street")

        # ---- QUEST 2: Last Mile ----
        # tinfoil first (keeps the Greeter asleep), then Biscuit at (6,6) from (6,5)
        await press(pilot, app, "tab")
        scr = app.screen
        await press(pilot, app, "right")
        for _ in range(scr.items().index("tinfoil")):
            await press(pilot, app, "down")
        await press(pilot, app, "enter")
        await press(pilot, app, "tab")
        await walk(pilot, app, 6, 5)
        await fight(pilot, app)
        await walk(pilot, app, 6, 5)
        await press(pilot, app, "down")
        assert isinstance(app.screen, DialogueScreen)
        await press(pilot, app, "1")
        await press(pilot, app, "1")
        assert app.state.companion == "biscuit"
        await walk(pilot, app, 10, 6)
        await shot(app, "13_biscuit")
        for _ in range(4):
            await walk(pilot, app, 22, 5)
            await fight(pilot, app)
        await press(pilot, app, "right")
        assert isinstance(app.screen, CityScreen), type(app.screen)
        await shot(app, "14_city")
        await press(pilot, app, "down")  # South End -> Dilworth
        await press(pilot, app, "enter")
        assert app.state.location == "dilworth", app.state.location
        # Kayla at (2,1)
        await walk(pilot, app, 2, 2)
        await press(pilot, app, "up")
        assert isinstance(app.screen, DialogueScreen)
        await press(pilot, app, "1")  # the park
        await press(pilot, app, "1")  # Biscuit's delivery
        await shot(app, "15_kayla")
        await press(pilot, app, "1")  # enjoy it
        await press(pilot, app, "1")  # leave
        assert app.state.quests["order_shipped"] == "done"
        # stealth route: hack the yard controller at (2,6)
        await walk(pilot, app, 2, 5)
        await press(pilot, app, "down")
        assert isinstance(app.screen, HackScreen)
        await press(pilot, app, *app.screen.hack.password.lower(), "enter")
        await press(pilot, app, "space")
        assert "mowers_off" in app.state.flags and app.state.quests["mow_better"] == 2
        await walk(pilot, app, 2, 2)
        await press(pilot, app, "up")
        await press(pilot, app, "1")  # mowers handled
        await press(pilot, app, "1")  # thanks
        await press(pilot, app, "1")  # leave
        assert app.state.quests["mow_better"] == "done"
        await walk(pilot, app, 12, 4)
        await shot(app, "16_park")
        await walk(pilot, app, 22, 4)
        await press(pilot, app, "right")
        assert app.state.location == "plaza_midwood"
        assert app.state.quests["last_mile"] == "done"
        # Delia at (6,1) from (6,2)
        await walk(pilot, app, 6, 2)
        await press(pilot, app, "up")
        await press(pilot, app, "2")  # my brother
        await shot(app, "17_delia")
        await press(pilot, app, "1")
        await press(pilot, app, "3")  # leave
        assert app.state.quests["analog_only"] == 1
        # Hollis at (13,2) from (13,3)
        await walk(pilot, app, 13, 3)
        await press(pilot, app, "up")
        cells = app.state.player.cells
        await press(pilot, app, "2")  # med-gummy
        await shot(app, "18_shop")
        await press(pilot, app, "5")
        assert app.state.player.cells == cells - 5
        await shot(app, "19_midwood")
        print("tips shown:", TIPS_SEEN)
        print("UI playthrough OK. HP", app.state.player.hp, "/", app.state.player.max_hp,
              "LV", app.state.player.level, "signal", int(app.state.player.signal))


if __name__ == "__main__":
    asyncio.run(main())
