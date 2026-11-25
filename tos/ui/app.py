"""Queen City: Terms of Service — Textual app entry point."""
from __future__ import annotations

import random

from textual.app import App

from ..engine.content import get_content
from ..engine.state import GameState
from .screens import CityScreen, LocationScreen, TitleScreen

CSS = """
Screen { background: #0a0d0b; color: #d8e0d0; }
.panel { border: round #3f6f4a; border-title-color: #e8c35a; border-title-style: bold; padding: 0 1; background: #0a0d0b; }
#main { height: 1fr; }
#left { width: 52; height: 1fr; }
#map { height: 13; }
#side { width: 1fr; min-width: 28; height: 1fr; }
#log { height: 1fr; min-height: 5; scrollbar-size: 0 0; }
#help { height: 1; padding: 0 1; }
#cityleft { width: 56; height: 1fr; }
#citymap { height: 17; }
#citymsg { height: 1fr; }
#cityside { width: 1fr; height: 1fr; }
TitleScreen, ProfileScreen, IntroScreen, GameOverScreen { align: center middle; }
#title-box { width: 80; height: auto; align: center middle; }
#title-art { width: 80; height: auto; content-align: center middle; }
#title-menu { width: 80; height: auto; padding: 1 2 0 30; }
#profile, #intro, #gameover { width: 76; height: auto; padding: 1 2; }
DialogueScreen, HackScreen, WristLinkScreen, TipScreen { align: center middle; background: #0a0d0b 60%; }
#tip { width: 74; height: auto; max-height: 23; padding: 1 2; border: round #e8c35a; }
.modal { background: #0d140f; }
#dialogue { width: 74; height: auto; max-height: 22; padding: 1 2; }
#hack { width: 78; height: auto; padding: 0 1; }
#hack-cols { height: 11; margin: 1 0 0 0; }
#hack-dump { width: 32; }
#hack-hist { width: 1fr; padding: 0 0 0 2; }
#hack-input { border: tall #3f6f4a; background: #0d140f; }
#wrist { width: 76; height: 22; padding: 0 2; }
"""


class QCApp(App):
    CSS = CSS
    TITLE = "Queen City: Terms of Service"

    def __init__(self, seed: int | None = None):
        super().__init__()
        self.content = get_content()
        self.rng = random.Random(seed)
        self.state: GameState | None = None

    def on_mount(self) -> None:
        self.push_screen(TitleScreen())

    def goto_current(self) -> None:
        if self.state.location.startswith("city:"):
            self.switch_screen(CityScreen())
        else:
            self.switch_screen(LocationScreen([("log", "Session restored.")]))


def main() -> None:
    QCApp().run()


if __name__ == "__main__":
    main()
