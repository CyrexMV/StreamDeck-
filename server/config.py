"""Laden und Speichern der Konfiguration.

Speicherort: unter Windows %APPDATA%\\TabDeck (übersteht Updates und neue Programmordner),
sonst <Programmordner>/data. Beim ersten Start wird eine ältere Belegung aus dem
Programmordner oder einem benachbarten TabDeck-Ordner automatisch übernommen.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import secrets
import shutil
import sys
import time
from pathlib import Path

log = logging.getLogger("tabdeck.config")

ROOT = Path(__file__).resolve().parent.parent
DATA_ENV = os.environ.get("TABDECK_DATA_DIR")


def _data_dir() -> Path:
    if DATA_ENV:
        return Path(DATA_ENV)
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "TabDeck"
    return ROOT / "data"


DATA_DIR = _data_dir()
CONFIG_PATH = DATA_DIR / "config.json"
ICON_DIR = DATA_DIR / "icons"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "default_config.json"

# Ohne leicht verwechselbare Zeichen (0/O, 1/I)
TOKEN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

DEFAULT_SERVER = {"host": "0.0.0.0", "port": 8765, "token": ""}
DEFAULT_SETTINGS = {
    "columns": 8,
    "rows": 4,
    "show_tabs": True,
    "show_labels": True,
    "rotate_portrait": True,
    "haptics": True,
    "gap": 12,
    "radius": 18,
    "discord": {"mute": "f14", "deafen": "f15", "ptt": "f13"},
}
CONFIG_VERSION = 4
DEFAULT_OBS = {"enabled": True, "host": "127.0.0.1", "port": 4455, "password": ""}


def new_token() -> str:
    return "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(8))


def normalize_token(token: str | None) -> str:
    return "".join(c for c in (token or "").upper() if c.isalnum())


def format_token(token: str) -> str:
    return f"{token[:4]}-{token[4:]}" if len(token) == 8 else token


def _merge_defaults(target: dict, defaults: dict) -> None:
    for key, value in defaults.items():
        if key not in target:
            target[key] = copy.deepcopy(value)
        elif isinstance(value, dict) and isinstance(target[key], dict):
            _merge_defaults(target[key], value)


def _is_tabdeck_config(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return isinstance(data, dict) and isinstance(data.get("pages"), list) and "settings" in data
    except (OSError, ValueError):
        return False


def find_previous_data() -> Path | None:
    """Ältere Belegung suchen: im eigenen Programmordner und in benachbarten (älteren) TabDeck-Ordnern."""
    candidates = [ROOT / "data"]
    try:
        candidates += [p.parent for p in ROOT.parent.glob("*/data/config.json")]
        candidates += [p.parent for p in ROOT.parent.glob("*/*/data/config.json")]
    except OSError:
        pass
    found = []
    for folder in dict.fromkeys(candidates):
        cfg = folder / "config.json"
        try:
            if folder.resolve() != DATA_DIR.resolve() and cfg.is_file() and _is_tabdeck_config(cfg):
                found.append((cfg.stat().st_mtime, folder))
        except OSError:
            continue
    return max(found)[1] if found else None


def _copy_data(src: Path) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "config.json", DATA_DIR / "config.json")
    for sub in ("icons", "appicons"):
        if (src / sub).is_dir():
            shutil.copytree(src / sub, DATA_DIR / sub, dirs_exist_ok=True)


def import_previous_data() -> None:
    """Bisherige Belegung (inkl. Bilder & Verbindungscode) übernehmen.

    1. Liegt im Programmordner ein Ordner „data“ mit einer Belegung (z. B. aus der alten
       Version hineingezogen), wird er IMMER übernommen. Die aktuelle Belegung wird vorher
       gesichert, der Ordner danach in „data (übernommen …)“ umbenannt.
    2. Sonst beim allerersten Start: neueste Belegung aus einem benachbarten TabDeck-Ordner.
    """
    if DATA_ENV:
        return
    local = ROOT / "data"
    try:
        same = local.resolve() == DATA_DIR.resolve()
    except OSError:
        same = False
    if not same and (local / "config.json").is_file() and _is_tabdeck_config(local / "config.json"):
        stamp = time.strftime("%Y-%m-%d %H-%M-%S")
        current = DATA_DIR / "config.json"
        if current.exists():
            shutil.copy2(current, DATA_DIR / f"config vorher {stamp}.json")
        _copy_data(local)
        try:
            local.rename(ROOT / f"data (übernommen {stamp})")
        except OSError:
            (local / "config.json").rename(local / f"config (übernommen {stamp}).json")
        log.info("Belegung aus %s übernommen (vorherige Belegung gesichert)", local)
        return
    if (DATA_DIR / "config.json").exists():
        return
    src = find_previous_data()
    if src:
        _copy_data(src)
        log.info("Bisherige Belegung übernommen aus %s", src)


class ConfigStore:
    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path
        self.data: dict = {}
        self.load()

    # ------------------------------------------------------------------ laden
    def load(self) -> None:
        if self.path == CONFIG_PATH:
            try:
                import_previous_data()
            except OSError as exc:
                log.error("Bisherige Belegung konnte nicht übernommen werden: %s", exc)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ICON_DIR.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                backup = self.path.with_suffix(".defekt.json")
                log.error("Konfiguration unlesbar (%s) – Sicherung unter %s, starte mit Standard.", exc, backup)
                try:
                    self.path.replace(backup)
                except OSError:
                    pass
                self.data = {}
        if not self.data:
            self.data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))

        self.data.setdefault("server", {})
        _merge_defaults(self.data["server"], DEFAULT_SERVER)
        self.data.setdefault("settings", {})
        _merge_defaults(self.data["settings"], DEFAULT_SETTINGS)
        self.data.setdefault("obs", {})
        _merge_defaults(self.data["obs"], DEFAULT_OBS)
        if not self.data.get("pages"):
            self.data["pages"] = [{"id": "main", "name": "Start", "buttons": {}}]
        self.data.setdefault("secrets", {})
        self.data["secrets"].setdefault("spotify", {})
        self._migrate()

        env_token = os.environ.get("TABDECK_TOKEN")
        if env_token:
            self.data["server"]["token"] = normalize_token(env_token)
        if not normalize_token(self.data["server"].get("token")):
            self.data["server"]["token"] = new_token()
        self.save()

    def _migrate(self) -> None:
        version = self.data.get("version", 1)
        if version < 2:
            # Spotify-Lautstärke: vom Windows-Mixer auf die echte Lautstärke in der Spotify-App umstellen
            ops = {"up": "volume_up", "down": "volume_down", "set": "volume_set", "toggle_mute": "mute_toggle"}
            changed = 0
            for page in self.data.get("pages", []):
                for btn in (page.get("buttons") or {}).values():
                    for i, a in enumerate(btn.get("actions") or []):
                        app = str(a.get("app", "")).lower().removesuffix(".exe")
                        if a.get("type") == "volume" and a.get("target") == "app" and app == "spotify" and a.get("op") in ops:
                            step = a.get("step", 10)
                            btn["actions"][i] = {"type": "spotify", "op": ops[a["op"]], "step": 10 if step == 5 else step}
                            changed += 1
            # Discords eingebaute Kürzel (Strg+Umschalt+M/D) wirken nur im Discord-Fenster –
            # für globale Tastenbelegungen kollisionsfreie Tasten verwenden
            d = self.data.get("settings", {}).get("discord", {})
            if d.get("mute") == "ctrl+shift+m":
                d["mute"] = "f14"
            if d.get("deafen") == "ctrl+shift+d":
                d["deafen"] = "f15"
            if changed:
                log.info("%d Spotify-Lautstärke-Tasten auf die Spotify-App-Lautstärke umgestellt", changed)
        if version < 3:
            # Neue automatische Mixer-Seite mit Schiebefadern für alles, was Ton abspielt
            pages = self.data.setdefault("pages", [])
            if not any(p.get("type") == "mixer" for p in pages):
                pid = "mixer" if not any(p.get("id") == "mixer" for p in pages) else "mixer-auto"
                pages.insert(min(1, len(pages)), {"id": pid, "name": "Mixer", "type": "mixer", "buttons": {}})
                log.info("Neue Seite „Mixer“ mit Schiebefadern hinzugefügt")
        if version < 4:
            # Echte Programm-Logos ergänzen – alles andere an der Belegung bleibt unverändert
            self._add_app_logos()
        self.data["version"] = CONFIG_VERSION

    def _add_app_logos(self) -> None:
        """Echte Programm-Logos: Öffnen-/Ordner-Tasten als großes Symbol, App-Tasten der Startseite als Abzeichen."""
        folder_apps = {"obs": "obs64", "discord": "discord", "spotify": "spotify"}
        badge_types = {"discord", "obs", "spotify"}
        changed = 0
        for page in self.data.get("pages", []):
            for btn in (page.get("buttons") or {}).values():
                if btn.get("image") or btn.get("widget") or "app_icon" in btn:
                    continue
                first = (btn.get("actions") or [{}])[0]
                kind = first.get("type")
                if kind == "open" and first.get("target") and not str(first["target"]).lower().startswith(("ms-settings", "shell:")):
                    btn["app_icon"] = "main"
                elif kind == "page" and first.get("page") in folder_apps:
                    btn["app"] = folder_apps[first["page"]]
                    btn["app_icon"] = "main"
                elif kind in badge_types and page.get("id") == "main":
                    btn["app_icon"] = "badge"
                else:
                    continue
                changed += 1
        if changed:
            log.info("%d Tasten zeigen jetzt das Programm-Logo", changed)

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    # ------------------------------------------------------------- Zugriffe
    @property
    def token(self) -> str:
        return normalize_token(self.data["server"]["token"])

    @property
    def settings(self) -> dict:
        return self.data["settings"]

    @property
    def secrets(self) -> dict:
        return self.data["secrets"]

    @property
    def obs(self) -> dict:
        return self.data["obs"]

    def page(self, page_id: str) -> dict | None:
        return next((p for p in self.data["pages"] if p.get("id") == page_id), None)

    def button(self, page_id: str, slot) -> dict | None:
        page = self.page(page_id)
        if not page:
            return None
        return page.get("buttons", {}).get(str(slot))

    def client_view(self) -> dict:
        """Konfiguration für das Tablet – ohne Server-Abschnitt (Token, Port)."""
        view = copy.deepcopy(self.data)
        view.pop("server", None)
        view.pop("secrets", None)
        return view

    def update_from_client(self, new: dict) -> None:
        if not isinstance(new, dict):
            raise ValueError("Konfiguration muss ein Objekt sein")
        pages = new.get("pages")
        if not isinstance(pages, list) or not pages:
            raise ValueError("Es muss mindestens eine Seite geben")
        seen = set()
        for page in pages:
            if not isinstance(page, dict) or not page.get("id"):
                raise ValueError("Ungültige Seite")
            if page["id"] in seen:
                raise ValueError(f"Seiten-ID doppelt: {page['id']}")
            seen.add(page["id"])
            if not isinstance(page.get("buttons", {}), dict):
                raise ValueError("Ungültige Tasten auf Seite " + str(page.get("name")))
            page.setdefault("buttons", {})
            page.setdefault("name", page["id"])

        merged = copy.deepcopy(new)
        merged["server"] = self.data["server"]
        merged["secrets"] = self.data.get("secrets", {})
        merged["version"] = int(new.get("version") or 1)  # ältere Sicherung → Ergänzungen nachtragen
        merged.setdefault("settings", {})
        _merge_defaults(merged["settings"], DEFAULT_SETTINGS)
        merged.setdefault("obs", {})
        _merge_defaults(merged["obs"], DEFAULT_OBS)
        self.data = merged
        self._migrate()
        self.save()
