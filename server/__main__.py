"""Startpunkt: python -m server"""

from __future__ import annotations

import argparse
import faulthandler
import logging
import signal
import sys
import webbrowser
from logging.handlers import RotatingFileHandler

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

    # Protokoll: Konsole (falls vorhanden) + Datei %APPDATA%\TabDeck\tabdeck.log (max. 2 × 1 MB)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", datefmt="%d.%m. %H:%M:%S")
    handlers: list[logging.Handler] = []
    try:
        file_handler = RotatingFileHandler(DATA_DIR / "tabdeck.log", maxBytes=1_000_000, backupCount=1, encoding="utf-8")
        file_handler.setFormatter(fmt)
        handlers.append(file_handler)
    except OSError:
        pass
    if sys.stderr is not None:
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", datefmt="%H:%M:%S"))
        handlers.append(console)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, handlers=handlers)
    # Unerwartete Fehler und echte Abstürze (z. B. in Windows-Treibern) in Dateien festhalten
    sys.excepthook = lambda t, v, tb: logging.getLogger("tabdeck").critical("Unerwarteter Fehler", exc_info=(t, v, tb))
    try:
        _crash_file = open(DATA_DIR / "crash.log", "a", encoding="utf-8")  # noqa: SIM115 – bleibt bis Programmende offen
        faulthandler.enable(file=_crash_file, all_threads=True)
    except OSError:
        pass
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

    log = logging.getLogger("tabdeck")
    ctrl_c = {"hit": False}

    def on_ctrl_c(signum, frame):  # Strg+C im Fenster erkennen (die Webserver-Bibliothek schluckt es sonst)
        ctrl_c["hit"] = True
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, on_ctrl_c)
    try:
        web.run_app(server.make_app(), host=host, port=port, print=None, access_log=None, handle_signals=False)
    except KeyboardInterrupt:
        log.warning("TabDeck wurde mit Strg+C beendet. (Tipp: Im TabDeck-Fenster kein Strg+C drücken – "
                    "zum Kopieren erst Text markieren.)")
    except OSError as exc:
        log.critical("TabDeck konnte nicht starten: %s – läuft TabDeck schon in einem anderen Fenster?", exc)
    except Exception:
        log.critical("TabDeck ist wegen eines Fehlers beendet worden", exc_info=True)
    else:
        if ctrl_c["hit"]:
            log.warning("TabDeck wurde mit Strg+C beendet. (Tipp: Im TabDeck-Fenster kein Strg+C drücken – "
                        "zum Kopieren erst Text markieren.)")
        else:
            log.warning("TabDeck wurde beendet.")
    finally:
        server.audio.close()


if __name__ == "__main__":
    main()
