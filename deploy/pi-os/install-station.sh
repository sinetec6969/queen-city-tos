#!/usr/bin/env bash
# Set up the radio side of a Queen City node on Raspberry Pi OS Lite (Bookworm).
#
#   sudo deploy/digipi/install.sh                 # the game itself (once)
#   sudo deploy/pi-os/install-station.sh KN4ABC   # direwolf + AX.25 + ax25d for your call
#
# Installs packages, writes configs with your callsign (node SSID -5), installs the
# systemd units and the qcts-on / qcts-off kill switch. It does NOT start transmitting:
# run `sudo qcts-on` yourself once the radio checks in the README pass.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "run with sudo" >&2; exit 1; }
CALL="${1:-}"
CALL="$(echo "$CALL" | tr '[:lower:]' '[:upper:]')"
[[ "$CALL" =~ ^[A-Z0-9]{1,2}[0-9][A-Z]{1,4}$ ]] || { echo "usage: $0 YOURCALL   (a real US callsign, no SSID)" >&2; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -x /usr/local/bin/qcts-line ] || { echo "install the game first: sudo $HERE/../digipi/install.sh" >&2; exit 1; }

if command -v apt-get >/dev/null; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq direwolf ax25-tools ax25-apps >/dev/null
fi

install -d /etc/qcts /etc/ax25
for f in axports ax25d.conf; do
  [ -f "/etc/ax25/$f" ] && [ ! -f "/etc/ax25/$f.pre-qcts" ] && cp "/etc/ax25/$f" "/etc/ax25/$f.pre-qcts"
done
sed "s/YOURCALL/$CALL/g" "$HERE/direwolf.conf" > /etc/qcts/direwolf.conf
sed "s/YOURCALL/$CALL/g" "$HERE/axports" > /etc/ax25/axports
sed "s/YOURCALL/$CALL/g" "$HERE/ax25d.conf" > /etc/ax25/ax25d.conf
install -m 644 "$HERE/qcts-direwolf.service" "$HERE/qcts-ax25.service" /etc/systemd/system/
install -m 755 "$HERE/qcts-on" "$HERE/qcts-off" /usr/local/sbin/

# the game user needs no audio or serial access; direwolf runs as root via systemd
if command -v systemctl >/dev/null && [ -d /run/systemd/system ]; then
  systemctl daemon-reload
  systemctl disable qcts-direwolf.service qcts-ax25.service >/dev/null 2>&1 || true
fi

echo "Station configured for $CALL-5 (not transmitting)."
echo "Next: the bench checks in deploy/pi-os/README.md, then 'sudo qcts-on'."
echo "To start at boot later: sudo systemctl enable qcts-direwolf qcts-ax25"
