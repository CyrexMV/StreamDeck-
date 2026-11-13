"""Laden und Speichern der Konfiguration (data/config.json)."""

from __future__ import annotations

import copy
import json
import logging
import os
import secrets
from pathlib import Path

log = logging.getLogger("tabdeck.config")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("TABDECK_DATA_DIR", ROOT / "data"))
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
    "discord": {"mute": "ctrl+shift+m", "deafen": "ctrl+shift+d", "ptt": "f13"},
}
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


class ConfigStore:
    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path
        self.data: dict = {}
        self.load()

    # ------------------------------------------------------------------ laden
    def load(self) -> None:
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

        env_token = os.environ.get("TABDECK_TOKEN")
        if env_token:
            self.data["server"]["token"] = normalize_token(env_token)
        if not normalize_token(self.data["server"].get("token")):
            self.data["server"]["token"] = new_token()
        self.save()

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
        merged.setdefault("settings", {})
        _merge_defaults(merged["settings"], DEFAULT_SETTINGS)
        merged.setdefault("obs", {})
        _merge_defaults(merged["obs"], DEFAULT_OBS)
        self.data = merged
        self.save()
