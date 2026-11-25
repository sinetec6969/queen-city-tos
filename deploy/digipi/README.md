# Queen City over AX.25 (DigiPi node)

The node starts `qcts-line CALLSIGN` once per incoming connection and connects
it to the program's stdin/stdout. The game speaks plain ASCII with CR line
endings and keeps most replies under ~250 bytes, so 1200 baud is playable.
Saves are per callsign (SSID stripped), so reconnecting resumes the game.

## 1. Station first
Check that the DigiPi can connect to another station *before* installing the game:
direwolf keys the radio through the Digirig, decodes, and the node answers a connect
from a second station. If a plain node connect doesn't work, the game won't either.

## 2. Install
```bash
git clone https://github.com/sinetec6969/queen-city-tos.git
cd queen-city-tos
sudo deploy/digipi/install.sh
sudo nano /etc/qcts/allow        # one callsign per line, no SSID
```

**Read-only root:** DigiPi images may mount `/` read-only to survive power
cuts (not verified). The installer stops if `/` is read-only. Saves need a
writable `/var/lib/qcts`. Either remount read-write while playing, or point
`QCTS_SAVE_DIR` in `/usr/local/bin/qcts-line` at writable storage.

## 3. Wire it into the node
Not yet checked on a DigiPi image. Copy whatever the image already does for
its other node programs (for example a Zork entry), and confirm the syntax
with `man ax25d.conf` / the comments in `uronode.conf`.

**ax25d** (`/etc/ax25/ax25d.conf`): a dedicated SSID that drops straight into
the game. Replace `N0CALL-5` with your call and SSID, and `radio` with the port
name in `/etc/ax25/axports`:
```
[N0CALL-5 VIA radio]
default  * * * * * *  -  qcts  /usr/local/bin/qcts-line  qcts-line %U
```
`%U` should be the caller's callsign without SSID. The game strips any SSID
anyway. Restart ax25d after editing.

**URONode**: add an external command so node users can type `GAME`.
Mirror the format of the existing `ExtCmd` lines in `uronode.conf`, running
`/usr/local/bin/qcts-line %u` as user `qcts`.

## 4. Test without a radio
```bash
printf 'n\rok\rx\rl\rbye\r' | sudo -u qcts env QCTS_ALLOW= qcts-line N0CALL --eol lf
# feel the airtime over telnet:
socat TCP-LISTEN:7300,reuseaddr,fork EXEC:"qcts-line N0CALL --eol crlf --baud 1200"
telnet localhost 7300
```

## Options
| Option | Default | Meaning |
| --- | --- | --- |
| `--eol cr\|crlf\|lf` | `cr` | AX.25 convention is CR |
| `--idle SECONDS` | 600 | Silence before save + disconnect |
| `--brief` | off | No map on arrival (players can toggle `BRIEF`/`VERBOSE`) |
| `--baud N` | off | Throttle output, for testing over telnet |
| `--allow FILE` | `$QCTS_ALLOW` | Allowlist; unreadable = nobody gets in |

One connection per callsign at a time. A second connect gets a polite refusal.
Crashes are logged to `QCTS_SAVE_DIR/line-errors.log`, never sent over the air.

## Part 97 reminders
- Plain text only, no encryption. AX.25 frames carry both callsigns.
- The node is an automatically controlled digital station. Keep it on a 2 m
  packet frequency where that's allowed.
- Game content goes out over the air. Keep it clean (97.113).
