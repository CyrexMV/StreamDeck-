"""Windows-Lautstärkesteuerung (System, Mikrofon, einzelne Programme) über pycaw."""

from __future__ import annotations

import asyncio
import logging
import sys
from concurrent.futures import ThreadPoolExecutor

from ..errors import ActionError

log = logging.getLogger("tabdeck.audio")


def _com_init() -> None:
    try:
        import comtypes

        comtypes.CoInitialize()
    except Exception:
        pass


class AudioController:
    def __init__(self) -> None:
        self.available = False
        self.error: str | None = None
        # COM-Objekte immer im selben Thread benutzen
        self._executor = ThreadPoolExecutor(max_workers=1, initializer=_com_init, thread_name_prefix="audio")
        if sys.platform != "win32":
            self.error = "Lautstärkesteuerung gibt es nur unter Windows"
            return
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # noqa: F401

            self._AU = AudioUtilities
            self._IEV = IAudioEndpointVolume
            self.available = True
        except Exception as exc:
            self.error = f"pycaw nicht verfügbar: {exc}"
            log.warning(self.error)

    async def _run(self, fn, *args):
        if not self.available:
            raise ActionError(self.error or "Lautstärkesteuerung nicht verfügbar")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, fn, *args)

    # ------------------------------------------------------------ Endpunkte
    def _endpoint(self, mic: bool):
        device = self._AU.GetMicrophone() if mic else self._AU.GetSpeakers()
        if device is None:
            raise ActionError("Kein Mikrofon gefunden" if mic else "Kein Ausgabegerät gefunden")
        endpoint = getattr(device, "EndpointVolume", None)
        if endpoint is not None:
            return endpoint
        from ctypes import POINTER, cast

        from comtypes import CLSCTX_ALL

        raw = device if hasattr(device, "Activate") else getattr(device, "_dev", device)
        interface = raw.Activate(self._IEV._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(self._IEV))

    def _sessions(self, app: str):
        wanted = (app or "").lower().removesuffix(".exe")
        found = []
        for session in self._AU.GetAllSessions():
            proc = session.Process
            if proc is None:
                continue
            name = proc.name().lower().removesuffix(".exe")
            if name == wanted:
                found.append(session.SimpleAudioVolume)
        if not found:
            raise ActionError(f"„{app}“ spielt gerade keinen Ton ab")
        return found

    # --------------------------------------------------------------- Aktion
    def _apply(self, target: str, app: str, op: str, step: float):
        step = max(0.0, min(100.0, float(step))) / 100.0
        if target in ("master", "mic"):
            ep = self._endpoint(mic=target == "mic")
            level = ep.GetMasterVolumeLevelScalar()
            muted = bool(ep.GetMute())
            if op == "up":
                ep.SetMasterVolumeLevelScalar(min(1.0, level + step), None)
                if muted:
                    ep.SetMute(0, None)
            elif op == "down":
                ep.SetMasterVolumeLevelScalar(max(0.0, level - step), None)
            elif op == "set":
                ep.SetMasterVolumeLevelScalar(step, None)
            elif op == "toggle_mute":
                ep.SetMute(0 if muted else 1, None)
            elif op == "mute":
                ep.SetMute(1, None)
            elif op == "unmute":
                ep.SetMute(0, None)
            else:
                raise ActionError(f"Unbekannte Lautstärke-Aktion: {op}")
            return
        if target == "app":
            for vol in self._sessions(app):
                level = vol.GetMasterVolume()
                muted = bool(vol.GetMute())
                if op == "up":
                    vol.SetMasterVolume(min(1.0, level + step), None)
                    if muted:
                        vol.SetMute(0, None)
                elif op == "down":
                    vol.SetMasterVolume(max(0.0, level - step), None)
                elif op == "set":
                    vol.SetMasterVolume(step, None)
                elif op == "toggle_mute":
                    vol.SetMute(0 if muted else 1, None)
                elif op == "mute":
                    vol.SetMute(1, None)
                elif op == "unmute":
                    vol.SetMute(0, None)
                else:
                    raise ActionError(f"Unbekannte Lautstärke-Aktion: {op}")
            return
        raise ActionError(f"Unbekanntes Lautstärke-Ziel: {target}")

    async def apply(self, target: str, app: str, op: str, step: float = 5) -> None:
        await self._run(self._apply, target, app, op, step)

    # ------------------------------------------------------------ Zustand
    def _snapshot(self) -> dict:
        state: dict = {"available": True, "master": None, "mic": None, "apps": {}}
        try:
            ep = self._endpoint(mic=False)
            state["master"] = {"level": round(ep.GetMasterVolumeLevelScalar() * 100), "muted": bool(ep.GetMute())}
        except Exception:
            pass
        try:
            ep = self._endpoint(mic=True)
            state["mic"] = {"level": round(ep.GetMasterVolumeLevelScalar() * 100), "muted": bool(ep.GetMute())}
        except Exception:
            pass
        try:
            for session in self._AU.GetAllSessions():
                if session.Process is None:
                    continue
                name = session.Process.name()
                vol = session.SimpleAudioVolume
                state["apps"][name.lower().removesuffix(".exe")] = {
                    "name": name,
                    "level": round(vol.GetMasterVolume() * 100),
                    "muted": bool(vol.GetMute()),
                }
        except Exception:
            pass
        return state

    async def snapshot(self) -> dict:
        if not self.available:
            return {"available": False}
        try:
            return await self._run(self._snapshot)
        except Exception as exc:
            log.debug("Audio-Snapshot fehlgeschlagen: %s", exc)
            return {"available": True}
