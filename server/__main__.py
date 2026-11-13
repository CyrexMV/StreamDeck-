"""Startpunkt: python -m server"""

from __future__ import annotations

import argparse
import logging
import sys
import webbrowser

from aiohttp import web

from . import __version__
from .app import DeckServer, print_qr
from .config import DATA_DIR, ConfigStore, format_token


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="TabDeck – Tablet als Stream Deck")
    parser.add_argument("--port", type=int, help="Port (Standard: aus config.json, 8765)")
    parser.add_argument("--host", help="Adresse, auf der gelauscht wird (Standard 0.0.0.0)")
    parser.add_argument("--open", action="store_true", help="Verbindungsseite mit QR-Code im Browser öffnen")
    parser.add_argument("--debug", action="store_true", help="Ausführliche Protokollausgabe")
    args = parser.parse_args()

    log_kwargs: dict = {}
    if sys.stdout is None or sys.stderr is None:
        # Start ohne Konsole (pythonw / start-hidden.vbs): in Datei protokollieren
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        log_kwargs["filename"] = str(DATA_DIR / "tabdeck.log")
        log_kwargs["encoding"] = "utf-8"
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
        **log_kwargs,
    )
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)

    store = ConfigStore()
    if args.port:
        store.data["server"]["port"] = args.port
    if args.host:
        store.data["server"]["host"] = args.host
    host = store.data["server"]["host"]
    port = int(store.data["server"]["port"])

    server = DeckServer(store)
    urls = server.connect_urls()

    print()
    print(f"  ━━━  TabDeck {__version__} – dein Tablet als Stream Deck  ━━━")
    print()
    print("  Auf dem Tablet im Browser öffnen (gleiches WLAN):")
    for url in urls:
        print(f"    → {url.split('?')[0]}")
    print()
    print(f"  Verbindungscode:  {format_token(store.token)}")
    print(f"  QR-Code am PC:    http://localhost:{port}/connect")
    print(f"  Deine Belegung:   {store.path}")
    print()
    print_qr(urls[0])
    print("  Funktionen:")
    for name, feat in server.features().items():
        print(f"    {'✔' if feat['ok'] else '✘'} {name:<9} {'' if feat['ok'] else feat['error']}")
    print()
    print("  Beenden mit Strg+C")
    print()

    if args.open:
        webbrowser.open(f"http://localhost:{port}/connect")

    web.run_app(server.make_app(), host=host, port=port, print=None, access_log=None)


if __name__ == "__main__":
    main()
