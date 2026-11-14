"""Spotify Web API – steuert die Lautstärke *in der Spotify-App* (nicht im Windows-Mixer).

Anmeldung per OAuth mit PKCE (kein Client-Secret nötig). Der Benutzer legt einmalig auf
developer.spotify.com eine App an, trägt die Redirect-URI ein und meldet sich am PC an.
Hinweis von Spotify: Wiedergabe-Steuerung (Lautstärke usw.) erfordert Spotify Premium.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import re
import secrets
import time
import urllib.parse
from typing import Awaitable, Callable

import aiohttp

from ..errors import ActionError


class NoDevice(ActionError):
    pass


class PremiumRequired(ActionError):
    pass


LINK_RE = re.compile(
    r"(?:open\.spotify\.com/(?:intl-[a-z]{2}(?:-[a-z]{2})?/)?(?:embed/)?|spotify:)"
    r"(track|album|playlist|artist|episode|show)[/:]([A-Za-z0-9]{10,40})", re.I)
PLAYABLE_SINGLE = ("track", "episode")
KIND_NAMES = {"track": "Song", "album": "Album", "playlist": "Playlist", "artist": "Künstler", "episode": "Podcast-Folge", "show": "Podcast"}


def parse_link(text: str) -> tuple[str, str] | None:
    """„https://open.spotify.com/intl-de/track/ID?si=…“ oder „spotify:track:ID“ → ("track", "ID")"""
    m = LINK_RE.search(text or "")
    return (m.group(1).lower(), m.group(2)) if m else None

log = logging.getLogger("tabdeck.spotify")

ACCOUNTS = os.environ.get("TABDECK_SPOTIFY_ACCOUNTS", "https://accounts.spotify.com")
WEB = os.environ.get("TABDECK_SPOTIFY_WEB", "https://open.spotify.com")
API = os.environ.get("TABDECK_SPOTIFY_API", "https://api.spotify.com/v1")
SCOPES = "user-read-playback-state user-modify-playback-state user-read-currently-playing user-library-read user-library-modify"


class SpotifyAPI:
    def __init__(self, secrets_store: dict, save: Callable[[], None], on_change: Callable[[], Awaitable[None]]) -> None:
        self._s = secrets_store  # Verweis auf config["secrets"]["spotify"]
        self._save = save
        self._on_change = on_change
        self._pkce: dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._target_volume: int | None = None
        self._target_time = 0.0
        self._muted_volume: int | None = None
        self._pending_volume: int | None = None
        self._volume_sending = False
        self.state: dict = {}
        self._reset_state()

    def _reset_state(self, error: str | None = None) -> None:
        self.state = {
            "configured": bool(self._s.get("client_id")),
            "connected": bool(self._s.get("refresh_token")),
            "user": self._s.get("user"),
            "premium": self._s.get("premium"),
            "error": error,
            "volume": None,
            "device": None,
            "liked": False,
            "track_id": None,
        }

    # ------------------------------------------------------------- Anmeldung
    def set_client_id(self, client_id: str) -> None:
        client_id = (client_id or "").strip()
        if client_id != self._s.get("client_id"):
            self._s.clear()
            self._s["client_id"] = client_id
            self._save()
        self._reset_state()

    def disconnect(self) -> None:
        client_id = self._s.get("client_id")
        self._s.clear()
        if client_id:
            self._s["client_id"] = client_id
        self._save()
        self._reset_state()

    def login_url(self, redirect_uri: str) -> str:
        client_id = self._s.get("client_id")
        if not client_id:
            raise ActionError("Bitte zuerst die Spotify Client-ID in den Einstellungen eintragen")
        verifier = secrets.token_urlsafe(64)[:96]
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        state = secrets.token_urlsafe(16)
        self._pkce = {"verifier": verifier, "state": state, "redirect_uri": redirect_uri}
        query = urllib.parse.urlencode({
            "client_id": client_id, "response_type": "code", "redirect_uri": redirect_uri,
            "code_challenge_method": "S256", "code_challenge": challenge, "state": state, "scope": SCOPES,
        })
        return f"{ACCOUNTS}/authorize?{query}"

    async def handle_callback(self, code: str | None, state: str | None, error: str | None) -> None:
        if error:
            raise ActionError("Spotify-Anmeldung abgebrochen" if error == "access_denied" else f"Spotify meldet: {error}")
        if not self._pkce or state != self._pkce.get("state"):
            raise ActionError("Anmeldung abgelaufen – bitte am Tablet erneut „Mit Spotify verbinden“ wählen")
        data = {
            "grant_type": "authorization_code", "code": code or "",
            "redirect_uri": self._pkce["redirect_uri"], "client_id": self._s["client_id"],
            "code_verifier": self._pkce["verifier"],
        }
        await self._token_request(data)
        self._pkce = {}
        try:
            me = await self.api("GET", "/me")
            self._s["user"] = me.get("display_name") or me.get("id")
            self._s["premium"] = me.get("product") == "premium" if me.get("product") else None
            self._save()
        except ActionError as exc:
            log.warning("Spotify-Profil nicht lesbar: %s", exc)
        self._reset_state()
        await self.poll()

    async def _token_request(self, data: dict) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{ACCOUNTS}/api/token", data=data, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                body = await resp.json(content_type=None)
        if resp.status != 200 or "access_token" not in (body or {}):
            desc = (body or {}).get("error_description") or (body or {}).get("error") or resp.status
            if (body or {}).get("error") == "invalid_grant":
                self.disconnect()
                raise ActionError("Spotify-Anmeldung abgelaufen – bitte in den Einstellungen neu verbinden")
            raise ActionError(f"Spotify-Anmeldung fehlgeschlagen: {desc}")
        self._s["access_token"] = body["access_token"]
        self._s["expires_at"] = time.time() + int(body.get("expires_in", 3600)) - 60
        if body.get("refresh_token"):
            self._s["refresh_token"] = body["refresh_token"]
        self._save()

    async def _access_token(self) -> str:
        if not self._s.get("refresh_token"):
            raise ActionError("Spotify ist nicht verbunden – Tablet: ⚙️ Einstellungen → Spotify")
        async with self._lock:
            if not self._s.get("access_token") or time.time() >= self._s.get("expires_at", 0):
                await self._token_request({
                    "grant_type": "refresh_token", "refresh_token": self._s["refresh_token"],
                    "client_id": self._s["client_id"],
                })
        return self._s["access_token"]

    # ------------------------------------------------------------------ API
    async def api(self, method: str, path: str, params: dict | None = None, _retry: bool = True, body: dict | None = None):
        token = await self._access_token()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, API + path, params=params, headers={"Authorization": f"Bearer {token}"},
                    json=body, timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    text = await resp.text()
                    status = resp.status
        except (aiohttp.ClientError, asyncio.TimeoutError):
            raise ActionError("Spotify ist gerade nicht erreichbar (Internet?)") from None
        if status == 401 and _retry:
            self._s["access_token"] = ""
            return await self.api(method, path, params, _retry=False, body=body)
        if status in (200, 201) and text:
            import json

            try:
                return json.loads(text)
            except ValueError:
                return {}
        if status < 300:
            return {}
        reason, message = "", ""
        try:
            import json

            err = json.loads(text).get("error", {})
            reason, message = err.get("reason", ""), err.get("message", "")
        except Exception:
            pass
        if status == 403 and (reason == "PREMIUM_REQUIRED" or "premium" in message.lower()):
            raise PremiumRequired("Für diese Funktion verlangt Spotify ein Premium-Abo")
        if status == 404 or reason == "NO_ACTIVE_DEVICE":
            raise NoDevice("Kein aktives Spotify-Gerät – starte die Wiedergabe einmal in Spotify")
        if status == 429:
            raise ActionError("Spotify: zu viele Anfragen – kurz warten")
        if status == 403 and "volume" in message.lower():
            raise ActionError("Dieses Spotify-Gerät erlaubt keine Lautstärkeänderung")
        raise ActionError(f"Spotify-Fehler {status}: {message or reason or 'unbekannt'}")

    # --------------------------------------------------------------- Status
    async def poll(self) -> None:
        if not self._s.get("refresh_token"):
            return
        try:
            player = await self.api("GET", "/me/player")
        except ActionError as exc:
            if self.state.get("error") != str(exc):
                self.state["error"] = str(exc)
                await self._on_change()
            return
        device = (player or {}).get("device") or {}
        item = (player or {}).get("item") or {}
        new = dict(self.state)
        artists = ", ".join(a.get("name", "") for a in item.get("artists") or []) or (item.get("show") or {}).get("name", "")
        images = (item.get("album") or {}).get("images") or item.get("images") or []
        images = sorted((i for i in images if str(i.get("url", "")).startswith("https://")), key=lambda i: abs((i.get("width") or 300) - 300))
        new.update(
            connected=True, error=None, device=device.get("name"),
            volume=device.get("volume_percent") if device.get("supports_volume", True) else None,
            track_id=item.get("id"),
            context=((player or {}).get("context") or {}).get("uri"),
            title=item.get("name") or None, artist=artists or None,
            cover=images[0]["url"] if images else None, playing=bool((player or {}).get("is_playing")),
        )
        if item.get("id") and item.get("id") != self.state.get("track_id"):
            try:
                res = await self.api("GET", "/me/tracks/contains", {"ids": item["id"]})
                new["liked"] = bool(res and res[0])
            except ActionError:
                new["liked"] = False
        if self._target_volume is not None and time.monotonic() - self._target_time < 2.5:
            new["volume"] = self._target_volume  # eigene Änderung ist noch unterwegs
        if new != self.state:
            self.state = new
            await self._on_change()

    # ---------------------------------------------------------------- Aktionen
    async def volume(self, op: str, step: float) -> None:
        if self._s.get("premium") is False:
            raise ActionError("Die Spotify-Lautstärke lässt sich nur mit Spotify Premium steuern")
        step = int(step or 10)
        current = self._target_volume if time.monotonic() - self._target_time < 2.5 else None
        if current is None:
            current = self.state.get("volume")
        if current is None and op != "volume_set":
            player = await self.api("GET", "/me/player")
            current = ((player or {}).get("device") or {}).get("volume_percent")
            if current is None:
                raise ActionError("Kein aktives Spotify-Gerät – starte die Wiedergabe einmal in Spotify")
        if op == "volume_up":
            target = min(100, current + step)
        elif op == "volume_down":
            target = max(0, current - step)
        elif op == "volume_set":
            target = max(0, min(100, step))
        elif op == "mute_toggle":
            if current and current > 0:
                self._muted_volume = current
                target = 0
            else:
                target = self._muted_volume or 50
        else:
            raise ActionError(f"Unbekannte Spotify-Aktion: {op}")
        self._target_volume, self._target_time = target, time.monotonic()
        await self.api("PUT", "/me/player/volume", {"volume_percent": str(int(target))})
        self.state["volume"] = target
        await self._on_change()

    async def set_volume(self, percent: float) -> None:
        """Für Fader: schnelle Folgewerte zusammenfassen, nur der neueste wird gesendet."""
        if self._s.get("premium") is False:
            raise ActionError("Die Spotify-Lautstärke lässt sich nur mit Spotify Premium steuern")
        target = int(max(0, min(100, round(float(percent)))))
        self._pending_volume = target
        self._target_volume, self._target_time = target, time.monotonic()
        self.state["volume"] = target
        if self._volume_sending:
            return  # der laufende Sender übernimmt den neuesten Wert
        self._volume_sending = True
        try:
            while self._pending_volume is not None:
                value, self._pending_volume = self._pending_volume, None
                await self.api("PUT", "/me/player/volume", {"volume_percent": str(value)})
        finally:
            self._volume_sending = False
            self._pending_volume = None
        await self._on_change()

    async def toggle_like(self) -> None:
        player = await self.api("GET", "/me/player/currently-playing")
        track = ((player or {}).get("item") or {}).get("id")
        if not track:
            raise ActionError("Gerade läuft kein Titel in Spotify")
        liked = (await self.api("GET", "/me/tracks/contains", {"ids": track}))[0]
        await self.api("DELETE" if liked else "PUT", "/me/tracks", {"ids": track})
        self.state.update(liked=not liked, track_id=track)
        await self._on_change()

    async def transport(self, op: str) -> None:
        """Ersatzweg für Play/Pause usw., falls die Windows-Medien-API Spotify nicht findet."""
        if op == "play_pause":
            player = await self.api("GET", "/me/player")
            await self.api("PUT", "/me/player/pause" if (player or {}).get("is_playing") else "/me/player/play")
        elif op == "next":
            await self.api("POST", "/me/player/next")
        elif op == "previous":
            await self.api("POST", "/me/player/previous")
        elif op == "shuffle":
            player = await self.api("GET", "/me/player")
            await self.api("PUT", "/me/player/shuffle", {"state": "false" if (player or {}).get("shuffle_state") else "true"})
        elif op == "repeat":
            player = await self.api("GET", "/me/player")
            nxt = {"off": "context", "context": "track", "track": "off"}.get((player or {}).get("repeat_state"), "context")
            await self.api("PUT", "/me/player/repeat", {"state": nxt})
        else:
            raise ActionError(f"Unbekannte Spotify-Aktion: {op}")

    # ------------------------------------------------------- Links abspielen
    @staticmethod
    async def resolve_link(text: str) -> tuple[str, str]:
        found = parse_link(text)
        if found:
            return found
        url = (text or "").strip()
        if re.match(r"^https://(spotify\.link|spoti\.fi)/", url):
            # Kurzlinks aus der Spotify-App auflösen
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        found = parse_link(str(resp.url)) or parse_link(await resp.text())
            except (aiohttp.ClientError, asyncio.TimeoutError):
                raise ActionError("Der Spotify-Kurzlink konnte nicht geöffnet werden (Internet?)") from None
            if found:
                return found
        raise ActionError("Das ist kein Spotify-Link. In Spotify: „Teilen → Link kopieren“ und hier einfügen.")

    @staticmethod
    async def lookup(text: str) -> dict:
        """Titel und Cover zu einem Link – über Spotifys öffentliche oEmbed-Schnittstelle (ohne Anmeldung)."""
        kind, item_id = await SpotifyAPI.resolve_link(text)
        info = {"kind": kind, "kind_name": KIND_NAMES.get(kind, kind), "id": item_id, "uri": f"spotify:{kind}:{item_id}",
                "url": f"https://open.spotify.com/{kind}/{item_id}", "title": None, "image": None}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{WEB}/oembed", params={"url": info["url"]}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        info["title"] = data.get("title")
                        info["image"] = data.get("thumbnail_url")
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            pass
        return info

    async def _devices(self) -> list:
        return ((await self.api("GET", "/me/player/devices")) or {}).get("devices") or []

    async def _with_device(self, method: str, path: str, params: dict | None = None, body: dict | None = None,
                           start_app=None) -> None:
        """Befehl senden; ist kein Gerät aktiv, den PC (oder ein anderes Gerät) wählen – notfalls Spotify starten."""
        try:
            await self.api(method, path, params, body=body)
            return
        except NoDevice:
            pass
        devices = await self._devices()
        if not devices and start_app is not None:
            await start_app()
            for _ in range(15):
                await asyncio.sleep(1)
                devices = await self._devices()
                if devices:
                    break
        if not devices:
            raise NoDevice("Spotify läuft auf keinem Gerät – bitte Spotify am PC öffnen")
        device = next((d for d in devices if d.get("is_active")), None) \
            or next((d for d in devices if d.get("type") == "Computer"), None) or devices[0]
        await self.api(method, path, {**(params or {}), "device_id": device["id"]}, body=body)

    async def play_link(self, text: str, enqueue: bool = False, shuffle: bool = False, start_app=None) -> None:
        if not self._s.get("refresh_token"):
            raise ActionError("Spotify ist nicht verbunden – Tablet: ⚙️ Einstellungen → Spotify")
        if self._s.get("premium") is False:
            raise PremiumRequired("Direktes Abspielen erlaubt Spotify nur mit Premium")
        kind, item_id = await self.resolve_link(text)
        uri = f"spotify:{kind}:{item_id}"
        if enqueue:
            if kind not in PLAYABLE_SINGLE:
                raise ActionError("Zur Warteschlange hinzufügen geht nur mit einzelnen Songs oder Podcast-Folgen")
            await self._with_device("POST", "/me/player/queue", {"uri": uri}, start_app=start_app)
        else:
            body = {"uris": [uri]} if kind in PLAYABLE_SINGLE else {"context_uri": uri}
            await self._with_device("PUT", "/me/player/play", body=body, start_app=start_app)
            if shuffle and kind not in PLAYABLE_SINGLE:
                try:
                    await self.api("PUT", "/me/player/shuffle", {"state": "true"})
                except ActionError:
                    pass
        await asyncio.sleep(0.8)
        await self.poll()
