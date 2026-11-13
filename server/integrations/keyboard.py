"""Tastatur-Simulation (Tastenkombinationen, Text, Medientasten) über pynput."""

from __future__ import annotations

import logging
import sys
import threading
import time

from ..errors import ActionError

log = logging.getLogger("tabdeck.keyboard")

IS_WINDOWS = sys.platform == "win32"

# Name -> Attribut von pynput.keyboard.Key
_KEY_NAMES = {
    "ctrl": "ctrl", "control": "ctrl", "strg": "ctrl",
    "lctrl": "ctrl_l", "rctrl": "ctrl_r",
    "shift": "shift", "umschalt": "shift", "lshift": "shift_l", "rshift": "shift_r",
    "alt": "alt", "lalt": "alt_l", "ralt": "alt_r", "altgr": "alt_gr",
    "win": "cmd", "windows": "cmd", "cmd": "cmd", "super": "cmd", "meta": "cmd",
    "enter": "enter", "return": "enter", "eingabe": "enter",
    "esc": "esc", "escape": "esc",
    "tab": "tab", "space": "space", "leertaste": "space",
    "backspace": "backspace", "rücktaste": "backspace",
    "delete": "delete", "del": "delete", "entf": "delete",
    "insert": "insert", "ins": "insert", "einfg": "insert",
    "home": "home", "pos1": "home", "end": "end", "ende": "end",
    "pageup": "page_up", "pgup": "page_up", "bildauf": "page_up",
    "pagedown": "page_down", "pgdn": "page_down", "bildab": "page_down",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "oben": "up", "unten": "down", "links": "left", "rechts": "right",
    "printscreen": "print_screen", "print": "print_screen", "druck": "print_screen", "prtsc": "print_screen",
    "pause": "pause", "capslock": "caps_lock", "numlock": "num_lock", "scrolllock": "scroll_lock",
    "menu": "menu", "apps": "menu",
    "play_pause": "media_play_pause", "playpause": "media_play_pause",
    "next": "media_next", "nexttrack": "media_next",
    "previous": "media_previous", "prev": "media_previous", "prevtrack": "media_previous",
    "volume_up": "media_volume_up", "volumeup": "media_volume_up",
    "volume_down": "media_volume_down", "volumedown": "media_volume_down",
    "volume_mute": "media_volume_mute", "mute": "media_volume_mute",
}

# Zeichen-Aliase, damit z. B. "+" und "," in Kombinationen nutzbar sind
_CHAR_ALIASES = {
    "plus": "+", "minus": "-", "comma": ",", "komma": ",", "period": ".", "punkt": ".",
    "slash": "/", "backslash": "\\", "semicolon": ";", "quote": "'", "equals": "=",
    "hash": "#", "raute": "#",
}

# Windows Virtual-Key-Codes für Tasten, die pynput nicht benennt
_WIN_VK = {
    **{f"num{i}": 0x60 + i for i in range(10)},
    "nummultiply": 0x6A, "numplus": 0x6B, "numminus": 0x6D, "numdecimal": 0x6E, "numdivide": 0x6F,
    "mediastop": 0xB2, "stop": 0xB2,
    **{f"f{i}": 0x70 + i - 1 for i in range(1, 25)},
}

MEDIA_KEYS = {
    "play_pause": "media_play_pause",
    "next": "media_next",
    "previous": "media_previous",
    "volume_up": "media_volume_up",
    "volume_down": "media_volume_down",
    "volume_mute": "media_volume_mute",
}


class Keyboard:
    def __init__(self) -> None:
        self.available = False
        self.error: str | None = None
        self._lock = threading.Lock()
        self._held: dict[str, list] = {}
        try:
            from pynput.keyboard import Controller, Key, KeyCode

            self._ctrl = Controller()
            self._Key = Key
            self._KeyCode = KeyCode
            self.available = True
        except Exception as exc:  # z. B. kein Display unter Linux
            first_line = (str(exc).strip().splitlines() or [type(exc).__name__])[0]
            self.error = f"Tastatursteuerung nicht verfügbar: {first_line}"
            log.warning(self.error)

    # ---------------------------------------------------------------- parsen
    def _key(self, token: str):
        name = token.strip().lower()
        if not name:
            raise ActionError("Leere Taste in Tastenkombination")
        if name in _CHAR_ALIASES:
            return self._KeyCode.from_char(_CHAR_ALIASES[name])
        if name in _KEY_NAMES and hasattr(self._Key, _KEY_NAMES[name]):
            return getattr(self._Key, _KEY_NAMES[name])
        if name.startswith("f") and name[1:].isdigit() and hasattr(self._Key, name):
            return getattr(self._Key, name)
        if IS_WINDOWS and name in _WIN_VK:
            return self._KeyCode.from_vk(_WIN_VK[name])
        if name.startswith("vk") and name[2:].isdigit():
            return self._KeyCode.from_vk(int(name[2:]))
        if len(name) == 1:
            return self._KeyCode.from_char(name)
        raise ActionError(f"Unbekannte Taste: „{token.strip()}“")

    def parse(self, spec: str) -> list:
        self._require()
        spec = (spec or "").strip()
        if not spec:
            raise ActionError("Keine Tasten angegeben")
        if spec == "+":
            return [self._KeyCode.from_char("+")]
        return [self._key(part) for part in spec.split("+")]

    def _require(self) -> None:
        if not self.available:
            raise ActionError(self.error or "Tastatursteuerung nicht verfügbar")

    # ------------------------------------------------------------- ausführen
    def tap(self, spec: str) -> None:
        keys = self.parse(spec)
        with self._lock:
            pressed = []
            try:
                for key in keys:
                    self._ctrl.press(key)
                    pressed.append(key)
                    time.sleep(0.015)
                time.sleep(0.03)
            finally:
                for key in reversed(pressed):
                    self._ctrl.release(key)
                    time.sleep(0.01)

    def hold(self, handle: str, spec: str) -> None:
        keys = self.parse(spec)
        self.release(handle)
        with self._lock:
            for key in keys:
                self._ctrl.press(key)
            self._held[handle] = keys

    def release(self, handle: str) -> None:
        keys = self._held.pop(handle, None)
        if not keys:
            return
        with self._lock:
            for key in reversed(keys):
                self._ctrl.release(key)

    def release_all(self) -> None:
        for handle in list(self._held):
            self.release(handle)

    def type_text(self, text: str, enter: bool = False) -> None:
        self._require()
        with self._lock:
            self._ctrl.type(text)
            if enter:
                self._ctrl.press(self._Key.enter)
                self._ctrl.release(self._Key.enter)

    def media(self, op: str) -> None:
        self._require()
        if op == "stop":
            if IS_WINDOWS:
                self.tap("mediastop")
            return
        attr = MEDIA_KEYS.get(op)
        if not attr or not hasattr(self._Key, attr):
            raise ActionError(f"Medientaste „{op}“ wird nicht unterstützt")
        key = getattr(self._Key, attr)
        with self._lock:
            self._ctrl.press(key)
            self._ctrl.release(key)
