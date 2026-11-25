"""Runs YAML dialogue trees with stat-gated options and effects."""
from __future__ import annotations

from .content import Content, apply_effects, check, describe_check
from .state import GameState


class Dialogue:
    def __init__(self, did: str, state: GameState, content: Content):
        self.state, self.content = state, content
        self.d = content.dialogues[did]
        self.events: list[tuple] = []
        self.done = False
        start = self.d.get("start", "start")
        for s in self.d.get("starts", []):
            if check(s.get("if"), state):
                start = s["node"]
                break
        self.enter(start)

    def enter(self, nid: str) -> None:
        self.node_id = nid
        self.node = self.d["nodes"][nid]
        self.events += apply_effects(self.node.get("effects"), self.state, self.content)

    @property
    def speaker(self) -> str:
        return self.node.get("speaker", self.d.get("speaker", ""))

    @property
    def text(self) -> str:
        text = self.node.get("text", "")
        for v in self.node.get("texts", []):
            if check(v.get("if"), self.state):
                text = v["text"]
                break
        return text.replace("{cells}", str(self.state.player.cells))

    def options(self) -> list[tuple[str, bool, dict]]:
        out = []
        for opt in self.node.get("options", [{"text": "[Leave]", "to": "end"}]):
            if not check(opt.get("show_if"), self.state):
                continue
            tag = describe_check(opt.get("if"))
            label = f"{tag} {opt['text']}".strip()
            out.append((label, check(opt.get("if"), self.state), opt))
        return out

    def choose(self, index: int) -> bool:
        opts = self.options()
        if not (0 <= index < len(opts)) or not opts[index][1]:
            return False
        opt = opts[index][2]
        self.events += apply_effects(opt.get("effects"), self.state, self.content)
        to = opt.get("to", "end")
        if to == "end" or any(e[0] == "game_over" for e in self.events):
            self.done = True
        else:
            self.enter(to)
        return True
