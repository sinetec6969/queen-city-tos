"""Line-mode entry point for AX.25 nodes (ax25d / URONode) and telnet testing.

  python -m tos.line [CALLSIGN] [--baud N] [--brief] [--eol cr|crlf|lf]
                     [--idle SECONDS] [--allow FILE]

The node runs this once per connection with the caller's callsign (%u) and wires
the connection to stdin/stdout. Saves are per callsign (SSID stripped) under
QCTS_SAVE_DIR. Tracebacks go to QCTS_SAVE_DIR/line-errors.log, never to the
connection.
"""
from __future__ import annotations

import argparse
import fcntl
import os
import re
import select
import signal
import time
import traceback

from ..engine.content import get_content
from ..engine.state import save_dir
from .session import Session

EOLS = {"cr": b"\r", "crlf": b"\r\n", "lf": b"\n"}


def base_call(call: str) -> str:
    """KN4ABC-7 -> KN4ABC. Anything that isn't a plausible callsign becomes ''."""
    call = call.strip().upper().split("-", 1)[0]
    return call if re.fullmatch(r"[A-Z0-9]{3,7}", call) else ""


def allowed(call: str, path: str | None) -> bool:
    if not path:
        return True
    try:
        with open(path, encoding="utf-8") as f:
            calls = {base_call(l.split("#", 1)[0]) for l in f}
    except OSError:
        return False  # a configured but unreadable allowlist fails closed
    return call in calls


class Out:
    def __init__(self, eol: bytes, baud: int):
        self.eol, self.baud = eol, baud
        self.sent = 0

    def write(self, text: str) -> None:
        if not text:
            return
        data = text.replace("\r\n", "\n").replace("\n", "\r").encode("ascii", "replace")
        data = data.replace(b"\r", self.eol)
        if not data.endswith(self.eol):
            data += b" "  # prompts end with a space so the cursor sits after '>'
        self.sent += len(data)
        if self.baud:
            for i in range(0, len(data), 32):  # throttle: 10 bits per byte on async serial
                os.write(1, data[i:i + 32])
                time.sleep(len(data[i:i + 32]) * 10 / self.baud)
        else:
            os.write(1, data)


def lines_in(idle: float):
    """Yield input lines split on CR, LF or CRLF. Yields None on idle timeout; stops at EOF."""
    buf = b""
    while True:
        while True:
            m = re.search(rb"\r\n|\r|\n", buf)
            if not m:
                break
            line, buf = buf[:m.start()], buf[m.end():]
            if m.group() == b"\r" and not buf:
                # a lone CR at the end of a read may be the first half of CRLF
                r, _, _ = select.select([0], [], [], 0.05)
                if r:
                    nxt = os.read(0, 1)
                    if nxt and nxt != b"\n":
                        buf = nxt
            yield line.decode("latin-1")
        r, _, _ = select.select([0], [], [], idle)
        if not r:
            yield None
            return
        chunk = os.read(0, 1024)
        if not chunk:
            return
        buf += chunk
        if len(buf) > 4096:  # nobody types this much at 1200 baud
            buf = buf[-256:]


def main() -> None:
    ap = argparse.ArgumentParser(prog="qcts-line")
    ap.add_argument("call", nargs="?", default="")
    ap.add_argument("--baud", type=int, default=0, help="throttle output to N baud (testing)")
    ap.add_argument("--brief", action="store_true", help="no map on arrival")
    ap.add_argument("--eol", choices=EOLS, default="cr", help="line ending: cr for AX.25, crlf for telnet")
    ap.add_argument("--idle", type=float, default=600, help="seconds of silence before save + disconnect")
    ap.add_argument("--allow", default=os.environ.get("QCTS_ALLOW"), help="allowlist file, one callsign per line")
    args = ap.parse_args()

    out = Out(EOLS[args.eol], args.baud)
    call = base_call(args.call) if args.call else "LOCAL"
    if not call or not allowed(call, args.allow):
        out.write(f"Queen City is invite-only. {call or 'Unknown station'} isn't on the list. 73.\n")
        return

    sdir = save_dir()
    sdir.mkdir(parents=True, exist_ok=True)
    lock = open(sdir / f"{call}.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        out.write(f"{call} is already connected. One session per callsign. 73.\n")
        return

    def hangup(signum, frame):
        raise SystemExit(0)

    signal.signal(signal.SIGHUP, hangup)  # node tearing the link down
    signal.signal(signal.SIGTERM, hangup)
    session = Session(get_content(), slot=call, brief=args.brief)
    try:
        out.write(f"QCTS v{_version()} - hello {call}\n" + session.start())
        for line in lines_in(args.idle):
            if line is None:
                session.save()
                out.write("\nIdle too long. Game saved. 73.\n")
                return
            try:
                reply = session.handle(line)
            except Exception:
                with open(sdir / "line-errors.log", "a") as f:
                    f.write(f"--- {time.ctime()} {call} input={line!r}\n{traceback.format_exc()}")
                session.save()
                out.write("\nSomething broke on our end. Game saved; reconnect to continue. 73.\n")
                return
            out.write(reply)
            if session.done:
                out.write("\n")
                return
    except OSError:
        pass  # the link dropped mid-read or mid-write: nobody left to tell
    finally:
        if not session.done:
            session.save()  # EOF, dropped link, hangup, idle: always keep progress
        lock.close()


def _version() -> str:
    """From pyproject.toml beside the package (deploy layout and checkouts), else installed metadata."""
    try:
        from pathlib import Path
        text = (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text()
        return re.search(r'^version = "([^"]+)"', text, re.M).group(1)
    except Exception:
        pass
    try:
        from importlib.metadata import version
        return version("queen-city-tos")
    except Exception:
        return "dev"


if __name__ == "__main__":
    main()
