"""Führt die Aktionen einer Taste aus."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from .errors import ActionError

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

    async def press(self, handle: str, button: dict) -> None:
        """Taste wurde gedrückt: alle Aktionen nacheinander ausführen."""
        for index, action in enumerate(button.get("actions") or []):
            t = action.get("type")
            if t in CLIENT_ONLY:
                continue
            if self._is_hold(action):
                keys = action.get("keys") if t == "hotkey" else self._discord_keys("ptt")
                await asyncio.to_thread(self.s.keyboard.hold, f"{handle}#{index}", keys)
                continue
            await self.run(action)

    async def release(self, handle: str, button: dict) -> None:
        """Taste wurde losgelassen: gehaltene Tasten wieder loslassen."""
        for index, action in enumerate(button.get("actions") or []):
            if self._is_hold(action):
                await asyncio.to_thread(self.s.keyboard.release, f"{handle}#{index}")

    async def run(self, a: dict) -> None:
        t = a.get("type")
        kb = self.s.keyboard
        if t == "hotkey":
            await asyncio.to_thread(kb.tap, a.get("keys", ""))
        elif t == "text":
            await asyncio.to_thread(kb.type_text, a.get("text", ""), bool(a.get("enter")))
        elif t == "media":
            await self.s.media.control(a.get("op", "play_pause"), "any")
        elif t == "spotify":
            await self.s.media.control(a.get("op", "play_pause"), "spotify")
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
        elif t == "delay":
            await asyncio.sleep(max(0, min(60_000, int(a.get("ms") or 0))) / 1000)
        elif t in CLIENT_ONLY:
            pass
        else:
            raise ActionError(f"Unbekannter Aktionstyp: {t}")

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
