"""Prompt Injection: guess the password from a list; wrong guesses report likeness."""
from __future__ import annotations

import random

from . import noise, perks

JUNK = "!@#$%^&*()[]{}<>/\\|;:'\",.?=+-_~"


def likeness(a: str, b: str) -> int:
    return sum(x == y for x, y in zip(a, b))


class Hack:
    def __init__(self, pool: list[str], n_words: int, attempts: int, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        words = [w.upper() for w in pool]
        self.rng.shuffle(words)
        self.words = words[:n_words]
        self.password = self.rng.choice(self.words)
        self.attempts = self.max_attempts = attempts
        self.history: list[tuple[str, int]] = []
        self.result: bool | None = None
        self.hit: dict | None = None
        self.dump = self._make_dump()

    def _make_dump(self, rows: int = 11, width: int = 22) -> list[str]:
        """Fake memory dump with the words buried in junk."""
        slots = self.rng.sample(range(rows), len(self.words)) if len(self.words) <= rows else range(rows)
        lines = []
        base = self.rng.randint(0xA000, 0xF000)
        placed = dict(zip(slots, self.words))
        for r in range(rows):
            junk = "".join(self.rng.choice(JUNK) for _ in range(width))
            w = placed.get(r)
            if w:
                at = self.rng.randint(0, width - len(w))
                junk = junk[:at] + w + junk[at + len(w):]
            lines.append(f"0x{base + r * width:04X}  {junk}")
        return lines

    def guess(self, word: str) -> str:
        word = word.strip().upper()
        if self.result is not None:
            return "Session closed."
        hit = noise.heard(word)
        if hit is not None:
            self.result, self.hit = True, hit
            return hit["say"]
        if word not in self.words:
            return f">{word}\n>Not in prompt buffer."
        self.attempts -= 1
        if word == self.password:
            self.result = True
            self.history.append((word, len(word)))
            return f">{word}\n>Exact match!\n>Injection accepted. Assuming admin role."
        lk = likeness(word, self.password)
        self.history.append((word, lk))
        if self.attempts <= 0:
            self.result = False
            return f">{word}\n>Likeness={lk}\n>INJECTION DETECTED. This incident has been reported (lovingly)."
        return f">{word}\n>Entry denied.\n>Likeness={lk}"


def attempts_for(wits: int) -> int:
    return 3 + (1 if wits >= 3 else 0) + (1 if wits >= 5 else 0)


def for_terminal(state, content, spec: dict, rng: random.Random | None = None) -> Hack:
    """The Hack for a terminal's `hack:` spec, with Wits and perks applied (both frontends use this)."""
    pool = content.hack_words[spec.get("length", 5)]
    words = max(3, spec.get("words", 8) + int(perks.mod(state, content, "hack_words")))
    attempts = attempts_for(state.player.stats["Wits"]) + int(perks.mod(state, content, "hack_attempts"))
    return Hack(pool, words, attempts, rng)
