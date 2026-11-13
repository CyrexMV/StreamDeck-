"""Webserver: liefert die Tablet-Oberfläche aus und spricht per WebSocket mit ihr."""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import io
import json
import logging
import re
import socket
import time
import webbrowser
from pathlib import Path

from aiohttp import WSMsgType, web

from . import __version__
from .actions import ActionRunner
from .config import ICON_DIR, ROOT, ConfigStore, format_token, normalize_token
from .errors import ActionError
from .integrations.audio import AudioController
from .integrations.keyboard import Keyboard
from .integrations.media import MediaController
from .integrations.obs import OBSClient
from .integrations.spotify_api import SpotifyAPI
from .integrations.system import SystemController

log = logging.getLogger("tabdeck")

WEB_DIR = ROOT / "web"
ICON_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
MAX_ICON_BYTES = 3 * 1024 * 1024


def lan_addresses() -> list[str]:
    addresses: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # sendet nichts, ermittelt nur die Route
            addresses.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in addresses and not ip.startswith("127."):
                addresses.append(ip)
    except OSError:
        pass
    return addresses or ["127.0.0.1"]


class DeckServer:
    POLL_INTERVAL = 1.0

    def __init__(self, store: ConfigStore) -> None:
        self.store = store
        self.clients: dict[web.WebSocketResponse, str] = {}
        self.keyboard = Keyboard()
        self.audio = AudioController()
        self.media = MediaController(self.keyboard)
        self.system = SystemController()
        self.obs = OBSClient(self._on_obs_change)
        self.spotify = SpotifyAPI(store.secrets["spotify"], store.save, self._on_spotify_change)
        self.runner = ActionRunner(self)
        self.state: dict = {
            "obs": self.obs.state,
            "audio": {"available": self.audio.available},
            "media": {"available": self.media.available},
            "stats": self.system.stats(),
            "spotify": self.spotify.state,
            "discord": {"mute": False, "deafen": False},
            "toggles": {},
        }
        self._press_tasks: dict[str, asyncio.Task] = {}
        self._auth_failures: dict[str, list[float]] = {}
        self._conn_counter = 0
        self._bg_tasks: list[asyncio.Task] = []

    # ================================================================ App
    def make_app(self) -> web.Application:
        app = web.Application(client_max_size=MAX_ICON_BYTES * 2)
        app.router.add_get("/", self.handle_index)
        app.router.add_get("/ws", self.handle_ws)
        app.router.add_get("/connect", self.handle_connect)
        app.router.add_get("/spotify/login", self.handle_spotify_login)
        app.router.add_get("/spotify/callback", self.handle_spotify_callback)
        app.router.add_get("/manifest.webmanifest", self.handle_file("manifest.webmanifest", "application/manifest+json"))
        app.router.add_get("/sw.js", self.handle_file("sw.js", "text/javascript"))
        app.router.add_static("/web/", WEB_DIR)
        app.router.add_static("/icons/", ICON_DIR)
        app.on_startup.append(self._startup)
        app.on_shutdown.append(self._shutdown)
        app.middlewares.append(self._no_cache)
        return app

    @web.middleware
    async def _no_cache(self, request: web.Request, handler):
        resp = await handler(request)
        if request.path.startswith(("/web/", "/sw.js")) or request.path == "/":
            resp.headers["Cache-Control"] = "no-cache"
        return resp

    async def _startup(self, app: web.Application) -> None:
        self.obs.configure(self.store.obs)
        loops = [("stats", self._poll_stats, 1.0), ("media", self._poll_media, 1.5),
                 ("audio", self.refresh_audio, 2.0), ("spotify", self.spotify.poll, 3.0)]
        for name, fn, interval in loops:
            self._bg_tasks.append(asyncio.create_task(self._loop(name, fn, interval), name=name))

    async def _shutdown(self, app: web.Application) -> None:
        self.keyboard.release_all()
        for task in self._bg_tasks:
            task.cancel()
        await self.obs.stop()
        for ws in list(self.clients):
            await ws.close()

    async def handle_index(self, request: web.Request) -> web.StreamResponse:
        return web.FileResponse(WEB_DIR / "index.html")

    def handle_file(self, name: str, content_type: str):
        async def handler(request: web.Request) -> web.StreamResponse:
            resp = web.FileResponse(WEB_DIR / name)
            resp.content_type = content_type
            return resp

        return handler

    # ------------------------------------------------- Verbindungsseite (PC)
    def connect_urls(self) -> list[str]:
        port = self.store.data["server"]["port"]
        return [f"http://{ip}:{port}/?token={self.store.token}" for ip in lan_addresses()]

    @staticmethod
    def _is_local(request: web.Request) -> bool:
        return (request.remote or "") in ("127.0.0.1", "::1", "localhost")

    def spotify_redirect_uri(self) -> str:
        return f"http://127.0.0.1:{self.store.data['server']['port']}/spotify/callback"

    async def handle_spotify_login(self, request: web.Request) -> web.StreamResponse:
        if not self._is_local(request):
            raise web.HTTPForbidden(text="Die Spotify-Anmeldung funktioniert nur direkt am PC.")
        try:
            url = self.spotify.login_url(self.spotify_redirect_uri())
        except ActionError as exc:
            return web.Response(text=MESSAGE_PAGE.format(icon="⚠️", title="Spotify", text=str(exc)), content_type="text/html")
        raise web.HTTPFound(url)

    async def handle_spotify_callback(self, request: web.Request) -> web.StreamResponse:
        if not self._is_local(request):
            raise web.HTTPForbidden()
        q = request.query
        try:
            await self.spotify.handle_callback(q.get("code"), q.get("state"), q.get("error"))
            name = self.spotify.state.get("user") or "dein Konto"
            hint = "" if self.spotify.state.get("premium") is not False else (
                "<br><br>⚠️ Dein Konto ist kein Premium-Konto. Spotify erlaubt die Lautstärke-Steuerung nur mit Premium.")
            html = MESSAGE_PAGE.format(icon="✅", title="Spotify verbunden",
                                       text=f"TabDeck ist jetzt mit {name} verbunden. Du kannst dieses Fenster schließen.{hint}")
        except ActionError as exc:
            html = MESSAGE_PAGE.format(icon="⚠️", title="Spotify-Anmeldung fehlgeschlagen", text=str(exc))
        await self.broadcast_state("spotify")
        return web.Response(text=html, content_type="text/html")

    async def handle_connect(self, request: web.Request) -> web.StreamResponse:
        """Zeigt am PC einen QR-Code zum Verbinden – nur vom PC selbst aus abrufbar."""
        remote = request.remote or ""
        if remote not in ("127.0.0.1", "::1", "localhost"):
            raise web.HTTPForbidden(text="Diese Seite ist nur direkt am PC abrufbar.")
        blocks = []
        for url in self.connect_urls():
            blocks.append(
                f'<div class="card"><div class="qr">{qr_svg(url)}</div>'
                f'<code>{url.split("?")[0]}</code></div>'
            )
        html = CONNECT_PAGE.format(
            cards="".join(blocks), token=format_token(self.store.token), version=__version__
        )
        return web.Response(text=html, content_type="text/html")

    # ========================================================== WebSocket
    def _auth_blocked(self, ip: str) -> bool:
        now = time.monotonic()
        recent = [t for t in self._auth_failures.get(ip, []) if now - t < 600]
        self._auth_failures[ip] = recent
        return len(recent) >= 10

    async def handle_ws(self, request: web.Request) -> web.StreamResponse:
        ws = web.WebSocketResponse(heartbeat=20, max_msg_size=8 * 1024 * 1024)
        await ws.prepare(request)
        ip = request.remote or "?"

        if self._auth_blocked(ip):
            await ws.close(code=4003, message=b"Zu viele Fehlversuche - bitte 10 Minuten warten")
            return ws
        token = normalize_token(request.query.get("token"))
        if not hmac.compare_digest(token, self.store.token):
            self._auth_failures.setdefault(ip, []).append(time.monotonic())
            log.warning("Verbindungsversuch mit falschem Code von %s", ip)
            await ws.close(code=4001, message=b"Falscher Verbindungscode")
            return ws

        self._conn_counter += 1
        conn_id = f"c{self._conn_counter}"
        self.clients[ws] = conn_id
        log.info("Tablet verbunden: %s (%d aktiv)", ip, len(self.clients))
        await ws.send_json(
            {
                "type": "hello",
                "version": __version__,
                "config": self.store.client_view(),
                "state": self.state,
                "features": self.features(),
            }
        )
        try:
            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    continue
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue
                await self._dispatch(ws, conn_id, data)
        finally:
            self.clients.pop(ws, None)
            for handle in [h for h in self._press_tasks if h.startswith(conn_id + ":")]:
                self._schedule_release(handle, None)
            log.info("Tablet getrennt: %s (%d aktiv)", ip, len(self.clients))
        return ws

    def features(self) -> dict:
        return {
            "keyboard": {"ok": self.keyboard.available, "error": self.keyboard.error},
            "audio": {"ok": self.audio.available, "error": self.audio.error},
            "media": {"ok": self.media.available, "error": self.media.error},
            "stats": {"ok": bool(self.system.stats()), "error": self.system.stats_error or "CPU/RAM nicht lesbar"},
        }

    async def _dispatch(self, ws: web.WebSocketResponse, conn_id: str, data: dict) -> None:
        kind = data.get("type")
        if kind == "down":
            self._on_down(ws, conn_id, str(data.get("page")), str(data.get("slot")))
        elif kind == "up":
            handle = f"{conn_id}:{data.get('page')}:{data.get('slot')}"
            button = self.store.button(str(data.get("page")), str(data.get("slot")))
            self._schedule_release(handle, button)
        elif kind == "rpc":
            asyncio.create_task(self._rpc(ws, data))

    # ---------------------------------------------------------- Tasten
    def _on_down(self, ws, conn_id: str, page: str, slot: str) -> None:
        button = self.store.button(page, slot)
        if not button:
            return
        handle = f"{conn_id}:{page}:{slot}"

        async def run() -> None:
            ok, error = True, None
            try:
                if button.get("toggle"):
                    key = f"{page}:{slot}"
                    self.state["toggles"][key] = not self.state["toggles"].get(key, False)
                    await self.broadcast_state("toggles")
                await self.runner.press(handle, button)
            except ActionError as exc:
                ok, error = False, str(exc)
            except Exception as exc:
                log.exception("Fehler bei Taste %s/%s", page, slot)
                ok, error = False, f"Unerwarteter Fehler: {exc}"
            if error:
                log.warning("Taste „%s“: %s", button.get("label") or slot, error)
            try:
                await ws.send_json({"type": "result", "page": page, "slot": slot, "ok": ok, "error": error})
            except Exception:
                pass

        self._press_tasks[handle] = asyncio.create_task(run())

    def _schedule_release(self, handle: str, button: dict | None) -> None:
        task = self._press_tasks.pop(handle, None)

        async def release() -> None:
            if task is not None:
                await asyncio.wait({task}, timeout=30)
            if button is not None:
                try:
                    await self.runner.release(handle, button)
                except Exception:
                    log.exception("Fehler beim Loslassen")
            # Sicherheitsnetz: alle zu diesem Handle gehaltenen Tasten freigeben
            for held in [h for h in list(self.keyboard._held) if h.startswith(handle + "#")]:
                await asyncio.to_thread(self.keyboard.release, held)

        asyncio.create_task(release())

    def flip_discord(self, op: str) -> None:
        self.state["discord"][op] = not self.state["discord"].get(op)
        asyncio.create_task(self.broadcast_state("discord"))

    # -------------------------------------------------------------- RPC
    async def _rpc(self, ws: web.WebSocketResponse, data: dict) -> None:
        method = data.get("method")
        params = data.get("params") or {}
        reply: dict = {"type": "rpc_result", "id": data.get("id"), "ok": True}
        try:
            reply["result"] = await self._call(method, params)
        except (ActionError, ValueError) as exc:
            reply.update(ok=False, error=str(exc))
        except Exception as exc:
            log.exception("RPC %s fehlgeschlagen", method)
            reply.update(ok=False, error=f"Unerwarteter Fehler: {exc}")
        try:
            await ws.send_json(reply)
        except Exception:
            pass

    async def _call(self, method: str, p: dict):
        if method == "save_config":
            self.store.update_from_client(p.get("config"))
            self.obs.configure(self.store.obs)
            self._cleanup_icons()
            await self.broadcast({"type": "config", "config": self.store.client_view()})
            return True
        if method == "upload_icon":
            return {"url": self._save_icon(p.get("data", ""))}
        if method == "test_action":
            await self.runner.run(p.get("action") or {})
            return True
        if method == "audio_apps":
            snap = await self.audio.snapshot()
            return sorted({a["name"] for a in (snap.get("apps") or {}).values()}, key=str.lower)
        if method == "obs_reconnect":
            self.obs.restart()
            return True
        if method == "set_volume":
            await self._set_channel(p, float(p.get("value", 0)))
            return True
        if method == "mute_channel":
            await self._mute_channel(p)
            return True
        if method == "send_keys":
            # Tastenkombination (nach Countdown) senden – z. B. zum Aufnehmen in Discord
            await asyncio.sleep(max(0.0, min(10.0, float(p.get("delay") or 0))))
            await asyncio.to_thread(self.keyboard.tap, p.get("keys", ""))
            return True
        if method == "spotify_info":
            return {"redirect_uri": self.spotify_redirect_uri(),
                    "client_id": self.store.secrets["spotify"].get("client_id", ""),
                    "login_url": f"http://127.0.0.1:{self.store.data['server']['port']}/spotify/login"}
        if method == "spotify_setup":
            client_id = (p.get("client_id") or "").strip()
            if not re.fullmatch(r"[0-9a-fA-F]{32}", client_id):
                raise ActionError("Die Client-ID besteht aus 32 Zeichen (0–9, a–f) – bitte genau kopieren")
            self.spotify.set_client_id(client_id)
            login = f"http://127.0.0.1:{self.store.data['server']['port']}/spotify/login"
            opened = await asyncio.to_thread(webbrowser.open, login)
            await self.broadcast_state("spotify")
            return {"opened": bool(opened), "login_url": login}
        if method == "spotify_disconnect":
            self.spotify.disconnect()
            await self._on_spotify_change()
            return True
        if method == "discord_reset":
            self.state["discord"] = {"mute": False, "deafen": False}
            await self.broadcast_state("discord")
            return True
        raise ActionError(f"Unbekannte Funktion: {method}")

    # ------------------------------------------------------------ Icons
    def _save_icon(self, data_url: str) -> str:
        match = re.match(r"^data:([\w/+.-]+);base64,(.*)$", data_url or "", re.S)
        if not match or match.group(1) not in ICON_TYPES:
            raise ActionError("Nur PNG-, JPG-, WebP- oder GIF-Bilder sind erlaubt")
        try:
            raw = base64.b64decode(match.group(2), validate=False)
        except (binascii.Error, ValueError):
            raise ActionError("Bild konnte nicht gelesen werden") from None
        if len(raw) > MAX_ICON_BYTES:
            raise ActionError("Bild ist zu groß (max. 3 MB)")
        name = hashlib.sha256(raw).hexdigest()[:20] + ICON_TYPES[match.group(1)]
        ICON_DIR.mkdir(parents=True, exist_ok=True)
        path = ICON_DIR / name
        if not path.exists():
            path.write_bytes(raw)
        return f"/icons/{name}"

    def _cleanup_icons(self) -> None:
        """Nicht mehr benutzte hochgeladene Bilder löschen."""
        text = json.dumps(self.store.data)
        used = set(re.findall(r"/icons/([\w.]+)", text))
        cutoff = time.time() - 3600  # frisch hochgeladene Bilder (noch nicht gespeichert) behalten
        for path in ICON_DIR.glob("*"):
            if path.is_file() and path.name not in used and path.stat().st_mtime < cutoff:
                try:
                    path.unlink()
                except OSError:
                    pass

    # ---------------------------------------------------------- Zustand
    async def broadcast(self, message: dict) -> None:
        if not self.clients:
            return
        payload = json.dumps(message)
        await asyncio.gather(*(ws.send_str(payload) for ws in list(self.clients)), return_exceptions=True)

    async def broadcast_state(self, *keys: str) -> None:
        await self.broadcast({"type": "state", "state": {k: self.state[k] for k in keys}})

    async def _on_obs_change(self, obs_state: dict) -> None:
        self.state["obs"] = obs_state
        await self.broadcast_state("obs")

    # ---------------------------------------------------------------- Fader
    async def _set_channel(self, ch: dict, value: float) -> None:
        kind = ch.get("kind")
        if kind in ("master", "mic", "app"):
            if not self.audio.available:
                raise ActionError(self.audio.error or "Lautstärkesteuerung nicht verfügbar")
            await self.audio.apply(kind, ch.get("app", ""), "set", max(0.0, min(100.0, value)))
            self._schedule_audio_refresh()
        elif kind == "spotify":
            await self.spotify.set_volume(value)
        elif kind == "obs":
            await self.obs.set_input_volume(ch.get("input", ""), value)
        else:
            raise ActionError(f"Unbekannter Fader: {kind}")

    async def _mute_channel(self, ch: dict) -> None:
        kind = ch.get("kind")
        if kind in ("master", "mic", "app"):
            await self.audio.apply(kind, ch.get("app", ""), "toggle_mute", 0)
            await self.refresh_audio()
        elif kind == "spotify":
            await self.spotify.volume("mute_toggle", 0)
        elif kind == "obs":
            await self.obs.action("mute_toggle", {"input": ch.get("input")})
        else:
            raise ActionError(f"Unbekannter Fader: {kind}")

    def _schedule_audio_refresh(self) -> None:
        """Beim Ziehen nicht nach jedem Wert alle Programme abfragen – kurz sammeln."""
        if getattr(self, "_audio_refresh", None) and not self._audio_refresh.done():
            return

        async def later() -> None:
            await asyncio.sleep(0.3)
            await self.refresh_audio()

        self._audio_refresh = asyncio.create_task(later())

    async def _on_spotify_change(self) -> None:
        self.state["spotify"] = self.spotify.state
        await self.broadcast_state("spotify")

    async def refresh_audio(self) -> None:
        if not self.audio.available:
            return
        snap = await self.audio.snapshot()
        if snap != self.state["audio"]:
            self.state["audio"] = snap
            await self.broadcast_state("audio")

    async def _poll_stats(self) -> None:
        stats = await asyncio.to_thread(self.system.stats)
        if stats != self.state["stats"]:
            self.state["stats"] = stats
            await self.broadcast_state("stats")

    async def _poll_media(self) -> None:
        if not self.media.available:
            return
        media = await self.media.snapshot()
        if media != self.state["media"]:
            self.state["media"] = media
            await self.broadcast_state("media")

    async def _loop(self, name: str, fn, interval: float) -> None:
        """Jede Abfrage läuft unabhängig – hängt eine (z. B. Windows-Medien), laufen die anderen weiter."""
        failures = 0
        while True:
            await asyncio.sleep(interval if failures < 3 else min(30.0, interval * failures))
            if not self.clients:
                continue
            try:
                await asyncio.wait_for(fn(), timeout=8)
                failures = 0
            except asyncio.CancelledError:
                raise
            except asyncio.TimeoutError:
                failures += 1
                log.warning("Abfrage „%s“ hat zu lange gedauert", name)
            except Exception:
                failures += 1
                log.exception("Fehler bei der Abfrage „%s“", name)


# ====================================================================== QR
def qr_svg(text: str) -> str:
    try:
        import qrcode
        import qrcode.image.svg

        img = qrcode.make(text, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
        buf = io.BytesIO()
        img.save(buf)
        svg = buf.getvalue().decode()
        return svg[svg.find("<svg"):]
    except Exception:
        return "<p>(QR-Code benötigt das Paket „qrcode“)</p>"


def print_qr(text: str) -> None:
    try:
        import qrcode

        qr = qrcode.QRCode(border=1)
        qr.add_data(text)
        qr.print_ascii(invert=True)
    except Exception:
        pass


MESSAGE_PAGE = """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>TabDeck</title>
<style>body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#0f1115;color:#e8eaf0;
font-family:system-ui,Segoe UI,sans-serif}}div{{max-width:520px;text-align:center;padding:24px;line-height:1.5}}
.i{{font-size:56px}}</style></head><body><div><div class="i">{icon}</div><h1>{title}</h1><p>{text}</p></div></body></html>"""


CONNECT_PAGE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TabDeck verbinden</title>
<style>
:root{{color-scheme:dark;--bg:#0f1115;--card:#1a1d24;--fg:#e8eaf0;--muted:#9aa0ad;--acc:#7c5cff}}
body{{margin:0;font-family:system-ui,Segoe UI,sans-serif;background:var(--bg);color:var(--fg);
display:flex;flex-direction:column;align-items:center;padding:40px 16px}}
h1{{margin:0 0 8px}} p{{color:var(--muted);max-width:640px;text-align:center;line-height:1.5}}
.cards{{display:flex;flex-wrap:wrap;gap:24px;justify-content:center;margin:24px 0}}
.card{{background:var(--card);border-radius:20px;padding:20px;text-align:center}}
.qr{{background:#fff;border-radius:12px;padding:12px;width:280px;height:280px}}
.qr svg{{width:100%;height:100%}} code{{display:block;margin-top:12px;font-size:15px}}
.token{{font-size:40px;letter-spacing:6px;font-weight:700;color:var(--acc);margin:8px 0}}
</style></head><body>
<h1>📱 TabDeck verbinden</h1>
<p>Scanne den QR-Code mit der Kamera deines Galaxy Tab. Tablet und PC müssen im selben WLAN sein.</p>
<div class="cards">{cards}</div>
<p>Oder öffne die Adresse im Browser des Tablets und gib diesen Verbindungscode ein:</p>
<div class="token">{token}</div>
<p style="font-size:13px">TabDeck {version}</p>
</body></html>"""
