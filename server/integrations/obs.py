"""Asynchroner Client für obs-websocket v5 (in OBS Studio 28+ eingebaut).

Hält die Verbindung automatisch aufrecht und verfolgt den OBS-Zustand (aktive Szene,
Aufnahme, Stream, stumme Quellen, sichtbare Quellen …), damit die Tasten auf dem
Tablet live anzeigen können, was gerade aktiv ist.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import math
import uuid
from typing import Any, Awaitable, Callable

import aiohttp

from ..errors import ActionError

log = logging.getLogger("tabdeck.obs")


def auth_response(password: str, salt: str, challenge: str) -> str:
    secret = base64.b64encode(hashlib.sha256((password + salt).encode()).digest()).decode()
    return base64.b64encode(hashlib.sha256((secret + challenge).encode()).digest()).decode()


class OBSError(ActionError):
    pass


# Quellenarten, die OBS immer im Audio-Mixer zeigt (Audio-Geräte, Anwendungsaudio, Mediendateien)
AUDIO_KINDS = {
    "wasapi_input_capture", "wasapi_output_capture", "wasapi_process_output_capture",
    "coreaudio_input_capture", "coreaudio_output_capture", "sck_audio_capture",
    "pulse_input_capture", "pulse_output_capture", "alsa_input_capture", "jack_output_capture",
    "asio_input_capture", "ffmpeg_source", "vlc_source",
}
# Bild-/Videoquellen, die nur dann im Audio-Mixer erscheinen, wenn Ton in den Eigenschaften aktiviert ist
AUDIO_SETTING_KINDS = {
    "browser_source": "reroute_audio",   # „Audio über OBS steuern“
    "game_capture": "capture_audio",     # „Audio aufnehmen“
    "window_capture": "capture_audio",
}


def _db(value) -> float:
    """OBS liefert für „stumm“ (Faktor 0) -inf bzw. null – auf −100 dB abbilden."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return -100.0
    return -100.0 if v != v or v < -100 else round(v, 1)


class OBSClient:
    RECONNECT_DELAY = 3

    def __init__(self, on_change: Callable[[dict], Awaitable[None]]) -> None:
        self._on_change = on_change
        self._cfg: dict = {}
        self._task: asyncio.Task | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._pending: dict[str, asyncio.Future] = {}
        self._notify_handle: asyncio.TimerHandle | None = None
        self._reset_state()

    def _reset_state(self, error: str | None = None) -> None:
        self.state: dict[str, Any] = {
            "enabled": bool(self._cfg.get("enabled")),
            "connected": False,
            "error": error,
            "current_scene": None,
            "scenes": [],
            "inputs": [],
            "muted": {},
            "volumes": {},
            "active_inputs": [],      # Quellen, die gerade im OBS-Audio-Mixer aktiv sind
            "active_known": False,    # False, solange OBS noch keine Pegel gemeldet hat
            "sources": {},
            "recording": False,
            "record_paused": False,
            "streaming": False,
            "virtualcam": False,
            "replay_buffer": False,
            "studio_mode": False,
        }
        self._item_ids: dict[str, dict[int, str]] = {}
        self.meters: dict[str, int] = {}
        self._kinds: dict[str, str] = {}
        self._audio_on: dict[str, bool] = {}
        self._heard: set[str] = set()

    # ------------------------------------------------------------- Lebenszyklus
    def configure(self, cfg: dict) -> None:
        new = {k: cfg.get(k) for k in ("enabled", "host", "port", "password")}
        if new == self._cfg and self._task and not self._task.done():
            return
        self._cfg = new
        self.restart()

    def restart(self) -> None:
        if self._task:
            self._task.cancel()
        self._reset_state()
        self._notify()
        if self._cfg.get("enabled"):
            self._task = asyncio.create_task(self._run(), name="obs")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    def _notify(self) -> None:
        """Zustandsänderungen kurz bündeln, damit nicht jedes Event einzeln gesendet wird."""
        if self._notify_handle:
            return
        loop = asyncio.get_running_loop()

        def fire() -> None:
            self._notify_handle = None
            asyncio.create_task(self._on_change(dict(self.state)))

        self._notify_handle = loop.call_later(0.05, fire)

    async def _run(self) -> None:
        url = f"ws://{self._cfg.get('host') or '127.0.0.1'}:{int(self._cfg.get('port') or 4455)}"
        last_error = None
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(
                        url, protocols=("obswebsocket.json",), heartbeat=15, timeout=aiohttp.ClientWSTimeout(ws_close=5)
                    ) as ws:
                        await self._handshake(ws)
                        self._ws = ws
                        self.state.update(connected=True, error=None)
                        last_error = None
                        log.info("Mit OBS verbunden (%s)", url)
                        self._notify()
                        refresh = asyncio.create_task(self._refresh_all())
                        try:
                            await self._read_loop(ws)
                        finally:
                            refresh.cancel()
                        if ws.close_code == 4009:
                            raise OBSError("OBS-Passwort falsch")
                        last_error = "Verbindung zu OBS getrennt – verbinde neu …"
            except asyncio.CancelledError:
                self._ws = None
                self._fail_pending("Verbindung beendet")
                raise
            except OBSError as exc:
                last_error = str(exc)
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
                last_error = "OBS nicht erreichbar – läuft OBS und ist der WebSocket-Server aktiviert?"
                log.debug("OBS-Verbindung fehlgeschlagen: %s", exc)
            except Exception as exc:  # unerwartete Protokollfehler
                last_error = f"OBS-Fehler: {exc}"
                log.exception("OBS-Fehler")
            self._ws = None
            self._fail_pending("Verbindung zu OBS getrennt")
            if self.state.get("connected"):
                log.info("Verbindung zu OBS getrennt")
            self._reset_state(last_error)
            self._notify()
            await asyncio.sleep(self.RECONNECT_DELAY)

    async def _handshake(self, ws) -> None:
        hello = await ws.receive(timeout=5)
        if hello.type != aiohttp.WSMsgType.TEXT:
            if ws.close_code == 4009 or hello.data == 4009:
                raise OBSError("OBS-Passwort falsch")
            raise OBSError("Unerwartete Antwort von OBS")
        data = hello.json()
        if data.get("op") != 0:
            raise OBSError("Unerwartete Begrüßung von OBS")
        # Alle normalen Events + InputVolumeMeters (Pegel aller Quellen, die im OBS-Audio-Mixer aktiv sind)
        identify: dict[str, Any] = {"rpcVersion": 1, "eventSubscriptions": 2047 | (1 << 16)}
        auth = data["d"].get("authentication")
        if auth:
            password = self._cfg.get("password") or ""
            if not password:
                raise OBSError("OBS verlangt ein Passwort – bitte in den Einstellungen eintragen")
            identify["authentication"] = auth_response(password, auth["salt"], auth["challenge"])
        await ws.send_json({"op": 1, "d": identify})
        msg = await ws.receive(timeout=5)
        if msg.type != aiohttp.WSMsgType.TEXT:
            if ws.close_code == 4009 or msg.data == 4009:
                raise OBSError("OBS-Passwort falsch")
            raise OBSError(f"OBS hat die Verbindung abgelehnt ({ws.close_code or msg.data})")
        if msg.json().get("op") != 2:
            raise OBSError("Anmeldung bei OBS fehlgeschlagen")

    async def _read_loop(self, ws) -> None:
        async for msg in ws:
            if msg.type != aiohttp.WSMsgType.TEXT:
                break
            data = msg.json()
            op, d = data.get("op"), data.get("d", {})
            if op == 7:
                fut = self._pending.pop(d.get("requestId"), None)
                if fut and not fut.done():
                    fut.set_result(d)
            elif op == 5:
                try:
                    await self._handle_event(d.get("eventType"), d.get("eventData") or {})
                except Exception:
                    log.exception("Fehler beim Verarbeiten des OBS-Events %s", d.get("eventType"))

    def _fail_pending(self, reason: str) -> None:
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(OBSError(reason))
        self._pending.clear()

    # ------------------------------------------------------------- Anfragen
    async def request(self, request_type: str, data: dict | None = None, timeout: float = 5) -> dict:
        ws = self._ws
        if ws is None or ws.closed:
            raise OBSError(self.state.get("error") or "Nicht mit OBS verbunden")
        request_id = uuid.uuid4().hex
        fut = asyncio.get_running_loop().create_future()
        self._pending[request_id] = fut
        payload: dict[str, Any] = {"requestType": request_type, "requestId": request_id}
        if data:
            payload["requestData"] = data
        await ws.send_json({"op": 6, "d": payload})
        try:
            resp = await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError:
            self._pending.pop(request_id, None)
            raise OBSError(f"OBS antwortet nicht ({request_type})") from None
        status = resp.get("requestStatus", {})
        if not status.get("result"):
            comment = status.get("comment") or f"Code {status.get('code')}"
            raise OBSError(f"OBS: {comment}")
        return resp.get("responseData") or {}

    # -------------------------------------------------------- Zustand laden
    async def _refresh_all(self) -> None:
        try:
            await asyncio.gather(
                self._refresh_scenes(),
                self._refresh_inputs(),
                self._refresh_outputs(),
                return_exceptions=True,
            )
        finally:
            self._notify()

    async def _refresh_outputs(self) -> None:
        async def get(req: str, key: str, field: str = "outputActive") -> None:
            try:
                self.state[key] = bool((await self.request(req)).get(field))
            except OBSError:
                pass

        await asyncio.gather(
            get("GetStreamStatus", "streaming"),
            get("GetVirtualCamStatus", "virtualcam"),
            get("GetReplayBufferStatus", "replay_buffer"),
            get("GetStudioModeEnabled", "studio_mode", "studioModeEnabled"),
        )
        try:
            rec = await self.request("GetRecordStatus")
            self.state["recording"] = bool(rec.get("outputActive"))
            self.state["record_paused"] = bool(rec.get("outputPaused"))
        except OBSError:
            pass

    async def _refresh_scenes(self) -> None:
        data = await self.request("GetSceneList")
        # OBS liefert die Szenen von unten nach oben
        scenes = [s["sceneName"] for s in reversed(data.get("scenes", []))]
        self.state["scenes"] = scenes
        self.state["current_scene"] = data.get("currentProgramSceneName")
        self.state["sources"] = {k: v for k, v in self.state["sources"].items() if k in scenes}
        await asyncio.gather(*(self._refresh_scene_items(s) for s in scenes), return_exceptions=True)
        self._notify()

    async def _refresh_scene_items(self, scene: str) -> None:
        data = await self.request("GetSceneItemList", {"sceneName": scene})
        ids: dict[int, str] = {}
        visible: dict[str, bool] = {}
        for item in data.get("sceneItems", []):
            ids[item["sceneItemId"]] = item["sourceName"]
            visible[item["sourceName"]] = bool(item.get("sceneItemEnabled"))
        self._item_ids[scene] = ids
        self.state["sources"][scene] = visible
        self._notify()

    async def _refresh_inputs(self) -> None:
        data = await self.request("GetInputList")
        names = [i["inputName"] for i in data.get("inputs", [])]
        self._kinds = {i["inputName"]: i.get("unversionedInputKind") or i.get("inputKind") or "" for i in data.get("inputs", [])}
        await asyncio.gather(*(self._load_audio_setting(n) for n in names if self._kinds.get(n) in AUDIO_SETTING_KINDS),
                             return_exceptions=True)

        async def mute_state(name: str):
            try:
                return name, bool((await self.request("GetInputMute", {"inputName": name})).get("inputMuted"))
            except OBSError:
                return name, None  # Quelle ohne Ton

        results = await asyncio.gather(*(mute_state(n) for n in names))
        self.state["muted"] = {n: m for n, m in results if m is not None}
        self.state["inputs"] = [n for n, m in results if m is not None]

        async def volume(name: str):
            try:
                return name, _db((await self.request("GetInputVolume", {"inputName": name})).get("inputVolumeDb"))
            except OBSError:
                return name, None

        vols = await asyncio.gather(*(volume(n) for n in self.state["inputs"]))
        self.state["volumes"] = {n: v for n, v in vols if v is not None}
        self._update_active()
        self._notify()

    async def _load_audio_setting(self, name: str) -> None:
        key = AUDIO_SETTING_KINDS[self._kinds[name]]
        settings = (await self.request("GetInputSettings", {"inputName": name})).get("inputSettings") or {}
        self._audio_on[name] = bool(settings.get(key, False))

    def _in_mixer(self, name: str) -> bool:
        """Würde OBS diese Quelle im Audio-Mixer anzeigen?"""
        kind = self._kinds.get(name, "")
        if kind in AUDIO_KINDS:
            return True                       # reine Audioquellen, Mediendateien
        if kind in AUDIO_SETTING_KINDS:
            return self._audio_on.get(name, False)  # Ton in den Eigenschaften eingeschaltet?
        return name in self._heard            # sonst (z. B. Webcam): nur wenn wirklich Ton ankommt

    def _update_active(self) -> None:
        meters = self.meters
        order = [n for n in self.state["inputs"] if n in meters] + [n for n in meters if n not in self.state["inputs"]]
        active = [n for n in order if self._in_mixer(n)]
        if active != self.state["active_inputs"] or not self.state["active_known"]:
            self.state["active_inputs"] = active
            self.state["active_known"] = bool(meters) or self.state["active_known"]
            self._notify()

    # ---------------------------------------------------------------- Events
    async def _handle_event(self, event: str, data: dict) -> None:
        s = self.state
        if event == "InputVolumeMeters":
            self._on_meters(data.get("inputs") or [])
            return
        if event == "CurrentProgramSceneChanged":
            s["current_scene"] = data.get("sceneName")
        elif event in ("SceneListChanged", "SceneNameChanged", "SceneCreated", "SceneRemoved"):
            asyncio.create_task(self._safe(self._refresh_scenes()))
        elif event == "RecordStateChanged":
            state = data.get("outputState", "")
            s["recording"] = bool(data.get("outputActive"))
            if state == "OBS_WEBSOCKET_OUTPUT_PAUSED":
                s["record_paused"] = True
            elif state in ("OBS_WEBSOCKET_OUTPUT_RESUMED", "OBS_WEBSOCKET_OUTPUT_STARTED", "OBS_WEBSOCKET_OUTPUT_STOPPED"):
                s["record_paused"] = False
        elif event == "StreamStateChanged":
            s["streaming"] = bool(data.get("outputActive"))
        elif event == "VirtualcamStateChanged":
            s["virtualcam"] = bool(data.get("outputActive"))
        elif event == "ReplayBufferStateChanged":
            s["replay_buffer"] = bool(data.get("outputActive"))
        elif event == "StudioModeStateChanged":
            s["studio_mode"] = bool(data.get("studioModeEnabled"))
        elif event == "InputVolumeChanged":
            s["volumes"][data.get("inputName")] = _db(data.get("inputVolumeDb"))
        elif event == "InputMuteStateChanged":
            name = data.get("inputName")
            s["muted"][name] = bool(data.get("inputMuted"))
            if name not in s["inputs"]:
                s["inputs"].append(name)
        elif event == "InputSettingsChanged":
            name = data.get("inputName")
            kind = self._kinds.get(name)
            if kind in AUDIO_SETTING_KINDS:
                settings = data.get("inputSettings") or {}
                if AUDIO_SETTING_KINDS[kind] in settings:
                    self._audio_on[name] = bool(settings[AUDIO_SETTING_KINDS[kind]])
                else:
                    asyncio.create_task(self._safe(self._load_audio_setting(name)))
                self._update_active()
            return
        elif event in ("InputCreated", "InputRemoved", "InputNameChanged"):
            asyncio.create_task(self._safe(self._refresh_inputs()))
            if event == "InputNameChanged":
                asyncio.create_task(self._safe(self._refresh_scenes()))
        elif event == "SceneItemEnableStateChanged":
            scene = data.get("sceneName")
            source = self._item_ids.get(scene, {}).get(data.get("sceneItemId"))
            if source is not None:
                s["sources"].setdefault(scene, {})[source] = bool(data.get("sceneItemEnabled"))
            else:
                asyncio.create_task(self._safe(self._refresh_scene_items(scene)))
        elif event in ("SceneItemCreated", "SceneItemRemoved"):
            asyncio.create_task(self._safe(self._refresh_scene_items(data.get("sceneName"))))
        else:
            return
        self._notify()

    @staticmethod
    async def _safe(coro) -> None:
        try:
            await coro
        except OBSError:
            pass

    # --------------------------------------------------------------- Aktionen
    async def action(self, op: str, a: dict) -> None:
        if not self._cfg.get("enabled"):
            raise OBSError("OBS-Anbindung ist in den Einstellungen deaktiviert")
        if op == "scene":
            scene = a.get("scene")
            if not scene:
                raise OBSError("Keine Szene ausgewählt")
            if a.get("preview") and self.state.get("studio_mode"):
                await self.request("SetCurrentPreviewScene", {"sceneName": scene})
            else:
                await self.request("SetCurrentProgramScene", {"sceneName": scene})
        elif op == "record_toggle":
            await self.request("ToggleRecord")
        elif op == "record_start":
            await self.request("StartRecord")
        elif op == "record_stop":
            await self.request("StopRecord")
        elif op == "record_pause":
            await self.request("ToggleRecordPause")
        elif op == "stream_toggle":
            await self.request("ToggleStream")
        elif op == "stream_start":
            await self.request("StartStream")
        elif op == "stream_stop":
            await self.request("StopStream")
        elif op == "virtualcam_toggle":
            await self.request("ToggleVirtualCam")
        elif op == "replay_toggle":
            await self.request("ToggleReplayBuffer")
        elif op == "replay_save":
            await self.request("SaveReplayBuffer")
        elif op == "studio_toggle":
            await self.request("SetStudioModeEnabled", {"studioModeEnabled": not self.state.get("studio_mode")})
        elif op == "transition":
            await self.request("TriggerStudioModeTransition")
        elif op == "mute_toggle":
            if not a.get("input"):
                raise OBSError("Keine Audioquelle ausgewählt")
            await self.request("ToggleInputMute", {"inputName": a["input"]})
        elif op == "source_toggle":
            await self._toggle_source(a.get("scene") or self.state.get("current_scene"), a.get("source"))
        elif op == "screenshot":
            await self._screenshot()
        else:
            raise OBSError(f"Unbekannte OBS-Aktion: {op}")

    def _on_meters(self, inputs: list) -> None:
        """OBS meldet ca. 20× pro Sekunde die Pegel aller aktiven Audioquellen – genau die im OBS-Audio-Mixer."""
        meters: dict[str, int] = {}
        sounding: set[str] = set()
        for item in inputs:
            name = item.get("inputName")
            if not name:
                continue
            peak = 0.0
            for channel in item.get("inputLevelsMul") or []:
                if len(channel) > 1:
                    peak = max(peak, float(channel[1] or 0))
            if peak > 0:
                sounding.add(name)
            db = 20 * math.log10(peak) if peak > 0 else -100.0
            meters[name] = max(0, min(100, round((db + 60) / 60 * 100)))
        self.meters = meters
        # Quellen ohne eindeutige Art (z. B. Webcam): erst zählen, wenn wirklich Ton ankommt
        self._heard = {n for n in self._heard if n in meters} | sounding
        self.state["active_known"] = True
        self._update_active()

    async def set_input_volume(self, name: str, percent: float) -> None:
        """Fader 0–100 % → OBS-Lautstärke (0 % = aus, sonst −60 dB … 0 dB wie der OBS-Mixer)."""
        if not name:
            raise OBSError("Keine Audioquelle ausgewählt")
        percent = max(0.0, min(100.0, float(percent)))
        if percent <= 0:
            await self.request("SetInputVolume", {"inputName": name, "inputVolumeMul": 0.0})
            db = -100.0
        else:
            db = round((percent - 100.0) * 0.6, 1)
            await self.request("SetInputVolume", {"inputName": name, "inputVolumeDb": db})
        self.state["volumes"][name] = db
        self._notify()

    async def _screenshot(self) -> None:
        """Speichert ein Bild der aktuellen Szene im Aufnahme-Ordner von OBS."""
        import time as _time

        scene = self.state.get("current_scene") or (await self.request("GetCurrentProgramScene")).get("sceneName")
        folder = (await self.request("GetRecordDirectory")).get("recordDirectory")
        if not folder:
            raise OBSError("In OBS ist kein Aufnahme-Ordner eingestellt")
        sep = "\\" if "\\" in folder else "/"
        path = f"{folder.rstrip('/').rstrip(sep)}{sep}Screenshot {_time.strftime('%Y-%m-%d %H-%M-%S')}.png"
        await self.request("SaveSourceScreenshot", {"sourceName": scene, "imageFormat": "png", "imageFilePath": path})

    async def _toggle_source(self, scene: str | None, source: str | None) -> None:
        if not scene or not source:
            raise OBSError("Szene und Quelle angeben")
        item = await self.request("GetSceneItemId", {"sceneName": scene, "sourceName": source})
        item_id = item["sceneItemId"]
        enabled = await self.request("GetSceneItemEnabled", {"sceneName": scene, "sceneItemId": item_id})
        await self.request(
            "SetSceneItemEnabled",
            {"sceneName": scene, "sceneItemId": item_id, "sceneItemEnabled": not enabled.get("sceneItemEnabled")},
        )
