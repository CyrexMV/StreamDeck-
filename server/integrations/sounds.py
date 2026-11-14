"""Eigene Sounds (Soundboard) abspielen.

Die Dateien liegen im Sound-Ordner (Windows: %APPDATA%\\TabDeck\\sounds). Abgespielt wird
unter Windows über die eingebaute Windows-Multimedia-Schnittstelle (MCI) – ohne Zusatzprogramme.
MP3 und WAV funktionieren immer, WMA/M4A je nach installierten Windows-Codecs.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import itertools
import logging
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

from ..errors import ActionError

log = logging.getLogger("tabdeck.sounds")

IS_WINDOWS = sys.platform == "win32"
SOUND_EXTENSIONS = {".mp3", ".wav", ".wma", ".m4a", ".aac", ".ogg", ".flac"}
MAX_UPLOAD = 5 * 1024 * 1024


class SoundPlayer:
    def __init__(self, folder: Path, on_change: Callable[[], None]) -> None:
        self.folder = folder
        self._on_change = on_change
        self._ids = itertools.count(1)
        self._playing: dict[int, dict] = {}  # id -> {"file", "stop": Event}
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.warning("Sound-Ordner nicht anlegbar: %s", exc)

    # ------------------------------------------------------------ Dateien
    def list(self) -> list[dict]:
        if not self.folder.exists():
            return []
        files = [p for p in self.folder.iterdir() if p.is_file() and p.suffix.lower() in SOUND_EXTENSIONS]
        return [{"name": p.name, "size": p.stat().st_size} for p in sorted(files, key=lambda p: p.name.lower())]

    def resolve(self, name: str) -> Path:
        if not name:
            raise ActionError("Kein Sound ausgewählt")
        path = (self.folder / name).resolve()
        if path.parent != self.folder.resolve():
            raise ActionError("Ungültiger Dateiname")
        if not path.is_file():
            raise ActionError(f"Sound „{name}“ nicht gefunden – liegt er im Sound-Ordner?")
        return path

    def save_upload(self, name: str, data: bytes) -> str:
        name = os.path.basename(name or "").strip()
        if not name or Path(name).suffix.lower() not in SOUND_EXTENSIONS:
            raise ActionError("Nur MP3-, WAV-, WMA-, M4A-, OGG- oder FLAC-Dateien")
        if len(data) > MAX_UPLOAD:
            raise ActionError("Datei ist zu groß (max. 5 MB beim Hochladen – größere Dateien direkt in den Ordner kopieren)")
        self.folder.mkdir(parents=True, exist_ok=True)
        (self.folder / name).write_bytes(data)
        return name

    @property
    def playing_files(self) -> list[str]:
        with self._lock:
            return sorted({p["file"] for p in self._playing.values()})

    def _changed(self) -> None:
        if self._loop:
            self._loop.call_soon_threadsafe(self._on_change)

    # ----------------------------------------------------------- Abspielen
    async def play(self, name: str, volume: float = 100, mode: str = "restart") -> None:
        path = self.resolve(name)
        self._loop = asyncio.get_running_loop()
        if mode == "toggle" and name in self.playing_files:
            self.stop(name)
            return
        if mode in ("restart", "toggle"):
            self.stop(name)
        sid = next(self._ids)
        stop = threading.Event()
        started: concurrent.futures.Future = concurrent.futures.Future()
        with self._lock:
            self._playing[sid] = {"file": name, "stop": stop}
        target = self._run_windows if IS_WINDOWS else self._run_other
        threading.Thread(target=target, args=(sid, path, max(0.0, min(100.0, float(volume))), stop, started),
                         daemon=True, name=f"sound-{sid}").start()
        try:
            await asyncio.wait_for(asyncio.wrap_future(started), timeout=8)
        except asyncio.TimeoutError:
            raise ActionError("Der Sound startet nicht") from None
        self._changed()

    def stop(self, name: str | None = None) -> None:
        with self._lock:
            for item in self._playing.values():
                if name is None or item["file"] == name:
                    item["stop"].set()

    def _finished(self, sid: int) -> None:
        with self._lock:
            self._playing.pop(sid, None)
        self._changed()

    # Windows: MCI (winmm.dll)
    def _run_windows(self, sid: int, path: Path, volume: float, stop: threading.Event, started) -> None:
        import ctypes

        winmm = ctypes.WinDLL("winmm")  # type: ignore[attr-defined]
        send = winmm.mciSendStringW
        send.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p)
        send.restype = ctypes.c_uint
        get_error = winmm.mciGetErrorStringW
        get_error.argtypes = (ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint)
        alias = f"tabdeck{sid}"

        def cmd(text: str) -> tuple[int, str]:
            buf = ctypes.create_unicode_buffer(256)
            return send(text, buf, 256, None), buf.value

        def error_text(code: int) -> str:
            buf = ctypes.create_unicode_buffer(256)
            get_error(code, buf, 256)
            return buf.value or f"Fehler {code}"

        opened = False
        try:
            err, _ = cmd(f'open "{path}" type mpegvideo alias {alias}')
            if err:
                raise ActionError(f"Sound kann nicht geöffnet werden: {error_text(err)}")
            opened = True
            cmd(f"setaudio {alias} volume to {int(volume * 10)}")
            err, _ = cmd(f"play {alias}")
            if err:
                raise ActionError(f"Sound kann nicht abgespielt werden: {error_text(err)}")
            started.set_result(True)
            stop.wait(0.15)
            while not stop.wait(0.1):
                err, mode = cmd(f"status {alias} mode")
                if err or mode == "stopped":
                    break
        except Exception as exc:
            if not started.done():
                started.set_exception(exc if isinstance(exc, ActionError) else ActionError(str(exc)))
        finally:
            if opened:
                cmd(f"stop {alias}")
                cmd(f"close {alias}")
            self._finished(sid)

    # Linux/macOS (zum Testen): vorhandenes Wiedergabeprogramm
    def _run_other(self, sid: int, path: Path, volume: float, stop: threading.Event, started) -> None:
        players = [
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(int(volume)), str(path)],
            ["afplay", "-v", str(volume / 100), str(path)],
            ["paplay", str(path)], ["mpg123", "-q", str(path)], ["aplay", "-q", str(path)],
        ]
        proc = None
        try:
            for args in players:
                if shutil.which(args[0]):
                    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    break
            if proc is None:
                raise ActionError("Kein Programm zum Abspielen gefunden (unter Windows nicht nötig)")
            started.set_result(True)
            while proc.poll() is None and not stop.wait(0.1):
                pass
        except Exception as exc:
            if not started.done():
                started.set_exception(exc if isinstance(exc, ActionError) else ActionError(str(exc)))
        finally:
            if proc and proc.poll() is None:
                proc.terminate()
            self._finished(sid)
