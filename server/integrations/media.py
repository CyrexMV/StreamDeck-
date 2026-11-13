"""Mediensteuerung und „Läuft gerade“-Anzeige.

Unter Windows wird die System-Medien-API (GlobalSystemMediaTransportControls) genutzt.
Damit lässt sich gezielt Spotify steuern – auch wenn gerade ein anderes Programm Ton
abspielt – und Titel, Interpret und Cover werden angezeigt. Ohne diese API wird auf
normale Medientasten zurückgegriffen.
"""

from __future__ import annotations

import base64
import logging
import sys

from ..errors import ActionError
from .keyboard import Keyboard

log = logging.getLogger("tabdeck.media")

PLAYING = 4  # GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING


class MediaController:
    def __init__(self, keyboard: Keyboard) -> None:
        self.kb = keyboard
        self.available = False
        self.error: str | None = None
        self._manager = None
        self._cover_key: str | None = None
        self._cover: str | None = None
        if sys.platform != "win32":
            self.error = "„Läuft gerade“ gibt es nur unter Windows – Medientasten funktionieren trotzdem"
            return
        try:
            from winrt.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as Manager,
            )

            self._Manager = Manager
            self.available = True
        except Exception as exc:
            self.error = f"Windows-Medien-API nicht verfügbar: {exc}"
            log.warning(self.error)

    # ------------------------------------------------------------- Sitzungen
    async def _manager_obj(self):
        if self._manager is None:
            self._manager = await self._Manager.request_async()
        return self._manager

    @staticmethod
    def _app_id(session) -> str:
        try:
            return (session.source_app_user_model_id or "").lower()
        except Exception:
            return ""

    async def _sessions(self) -> list:
        mgr = await self._manager_obj()
        return list(mgr.get_sessions())

    async def _spotify_session(self):
        for session in await self._sessions():
            if "spotify" in self._app_id(session):
                return session
        return None

    async def _target_session(self, target: str):
        if target == "spotify":
            return await self._spotify_session()
        mgr = await self._manager_obj()
        return mgr.get_current_session()

    # -------------------------------------------------------------- Steuern
    async def control(self, op: str, target: str = "any") -> None:
        session = None
        if self.available:
            try:
                session = await self._target_session(target)
                if session is not None and await self._session_control(session, op):
                    return
            except ActionError:
                raise
            except Exception as exc:
                log.debug("Medien-API fehlgeschlagen, nutze Medientasten: %s", exc)

        if op in ("shuffle", "repeat"):
            raise ActionError("Spotify läuft nicht" if target == "spotify" else "Kein aktiver Mediaplayer")
        # Fallback: globale Medientaste
        self.kb.media(op)

    async def _session_control(self, session, op: str) -> bool:
        if op == "play_pause":
            return bool(await session.try_toggle_play_pause_async())
        if op == "next":
            return bool(await session.try_skip_next_async())
        if op == "previous":
            return bool(await session.try_skip_previous_async())
        if op == "stop":
            return bool(await session.try_stop_async())
        info = session.get_playback_info()
        if op == "shuffle":
            current = bool(info.is_shuffle_active)
            return bool(await session.try_change_shuffle_active_async(not current))
        if op == "repeat":
            from winrt.windows.media import MediaPlaybackAutoRepeatMode as Mode

            order = [Mode.NONE, Mode.LIST, Mode.TRACK]
            current = info.auto_repeat_mode
            try:
                nxt = order[(order.index(current) + 1) % len(order)]
            except ValueError:
                nxt = Mode.LIST
            return bool(await session.try_change_auto_repeat_mode_async(nxt))
        raise ActionError(f"Unbekannte Medien-Aktion: {op}")

    # ---------------------------------------------------------- Läuft gerade
    async def snapshot(self) -> dict:
        if not self.available:
            return {"available": False}
        try:
            sessions = await self._sessions()
            mgr = await self._manager_obj()
            current = mgr.get_current_session()
            spotify = next((s for s in sessions if "spotify" in self._app_id(s)), None)

            def is_playing(s) -> bool:
                try:
                    return int(s.get_playback_info().playback_status) == PLAYING
                except Exception:
                    return False

            # Spotify bevorzugen, wenn es spielt oder sonst nichts läuft
            shown = current
            if spotify is not None and (is_playing(spotify) or current is None or not is_playing(current)):
                shown = spotify
            state: dict = {
                "available": True,
                "playing": is_playing(current) if current is not None else False,
                "spotify_running": spotify is not None,
                "spotify_playing": is_playing(spotify) if spotify is not None else False,
                "spotify_shuffle": False,
                "spotify_title": "",
                "spotify_artist": "",
                "title": "",
                "artist": "",
                "app": "",
                "cover": None,
            }
            if spotify is not None:
                try:
                    state["spotify_shuffle"] = bool(spotify.get_playback_info().is_shuffle_active)
                except Exception:
                    pass
                try:  # Songtitel von Spotify – auch wenn gerade ein anderes Programm im Vordergrund spielt
                    sp_props = await spotify.try_get_media_properties_async()
                    state["spotify_title"] = sp_props.title or ""
                    state["spotify_artist"] = sp_props.artist or ""
                except Exception:
                    pass
            if shown is None:
                return state
            props = await shown.try_get_media_properties_async()
            state["title"] = props.title or ""
            state["artist"] = props.artist or ""
            state["app"] = self._app_id(shown)
            state["shown_playing"] = is_playing(shown)
            key = f"{state['app']}|{state['title']}|{state['artist']}"
            if key != self._cover_key:
                self._cover_key = key
                self._cover = await self._read_thumbnail(props)
            state["cover"] = self._cover
            return state
        except Exception as exc:
            log.debug("Medien-Snapshot fehlgeschlagen: %s", exc)
            self._manager = None
            return {"available": True}

    @staticmethod
    async def _read_thumbnail(props) -> str | None:
        try:
            ref = props.thumbnail
            if ref is None:
                return None
            from winrt.windows.storage.streams import Buffer, DataReader, InputStreamOptions

            stream = await ref.open_read_async()
            size = int(stream.size)
            if size <= 0 or size > 8_000_000:
                return None
            buf = await stream.read_async(Buffer(size), size, InputStreamOptions.READ_AHEAD)
            try:
                data = bytes(buf)
            except TypeError:
                reader = DataReader.from_buffer(buf)
                arr = bytearray(buf.length)
                reader.read_bytes(arr)
                data = bytes(arr)
            mime = getattr(stream, "content_type", "") or "image/jpeg"
            return f"data:{mime};base64,{base64.b64encode(data).decode()}"
        except Exception as exc:
            log.debug("Cover konnte nicht gelesen werden: %s", exc)
            return None
