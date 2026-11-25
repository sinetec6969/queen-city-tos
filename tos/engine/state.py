"""Game state: the player, world flags, quests, and save/load."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

STATS = ["Brawn", "Grit", "Aim", "Wits", "Charm", "Luck"]
STAT_BLURBS = {
    "Brawn": "Melee damage.",
    "Grit": "Max HP. Shrugging things off.",
    "Aim": "Ranged hit chance.",
    "Wits": "Hacking attempts and XP gain.",
    "Charm": "Dialogue options and prices.",
    "Luck": "Crits, and which way surprises break.",
}
STAT_MIN, STAT_MAX, STAT_BUDGET = 1, 5, 15
STAT_CAP = 6  # training can push one past character creation's max
SAVE_VERSION = 1


@dataclass
class Player:
    name: str = "Dez Harlan"
    stats: dict = field(default_factory=lambda: {s: STAT_MIN for s in STATS})
    level: int = 1
    xp: int = 0
    hp: int = 0
    max_hp: int = 0
    signal: float = 0.0
    cells: int = 12
    inventory: dict = field(default_factory=dict)
    weapon: str = "fists"
    hp_bonus: int = 0  # permanent max-HP upgrades (the `max_hp` effect)

    def recalc(self) -> None:
        self.max_hp = 20 + 4 * self.stats["Grit"] + 5 * (self.level - 1) + self.hp_bonus
        self.hp = min(self.hp, self.max_hp)

    def xp_to_next(self) -> int:
        return 100 * self.level

    def has(self, item: str, n: int = 1) -> bool:
        return self.inventory.get(item, 0) >= n

    def give(self, item: str, n: int = 1) -> None:
        self.inventory[item] = self.inventory.get(item, 0) + n

    def take(self, item: str, n: int = 1) -> bool:
        if not self.has(item, n):
            return False
        self.inventory[item] -= n
        if self.inventory[item] <= 0:
            del self.inventory[item]
            if self.weapon == item:
                self.weapon = "fists"
        return True


@dataclass
class GameState:
    player: Player = field(default_factory=Player)
    location: str = "lumen_1412"
    pos: list = field(default_factory=lambda: [0, 0])
    flags: set = field(default_factory=set)
    taken: set = field(default_factory=set)  # "loc:entity" keys removed from the world
    quests: dict = field(default_factory=dict)  # quest id -> stage (int) or "done"
    notes: list = field(default_factory=list)  # [title, body] pairs shown in WristLink DATA
    log: list = field(default_factory=list)
    steps: int = 0
    companion: str | None = None
    companion_pos: list | None = None

    # ---- helpers -------------------------------------------------------
    def say(self, text: str) -> None:
        self.log.append(text)
        del self.log[:-200]

    def add_xp(self, n: int) -> list[str]:
        p = self.player
        n = round(n * (1 + 0.05 * (p.stats["Wits"] - 1)))
        p.xp += n
        msgs = [f"+{n} XP"]
        while p.xp >= p.xp_to_next():
            p.xp -= p.xp_to_next()
            p.level += 1
            p.recalc()
            p.hp = p.max_hp
            msgs.append(f"LEVEL {p.level}. Your rating has been updated. HP restored.")
        return msgs

    def add_signal(self, amount: float) -> list[str]:
        p = self.player
        before = p.signal
        p.signal = max(0.0, min(100.0, p.signal + amount))
        msgs = []
        for mark, text in ((50, "SIGNAL 50: You're showing up on things. Patrols will notice."),
                           (75, "SIGNAL 75: The Concierge has you in high definition. Enemies aim better."),
                           (100, "SIGNAL 100: \"We see you, and we care.\" Find tinfoil. Now.")):
            if before < mark <= p.signal:
                msgs.append(text)
        return msgs

    def add_note(self, title: str, body: str) -> None:
        if not any(n[0] == title for n in self.notes):
            self.notes.append([title, body])

    # ---- persistence ---------------------------------------------------
    def to_json(self) -> dict:
        d = asdict(self)
        d["flags"] = sorted(self.flags)
        d["taken"] = sorted(self.taken)
        d["version"] = SAVE_VERSION
        return d

    @classmethod
    def from_json(cls, d: dict) -> "GameState":
        d = dict(d)
        d.pop("version", None)
        player = Player(**d.pop("player"))
        gs = cls(player=player, **d)
        gs.flags = set(gs.flags)
        gs.taken = set(gs.taken)
        return gs


def save_dir() -> Path:
    return Path(os.environ.get("QCTS_SAVE_DIR", Path.home() / ".qcts"))


def save_path(slot: str = "save") -> Path:
    return save_dir() / f"{slot}.json"


def save_game(state: GameState, slot: str = "save") -> Path:
    path = save_path(slot)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state.to_json(), indent=1))
    tmp.replace(path)
    return path


def load_game(slot: str = "save") -> GameState | None:
    path = save_path(slot)
    if not path.exists():
        return None
    try:
        return GameState.from_json(json.loads(path.read_text()))
    except (ValueError, TypeError, KeyError):
        return None


def has_save(slot: str = "save") -> bool:
    return save_path(slot).exists()
