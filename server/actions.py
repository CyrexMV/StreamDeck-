"""Führt die Aktionen einer Taste aus."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from .errors import ActionError
from .integrations.spotify_api import PremiumRequired

if TYPE_CHECKING:
    from .app import DeckServer

log = logging.getLogger("tabdeck.actions")

# Aktionen, die nur das Tablet betreffen (Seitenwechsel)
CLIENT_ONLY = {"page", "back", "home"}


class ActionRunner:
    def __init__(self, server: "DeckServer") -> None:
        self.s = server

    @staticmethod
    def _is_hold(action: dict) -> bool:
        t = action.get("type")
        return (t == "hotkey" and action.get("mode") == "hold") or (t == "discord" and action.get("op") == "ptt")

    def _discord_keys(self, op: str) -> str:
        keys = (self.s.store.settings.get("discord") or {}).get(op, "")
        if not keys:
            raise ActionError(f"Für Discord „{op}“ ist keine Tastenkombination eingestellt (Einstellungen → Discord)")
        return keys

    async def press(self, handle: str, button: dict) -> str | None:
        """Taste wurde gedrückt: alle Aktionen nacheinander ausführen. Liefert ggf. einen Hinweis fürs Tablet."""
        info = None
        for index, action in enumerate(button.get("actions") or []):
            t = action.get("type")
            if t in CLIENT_ONLY:
                continue
            if self._is_hold(action):
                keys = action.get("keys") if t == "hotkey" else self._discord_keys("ptt")
                await asyncio.to_thread(self.s.keyboard.hold, f"{handle}#{index}", keys)
                continue
            info = await self.run(action) or info
        return info

    async def release(self, handle: str, button: dict) -> None:
        """Taste wurde losgelassen: gehaltene Tasten wieder loslassen."""
        for index, action in enumerate(button.get("actions") or []):
            if self._is_hold(action):
                await asyncio.to_thread(self.s.keyboard.release, f"{handle}#{index}")

    async def run(self, a: dict) -> str | None:
        t = a.get("type")
        kb = self.s.keyboard
        if t == "hotkey":
            await asyncio.to_thread(kb.tap, a.get("keys", ""))
        elif t == "text":
            await asyncio.to_thread(kb.type_text, a.get("text", ""), bool(a.get("enter")))
        elif t == "media":
            await self.s.media.control(a.get("op", "play_pause"), "any")
        elif t == "spotify":
            return await self._spotify(a)
        elif t == "volume":
            await self._volume(a)
        elif t == "obs":
            await self.s.obs.action(a.get("op", ""), a)
        elif t == "discord":
            op = a.get("op", "mute")
            await asyncio.to_thread(kb.tap, self._discord_keys(op))
            if op in ("mute", "deafen"):
                self.s.flip_discord(op)
        elif t == "open":
            await asyncio.to_thread(self.s.system.open, a.get("target", ""), a.get("args", ""))
        elif t == "command":
            await asyncio.to_thread(self.s.system.command, a.get("command", ""))
        elif t == "system":
            await asyncio.to_thread(self.s.system.power, a.get("op", ""))
        elif t == "sound":
            if a.get("op") == "stop_all":
                self.s.sounds.stop()
            elif a.get("target") != "tablet":  # „auf dem Tablet“ spielt das Tablet selbst ab
                await self.s.sounds.play(a.get("file", ""), a.get("volume", 100), a.get("mode", "restart"))
        elif t == "delay":
            await asyncio.sleep(max(0, min(60_000, int(a.get("ms") or 0))) / 1000)
        elif t in CLIENT_ONLY:
            pass
        else:
            raise ActionError(f"Unbekannter Aktionstyp: {t}")

    async def _spotify(self, a: dict) -> str | None:
        op = a.get("op", "play_pause")
        sp = self.s.spotify
        if op == "play_link":
            return await self._spotify_link(a)
        if op in ("volume_up", "volume_down", "volume_set", "mute_toggle"):
            # Echte Lautstärke in der Spotify-App (nicht Windows-Mixer)
            await sp.volume(op, a.get("step", 50 if op == "volume_set" else 10))
            return
        if op == "like":
            await sp.toggle_like()
            return
        try:
            await self.s.media.control(op, "spotify")
        except ActionError:
            if not sp.state.get("connected"):
                raise
            await sp.transport(op)  # Ersatzweg über die Spotify Web API

    async def _spotify_link(self, a: dict) -> str | None:
        sp = self.s.spotify
        link = a.get("link", "")
        kind, item_id = await sp.resolve_link(link)

        async def start_app() -> None:
            await asyncio.to_thread(self.s.system.open, "spotify:")

        reason = None
        if not sp.state.get("connected"):
            reason = "Für direktes Abspielen Spotify verbinden (⚙️ → Spotify)."
        else:
            try:
                await sp.play_link(link, bool(a.get("enqueue")), bool(a.get("shuffle")), start_app=start_app)
                return None
            except PremiumRequired:
                reason = "Direktes Abspielen erlaubt Spotify nur mit Premium."
        # Ersatzweg: in der Spotify-App am PC öffnen
        await asyncio.to_thread(self.s.system.open, f"spotify:{kind}:{item_id}")
        return f"In Spotify geöffnet – dort auf Play tippen. {reason}"

    async def _volume(self, a: dict) -> None:
        target = a.get("target", "master")
        op = a.get("op", "toggle_mute")
        step = a.get("step", 5 if op != "set" else 50)
        audio = self.s.audio
        if audio.available:
            await audio.apply(target, a.get("app", ""), op, step)
            await self.s.refresh_audio()
            return
        # Ohne pycaw: Systemlautstärke über Medientasten
        if target == "master" and op in ("up", "down", "toggle_mute"):
            key = {"up": "volume_up", "down": "volume_down", "toggle_mute": "volume_mute"}[op]
            repeat = max(1, round(float(step) / 2)) if op != "toggle_mute" else 1
            for _ in range(repeat):
                await asyncio.to_thread(self.s.keyboard.media, key)
            return
        raise ActionError(audio.error or "Lautstärkesteuerung nicht verfügbar")
