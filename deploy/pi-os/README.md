# Queen City node on Raspberry Pi OS (Pi 4 + Digirig Mobile + UV-5R)

The recommended way to host the game over the air. DigiPi is built as a read-only appliance (its changes are erased at reboot), and the game needs writable saves and its own node entry. Keep a DigiPi card around only as a quick known-good test of the radio and Digirig.

The node pieces (`axports` paclen 128, the `ax25d.conf` entry, `%U`, the game's I/O) were proven on 2026-11-25 in a loopback lab: two direwolf modems, real 1200-baud AFSK, kernel AX.25, ax25d spawning the game, axcall playing it. **What has not been tested yet:** this exact Pi, the Digirig and the UV-5R.

## 1. Install
On a fresh **Raspberry Pi OS Lite (Bookworm, 64-bit)** card:
```bash
sudo apt update && sudo apt install -y git python3-venv
git clone https://github.com/sinetec6969/queen-city-tos.git && cd queen-city-tos
sudo deploy/digipi/install.sh               # the game (generic; the name is historical)
sudo deploy/pi-os/install-station.sh YOURCALL
sudo nano /etc/qcts/allow                   # callsigns allowed to play, no SSIDs
```
`install-station.sh` writes `/etc/qcts/direwolf.conf`, `/etc/ax25/axports` and `/etc/ax25/ax25d.conf`, backing up any originals as `*.pre-qcts`. It installs `qcts-on` / `qcts-off`. **It does not start transmitting.**

## 2. Radio setup (UV-5R)
- Program the node frequency. Never 144.39 (APRS). Pick a frequency after checking the local band plan and with local packet users.
- Menu settings:
  - **SAVE** (battery save): **OFF**. It eats the start of incoming packets.
  - **TDR** (dual watch): **OFF**.
  - **VOX**: **OFF**.
  - **ROGER**: OFF.
  - **STE**: OFF.
  - **TOT**: 60 s or more.
  - **BEEP**: OFF.
  - **SQL**: 3–5.
- **Power: LOW (1 W)** while testing.
- Run the radio from a **battery eliminator / DC supply**, not the battery, for long sessions. An HT isn't built for a high duty cycle; watch the heat.

## 3. Digirig + audio
- The Digirig is a USB sound card plus a serial port whose **RTS line keys the radio** (`PTT /dev/ttyUSB0 RTS`).
- Check `arecord -l`; the card is usually `Device`. If not, edit `ADEVICE` in `/etc/qcts/direwolf.conf`.
- Use the Digirig's **Baofeng (K-plug) cable**. It needs Digirig Mobile rev 1.6+.
- **Levels:**
  - Set capture so direwolf shows audio level ~50 on received packets.
  - **Start playback low.** The Digirig Mobile is known to over-drive HT mic inputs. Raise it until another station decodes you reliably, then stop.
  - Use `alsamixer -c Device` and save with `sudo alsactl store`.
- **RF hygiene:**
  - Put ferrite chokes on the USB and audio leads.
  - Keep the antenna a few feet from the Pi and Digirig.
  - Check the 3.5 dBi antenna's **SWR** on the node frequency.

## 4. Bench checks before any real use
1. **Into a dummy load** (or LOW power on a quiet frequency): `sudo qcts-on`, then `journalctl -fu qcts-direwolf`.
2. From a second station, connect to `YOURCALL-5` (e.g. another Pi with `axcall`, or a TNC/app). You should get the title screen.
3. **Tune `TXDELAY`:**
   - Start at 40 (400 ms).
   - If the other side misses the start of your frames, go up in steps of 5.
   - If it's solid, try going down. The UV-5R is slow to switch from TX to RX.
4. Play to the first save, `BYE`, reconnect, and check it resumes.
5. Pull the other station's power mid-game, reconnect, and check progress was kept.
6. **Kill switch:** `sudo qcts-off`. Confirm the radio cannot key.

## 5. Running it
- Start: `sudo qcts-on`. Stop: `sudo qcts-off`.
- At boot: `sudo systemctl enable qcts-direwolf qcts-ax25`.
- Players connect to `YOURCALL-5`, one game per callsign, at most 3 at once (`QCTS_MAX_SESSIONS`).
- Logs:
  - direwolf: `journalctl -u qcts-direwolf`.
  - Game crashes: `/var/lib/qcts/line-errors.log` (never sent over the air).

## Part 97 reminders (you're the station licensee and control operator)
- **Automatic control:** data on 2 m appears to be allowed under 97.221(b) (6 m and shorter). Verify against the current eCFR.
- **Station ID:** the AX.25 address on every frame carries your callsign.
- **Turning it off:** keep `qcts-off` reachable (SSH) whenever it's unattended.
- **RF exposure:** do and keep the routine evaluation (97.13(c)). At 1–5 W into a 3.5 dBi antenna it's simple.
- **Spurious emissions:** you're responsible for them (97.307). Baofengs vary. Ideally have yours checked on a spectrum analyzer, or add a 2 m low-pass filter.
- **Content:** plain text, no encryption. The game text is profanity-free and contains no business names.
