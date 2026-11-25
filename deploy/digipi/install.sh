#!/usr/bin/env bash
# Install the line-mode game for an AX.25 node (DigiPi or any Linux ax25d/URONode box).
#
#   sudo deploy/digipi/install.sh            # from a checkout of the repo
#
# Puts the game package in /opt/qcts, a PyYAML-only venv beside it (Textual isn't
# needed for line mode), saves in /var/lib/qcts owned by a `qcts` system user, the
# allowlist in /etc/qcts/allow, and a wrapper at /usr/local/bin/qcts-line.
# Re-running updates the code and keeps saves and the allowlist.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "run with sudo" >&2; exit 1; }
SRC="$(cd "$(dirname "$0")/../.." && pwd)"
PREFIX=/opt/qcts
SAVES=/var/lib/qcts

if findmnt -no OPTIONS / | grep -qw ro; then
  echo "root filesystem is read-only; remount it read-write first (and see README.md about saves)" >&2
  exit 1
fi

id qcts >/dev/null 2>&1 || useradd --system --home-dir "$SAVES" --shell /usr/sbin/nologin qcts

install -d "$PREFIX"
rm -rf "$PREFIX/app.new"
install -d "$PREFIX/app.new"
cp -r "$SRC/tos" "$SRC/pyproject.toml" "$PREFIX/app.new/"
find "$PREFIX/app.new" -name __pycache__ -prune -exec rm -rf {} +
rm -rf "$PREFIX/app"
mv "$PREFIX/app.new" "$PREFIX/app"

[ -x "$PREFIX/venv/bin/python" ] || python3 -m venv "$PREFIX/venv"
"$PREFIX/venv/bin/pip" install -q --upgrade "pyyaml>=6"

install -d -o qcts -g qcts -m 750 "$SAVES"
install -d /etc/qcts
[ -f /etc/qcts/allow ] || install -m 644 "$SRC/deploy/digipi/allow.example" /etc/qcts/allow
install -m 755 "$SRC/deploy/digipi/qcts-line" /usr/local/bin/qcts-line

# smoke test as the qcts user: should print the title and exit
printf 'q\r' | sudo -u qcts env QCTS_ALLOW= /usr/local/bin/qcts-line N0CALL --eol lf
echo
echo "Installed. Edit /etc/qcts/allow, then wire the node (deploy/digipi/README.md)."
