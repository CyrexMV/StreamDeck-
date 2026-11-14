"""Programme/Dateien/URLs öffnen, Befehle ausführen, Energie-Optionen und Systemwerte."""

from __future__ import annotations

import logging
import os
import re
import shlex
import subprocess
import sys
import webbrowser

from ..errors import ActionError

log = logging.getLogger("tabdeck.system")

IS_WINDOWS = sys.platform == "win32"
_DETACHED = 0x00000008 | 0x00000200 if IS_WINDOWS else 0  # DETACHED_PROCESS | NEW_PROCESS_GROUP


class SystemController:
    def __init__(self) -> None:
        self.stats_error: str | None = None
        self._last_times = None
        try:
            import psutil

            self._psutil = psutil
            psutil.cpu_percent(interval=None)  # erste Messung initialisieren
        except Exception as exc:
            self._psutil = None
            if not IS_WINDOWS:
                self.stats_error = f"psutil fehlt: {exc}"

    # ---------------------------------------------------------------- Öffnen
    def open(self, target: str, args: str = "") -> None:
        target = (target or "").strip().strip('"')
        if not target:
            raise ActionError("Kein Ziel zum Öffnen angegeben")
        target = os.path.expandvars(os.path.expanduser(target))
        # Manche Programme (z. B. OBS) brauchen ihren eigenen Ordner als Arbeitsverzeichnis
        cwd = os.path.dirname(target) if os.path.isfile(target) else None
        try:
            if args:
                cmd = [target, *shlex.split(args, posix=not IS_WINDOWS)]
                subprocess.Popen(cmd, cwd=cwd, creationflags=_DETACHED, close_fds=True)
            elif IS_WINDOWS:
                if cwd:
                    os.startfile(target, cwd=cwd)  # type: ignore[attr-defined]
                else:
                    os.startfile(target)  # type: ignore[attr-defined]
            elif re.match(r"^[a-z][a-z0-9+.-]+:", target, re.I):  # Links wie https://, spotify:track:…
                webbrowser.open(target)
            else:
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.Popen([opener, target], start_new_session=True)
        except FileNotFoundError:
            raise ActionError(f"Nicht gefunden: {target}") from None
        except OSError as exc:
            raise ActionError(f"Konnte „{target}“ nicht öffnen: {exc.strerror or exc}") from None

    def command(self, command: str) -> None:
        command = (command or "").strip()
        if not command:
            raise ActionError("Kein Befehl angegeben")
        kwargs = {"creationflags": 0x08000000} if IS_WINDOWS else {"start_new_session": True}  # ohne Konsolenfenster
        subprocess.Popen(command, shell=True, **kwargs)

    # -------------------------------------------------------------- Energie
    def power(self, op: str) -> None:
        if not IS_WINDOWS:
            raise ActionError("Energie-Aktionen gibt es nur unter Windows")
        import ctypes

        if op == "lock":
            ctypes.windll.user32.LockWorkStation()  # type: ignore[attr-defined]
            return
        if op == "monitor_off":
            # HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2 = aus
            ctypes.windll.user32.PostMessageW(0xFFFF, 0x0112, 0xF170, 2)  # type: ignore[attr-defined]
            return
        if op == "sleep":
            # Hibernate=False, Force=True, WakeupEventsDisabled=False
            ctypes.windll.powrprof.SetSuspendState(False, True, False)  # type: ignore[attr-defined]
            return
        commands = {
            "shutdown": "shutdown /s /t 0",
            "restart": "shutdown /r /t 0",
            "logoff": "shutdown /l",
        }
        if op not in commands:
            raise ActionError(f"Unbekannte Energie-Aktion: {op}")
        self.command(commands[op])

    # ---------------------------------------------------------- Systemwerte
    def stats(self) -> dict:
        try:
            if self._psutil:
                return {
                    "cpu": round(self._psutil.cpu_percent(interval=None)),
                    "ram": round(self._psutil.virtual_memory().percent),
                }
            if IS_WINDOWS:
                return self._win_stats()
        except Exception as exc:
            log.debug("Systemwerte nicht lesbar: %s", exc)
        return {}

    def _win_stats(self) -> dict:
        """CPU/RAM direkt über die Windows-API (falls psutil fehlt)."""
        import ctypes
        from ctypes import wintypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD)] + [
                (n, ctypes.c_ulonglong) for n in ("t1", "a1", "t2", "a2", "t3", "a3", "a4")]

        mem = MEMORYSTATUSEX()
        mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))  # type: ignore[attr-defined]

        idle, kernel, user = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
        ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))  # type: ignore[attr-defined]
        val = lambda ft: (ft.dwHighDateTime << 32) | ft.dwLowDateTime  # noqa: E731
        now = (val(idle), val(kernel), val(user))
        cpu = None
        if self._last_times:
            d_idle, d_kernel, d_user = (n - o for n, o in zip(now, self._last_times))
            total = d_kernel + d_user  # Kernel-Zeit enthält die Leerlaufzeit
            cpu = round(100 * (total - d_idle) / total) if total else 0
        self._last_times = now
        out = {"ram": int(mem.dwMemoryLoad)}
        if cpu is not None:
            out["cpu"] = max(0, min(100, cpu))
        return out
