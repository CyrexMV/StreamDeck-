"""Tastatur-Simulation: Tastenkombinationen, gehaltene Tasten, Text und Medientasten.

Unter Windows werden die Tasten direkt über die Windows-Funktion SendInput mit echten
virtuellen Tastencodes und Scancodes gesendet – genau wie bei einer echten Tastatur.
So erkennen auch Discord-Tastenbelegungen, das Snipping-Tool (Win+Umschalt+S) und
Spiele die Kombinationen. Auf anderen Systemen wird pynput verwendet.
"""

from __future__ import annotations

import logging
import sys
import threading
import time

from ..errors import ActionError

log = logging.getLogger("tabdeck.keyboard")

IS_WINDOWS = sys.platform == "win32"

# ---------------------------------------------------------------- Tastennamen
# Eingabe-Alias -> einheitlicher Name
ALIASES = {
    "ctrl": "ctrl", "control": "ctrl", "strg": "ctrl", "lctrl": "ctrl", "rctrl": "rctrl",
    "shift": "shift", "umschalt": "shift", "lshift": "shift", "rshift": "rshift",
    "alt": "alt", "lalt": "alt", "ralt": "altgr", "altgr": "altgr",
    "win": "win", "windows": "win", "cmd": "win", "super": "win", "meta": "win", "lwin": "win", "rwin": "rwin",
    "enter": "enter", "return": "enter", "eingabe": "enter",
    "esc": "esc", "escape": "esc",
    "tab": "tab", "space": "space", "leertaste": "space", "leer": "space",
    "backspace": "backspace", "rücktaste": "backspace",
    "delete": "delete", "del": "delete", "entf": "delete",
    "insert": "insert", "ins": "insert", "einfg": "insert",
    "home": "home", "pos1": "home", "end": "end", "ende": "end",
    "pageup": "page_up", "pgup": "page_up", "bildauf": "page_up", "page_up": "page_up",
    "pagedown": "page_down", "pgdn": "page_down", "bildab": "page_down", "page_down": "page_down",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "oben": "up", "unten": "down", "links": "left", "rechts": "right",
    "printscreen": "print_screen", "print": "print_screen", "druck": "print_screen", "prtsc": "print_screen",
    "pause": "pause", "capslock": "caps_lock", "numlock": "num_lock", "scrolllock": "scroll_lock",
    "menu": "menu", "apps": "menu",
    "play_pause": "play_pause", "playpause": "play_pause",
    "next": "next", "nexttrack": "next",
    "previous": "previous", "prev": "previous", "prevtrack": "previous",
    "stop": "stop", "mediastop": "stop",
    "volume_up": "volume_up", "volumeup": "volume_up",
    "volume_down": "volume_down", "volumedown": "volume_down",
    "volume_mute": "volume_mute", "mute": "volume_mute",
    "nummultiply": "nummultiply", "numplus": "numplus", "numminus": "numminus",
    "numdecimal": "numdecimal", "numdivide": "numdivide",
    **{f"num{i}": f"num{i}" for i in range(10)},
    **{f"f{i}": f"f{i}" for i in range(1, 25)},
}
CHAR_ALIASES = {
    "plus": "+", "minus": "-", "comma": ",", "komma": ",", "period": ".", "punkt": ".",
    "slash": "/", "backslash": "\\", "semicolon": ";", "quote": "'", "equals": "=",
    "hash": "#", "raute": "#",
}
MODIFIERS = {"ctrl", "rctrl", "shift", "rshift", "alt", "altgr", "win", "rwin"}


def parse_spec(spec: str) -> list[str]:
    """'ctrl+shift+m' -> ['ctrl', 'shift', 'char:m']"""
    spec = (spec or "").strip()
    if not spec:
        raise ActionError("Keine Tasten angegeben")
    parts = ["+"] if spec == "+" else spec.split("+")
    keys = []
    for part in parts:
        name = part.strip().lower()
        if not name:
            raise ActionError(f"Ungültige Tastenkombination: „{spec}“")
        if name in ALIASES:
            keys.append(ALIASES[name])
        elif name in CHAR_ALIASES:
            keys.append("char:" + CHAR_ALIASES[name])
        elif name.startswith("vk") and name[2:].isdigit():
            keys.append("vk:" + name[2:])
        elif len(name) == 1:
            keys.append("char:" + name)
        else:
            raise ActionError(f"Unbekannte Taste: „{part.strip()}“")
    return keys


# ============================================================ Windows-Backend
_VK = {
    "ctrl": 0xA2, "rctrl": 0xA3, "shift": 0xA0, "rshift": 0xA1, "alt": 0xA4, "altgr": 0xA5,
    "win": 0x5B, "rwin": 0x5C, "menu": 0x5D,
    "enter": 0x0D, "esc": 0x1B, "tab": 0x09, "space": 0x20, "backspace": 0x08,
    "delete": 0x2E, "insert": 0x2D, "home": 0x24, "end": 0x23, "page_up": 0x21, "page_down": 0x22,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "print_screen": 0x2C, "pause": 0x13, "caps_lock": 0x14, "num_lock": 0x90, "scroll_lock": 0x91,
    "play_pause": 0xB3, "next": 0xB0, "previous": 0xB1, "stop": 0xB2,
    "volume_up": 0xAF, "volume_down": 0xAE, "volume_mute": 0xAD,
    "nummultiply": 0x6A, "numplus": 0x6B, "numminus": 0x6D, "numdecimal": 0x6E, "numdivide": 0x6F,
    **{f"num{i}": 0x60 + i for i in range(10)},
    **{f"f{i}": 0x70 + i - 1 for i in range(1, 25)},
}
# Tasten, die Windows als „erweiterte“ Tasten erwartet
_EXTENDED = {0xA3, 0xA5, 0x5B, 0x5C, 0x5D, 0x2E, 0x2D, 0x24, 0x23, 0x21, 0x22, 0x26, 0x28, 0x25, 0x27,
             0x2C, 0x90, 0x6F, 0xB3, 0xB0, 0xB1, 0xB2, 0xAF, 0xAE, 0xAD}

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004


def _input_structs():
    import ctypes

    ULONG_PTR = ctypes.c_size_t

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", ctypes.c_uint16), ("wScan", ctypes.c_uint16), ("dwFlags", ctypes.c_uint32),
                    ("time", ctypes.c_uint32), ("dwExtraInfo", ULONG_PTR)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", ctypes.c_int32), ("dy", ctypes.c_int32), ("mouseData", ctypes.c_uint32),
                    ("dwFlags", ctypes.c_uint32), ("time", ctypes.c_uint32), ("dwExtraInfo", ULONG_PTR)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", ctypes.c_uint32), ("wParamL", ctypes.c_uint16), ("wParamH", ctypes.c_uint16)]

    class _UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", ctypes.c_uint32), ("u", _UNION)]

    return INPUT


class WindowsKeys:
    """Sendet Tasten über SendInput (wie eine echte Tastatur)."""

    def __init__(self, user32=None) -> None:
        import ctypes

        self._ctypes = ctypes
        self.INPUT = _input_structs()
        if user32 is None:
            user32 = ctypes.WinDLL("user32", use_last_error=True)  # type: ignore[attr-defined]
            user32.SendInput.argtypes = (ctypes.c_uint, ctypes.POINTER(self.INPUT), ctypes.c_int)
            user32.SendInput.restype = ctypes.c_uint
            user32.MapVirtualKeyW.argtypes = (ctypes.c_uint, ctypes.c_uint)
            user32.MapVirtualKeyW.restype = ctypes.c_uint
            user32.VkKeyScanW.argtypes = (ctypes.c_wchar,)
            user32.VkKeyScanW.restype = ctypes.c_short
        self.user32 = user32

    # ------------------------------------------------------------- Zuordnung
    def resolve(self, key: str) -> tuple[int, list[int]]:
        """Liefert (virtueller Tastencode, benötigte Zusatz-Modifikatoren)."""
        if key.startswith("vk:"):
            return int(key[3:]), []
        if key.startswith("char:"):
            ch = key[5:]
            res = self.user32.VkKeyScanW(ch)
            if res == -1 or (res & 0xFF) == 0xFF:
                raise ActionError(f"Die Taste „{ch}“ gibt es auf deinem Tastaturlayout nicht")
            vk, mods = res & 0xFF, (res >> 8) & 0xFF
            extra = []
            # Bei Buchstaben nie automatisch Umschalt ergänzen (Strg+M bleibt Strg+M)
            if not ch.isalpha():
                if mods & 1:
                    extra.append(_VK["shift"])
                if mods & 2:
                    extra.append(_VK["ctrl"])
                if mods & 4:
                    extra.append(_VK["alt"])
            return vk, extra
        if key in _VK:
            return _VK[key], []
        raise ActionError(f"Unbekannte Taste: {key}")

    def _event(self, vk: int, up: bool):
        scan = self.user32.MapVirtualKeyW(vk, 0) & 0xFF
        flags = KEYEVENTF_KEYUP if up else 0
        if vk in _EXTENDED:
            flags |= KEYEVENTF_EXTENDEDKEY
        inp = self.INPUT(type=INPUT_KEYBOARD)
        inp.ki.wVk, inp.ki.wScan, inp.ki.dwFlags = vk, scan, flags
        return inp

    def _unicode(self, ch: str, up: bool):
        inp = self.INPUT(type=INPUT_KEYBOARD)
        inp.ki.wVk, inp.ki.wScan = 0, ord(ch)
        inp.ki.dwFlags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if up else 0)
        return inp

    def send(self, events: list) -> None:
        if not events:
            return
        arr = (self.INPUT * len(events))(*events)
        sent = self.user32.SendInput(len(events), arr, self._ctypes.sizeof(self.INPUT))
        if sent != len(events):
            raise ActionError(
                "Windows hat die Tastatureingabe blockiert. Läuft das Zielprogramm als Administrator? "
                "Dann TabDeck ebenfalls als Administrator starten."
            )

    def vks(self, keys: list[str]) -> list[int]:
        """Reihenfolge: Modifikatoren zuerst, dann die eigentlichen Tasten."""
        out: list[int] = []
        for key in keys:
            vk, extra = self.resolve(key)
            for e in extra:
                if e not in out:
                    out.insert(0, e)
            if vk not in out:
                out.append(vk)
        return out

    def down(self, vks: list[int]) -> None:
        self.send([self._event(vk, False) for vk in vks])

    def up(self, vks: list[int]) -> None:
        self.send([self._event(vk, True) for vk in reversed(vks)])

    def tap(self, vks: list[int]) -> None:
        mods = [v for v in vks if v in (0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x5B, 0x5C)]
        main = [v for v in vks if v not in mods]
        try:
            if mods:
                self.down(mods)
                time.sleep(0.02)
            for vk in main:
                self.send([self._event(vk, False)])
                time.sleep(0.04)  # kurz halten, damit Discord & Co. die Taste sicher erkennen
                self.send([self._event(vk, True)])
                time.sleep(0.01)
        finally:
            if mods:
                time.sleep(0.02)
                self.up(mods)

    def type_text(self, text: str) -> None:
        events = []
        for ch in text.replace("\r\n", "\n"):
            if ch == "\n":
                events += [self._event(0x0D, False), self._event(0x0D, True)]
            else:
                events += [self._unicode(ch, False), self._unicode(ch, True)]
        for i in range(0, len(events), 40):
            self.send(events[i:i + 40])
            time.sleep(0.005)


# ============================================================ pynput-Backend
_PYNPUT = {
    "ctrl": "ctrl_l", "rctrl": "ctrl_r", "shift": "shift_l", "rshift": "shift_r", "alt": "alt_l",
    "altgr": "alt_gr", "win": "cmd", "rwin": "cmd_r", "print_screen": "print_screen",
    "play_pause": "media_play_pause", "next": "media_next", "previous": "media_previous",
    "volume_up": "media_volume_up", "volume_down": "media_volume_down", "volume_mute": "media_volume_mute",
}


class PynputKeys:
    def __init__(self) -> None:
        from pynput.keyboard import Controller, Key, KeyCode

        self._ctrl, self._Key, self._KeyCode = Controller(), Key, KeyCode

    def vks(self, keys: list[str]) -> list:
        out = []
        for key in keys:
            if key.startswith("char:"):
                out.append(self._KeyCode.from_char(key[5:]))
            elif key.startswith("vk:"):
                out.append(self._KeyCode.from_vk(int(key[3:])))
            else:
                attr = _PYNPUT.get(key, key)
                if not hasattr(self._Key, attr):
                    raise ActionError(f"Taste „{key}“ wird auf diesem System nicht unterstützt")
                out.append(getattr(self._Key, attr))
        return out

    def down(self, keys: list) -> None:
        for k in keys:
            self._ctrl.press(k)

    def up(self, keys: list) -> None:
        for k in reversed(keys):
            self._ctrl.release(k)

    def tap(self, keys: list) -> None:
        try:
            self.down(keys)
            time.sleep(0.04)
        finally:
            self.up(keys)

    def type_text(self, text: str) -> None:
        self._ctrl.type(text)


# ================================================================== Fassade
class Keyboard:
    def __init__(self) -> None:
        self.available = False
        self.error: str | None = None
        self.backend_name = ""
        self._lock = threading.Lock()
        self._held: dict[str, list] = {}
        try:
            if IS_WINDOWS:
                self._b = WindowsKeys()
                self.backend_name = "Windows SendInput"
            else:
                self._b = PynputKeys()
                self.backend_name = "pynput"
            self.available = True
        except Exception as exc:  # z. B. kein Display unter Linux
            first_line = (str(exc).strip().splitlines() or [type(exc).__name__])[0]
            self.error = f"Tastatursteuerung nicht verfügbar: {first_line}"
            log.warning(self.error)

    def _require(self) -> None:
        if not self.available:
            raise ActionError(self.error or "Tastatursteuerung nicht verfügbar")

    def parse(self, spec: str) -> list:
        self._require()
        return self._b.vks(parse_spec(spec))

    def tap(self, spec: str) -> None:
        keys = self.parse(spec)
        with self._lock:
            self._b.tap(keys)

    def hold(self, handle: str, spec: str) -> None:
        keys = self.parse(spec)
        self.release(handle)
        with self._lock:
            self._b.down(keys)
            self._held[handle] = keys

    def release(self, handle: str) -> None:
        keys = self._held.pop(handle, None)
        if not keys:
            return
        with self._lock:
            self._b.up(keys)

    def release_all(self) -> None:
        for handle in list(self._held):
            try:
                self.release(handle)
            except Exception:
                pass

    def type_text(self, text: str, enter: bool = False) -> None:
        self._require()
        with self._lock:
            if text:
                self._b.type_text(text)
        if enter:
            self.tap("enter")

    def media(self, op: str) -> None:
        names = {"play_pause": "play_pause", "next": "next", "previous": "previous", "stop": "stop",
                 "volume_up": "volume_up", "volume_down": "volume_down", "volume_mute": "volume_mute"}
        if op not in names:
            raise ActionError(f"Medientaste „{op}“ wird nicht unterstützt")
        self.tap(names[op])
