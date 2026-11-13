#!/usr/bin/env bash
# Start unter Linux/macOS (Hauptzielplattform ist Windows – siehe start.bat)
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Erster Start: richte Python-Umgebung ein ..."
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
exec .venv/bin/python -m server "$@"
