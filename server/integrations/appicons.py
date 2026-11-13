"""Echte Programm-Symbole (Discord, Spotify, OBS, Chrome …) direkt aus den installierten Programmen.

Windows zeigt in Taskleiste und Startmenü die Symbole, die in den .exe-Dateien stecken.
TabDeck liest genau diese aus (wie der Explorer), wandelt sie in PNG-Bilder um und
speichert sie in data/appicons/. So passen die Logos immer exakt zur installierten App.

Wege, um die passende Programmdatei zu finden:
  1. laufender Prozess (z. B. Discord.exe läuft gerade)
  2. bekannte Installationsorte (Discord, Spotify, OBS, Steam …)
  3. Registrierte Links (discord://, spotify:, steam://) und Standardbrowser
  4. Windows „App Paths“ und PATH (chrome.exe, explorer.exe …)
  5. Microsoft-Store-Apps: Logo aus dem App-Paket
"""

from __future__ import annotations

import glob
import logging
import os
import re
import shutil
import struct
import sys
import threading
import time
import zlib
from pathlib import Path

log = logging.getLogger("tabdeck.appicons")

IS_WINDOWS = sys.platform == "win32"
ICON_SIZE = 128
RETRY_AFTER = 60.0

_SAFE = re.compile(r"[^a-z0-9._-]+")


def safe_key(key: str) -> str:
    key = (key or "").strip().lower()
    if key.endswith(".exe"):
        key = key[:-4]
    return _SAFE.sub("-", key).strip("-.")[:60]


# ------------------------------------------------------------------ PNG-Kodierer
def png_rgba(width: int, height: int, rgba: bytes) -> bytes:
    stride = width * 4
    raw = b"".join(b"\x00" + rgba[y * stride:(y + 1) * stride] for y in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def unblend(on_black: bytes, on_white: bytes) -> bytes:
    """Aus zwei Renderings (schwarzer/weißer Hintergrund, BGRA) echtes RGBA mit Transparenz berechnen.
    Funktioniert für Symbole mit und ohne Alphakanal gleichermaßen."""
    out = bytearray(len(on_black))
    for i in range(0, len(on_black), 4):
        b0, g0, r0 = on_black[i], on_black[i + 1], on_black[i + 2]
        g1 = on_white[i + 1]
        alpha = 255 - max(0, min(255, g1 - g0))
        if alpha:
            out[i] = min(255, r0 * 255 // alpha)
            out[i + 1] = min(255, g0 * 255 // alpha)
            out[i + 2] = min(255, b0 * 255 // alpha)
        out[i + 3] = alpha
    return bytes(out)


# ------------------------------------------------------------ Windows: Symbol lesen
class _Win32Icons:
    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes

        self.ct = ctypes
        u = self.user32 = ctypes.WinDLL("user32", use_last_error=True)  # type: ignore[attr-defined]
        g = self.gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)  # type: ignore[attr-defined]
        s = self.shell32 = ctypes.WinDLL("shell32", use_last_error=True)  # type: ignore[attr-defined]
        vp, ci, cu = ctypes.c_void_p, ctypes.c_int, ctypes.c_uint

        u.PrivateExtractIconsW.argtypes = (wintypes.LPCWSTR, ci, ci, ci, ctypes.POINTER(vp), ctypes.POINTER(cu), cu, cu)
        u.PrivateExtractIconsW.restype = cu
        u.GetDC.argtypes, u.GetDC.restype = (vp,), vp
        u.ReleaseDC.argtypes, u.ReleaseDC.restype = (vp, vp), ci
        u.DrawIconEx.argtypes = (vp, ci, ci, vp, ci, ci, cu, vp, cu)
        u.DrawIconEx.restype = wintypes.BOOL
        u.DestroyIcon.argtypes, u.DestroyIcon.restype = (vp,), wintypes.BOOL
        g.CreateCompatibleDC.argtypes, g.CreateCompatibleDC.restype = (vp,), vp
        g.CreateDIBSection.argtypes = (vp, vp, cu, ctypes.POINTER(vp), vp, wintypes.DWORD)
        g.CreateDIBSection.restype = vp
        g.SelectObject.argtypes, g.SelectObject.restype = (vp, vp), vp
        g.DeleteObject.argtypes, g.DeleteObject.restype = (vp,), wintypes.BOOL
        g.DeleteDC.argtypes, g.DeleteDC.restype = (vp,), wintypes.BOOL
        g.GdiFlush.argtypes, g.GdiFlush.restype = (), wintypes.BOOL

        class SHFILEINFOW(ctypes.Structure):
            _fields_ = [("hIcon", vp), ("iIcon", ci), ("dwAttributes", wintypes.DWORD),
                        ("szDisplayName", wintypes.WCHAR * 260), ("szTypeName", wintypes.WCHAR * 80)]

        self.SHFILEINFOW = SHFILEINFOW
        s.SHGetFileInfoW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(SHFILEINFOW), cu, cu)
        s.SHGetFileInfoW.restype = ctypes.c_size_t

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

        class BITMAPINFO(ctypes.Structure):
            _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

        self.BITMAPINFO = BITMAPINFO

    def _hicon(self, path: str, size: int):
        ct = self.ct
        hicon = ct.c_void_p()
        if path.lower().endswith((".exe", ".dll", ".ico", ".icl", ".cpl", ".scr")):
            got = self.user32.PrivateExtractIconsW(path, 0, size, size, ct.byref(hicon), None, 1, 0)
            if got not in (0, 0xFFFFFFFF) and hicon.value:
                return hicon.value
        info = self.SHFILEINFOW()
        SHGFI_ICON, SHGFI_LARGEICON = 0x100, 0x0
        if self.shell32.SHGetFileInfoW(path, 0, ct.byref(info), ct.sizeof(info), SHGFI_ICON | SHGFI_LARGEICON) and info.hIcon:
            return info.hIcon
        return None

    def _render(self, hicon, size: int, background: int) -> bytes:
        ct = self.ct
        hdc = self.user32.GetDC(None)
        mem = self.gdi32.CreateCompatibleDC(hdc)
        bmi = self.BITMAPINFO()
        h = bmi.bmiHeader
        h.biSize, h.biWidth, h.biHeight, h.biPlanes, h.biBitCount, h.biCompression = ct.sizeof(h), size, -size, 1, 32, 0
        bits = ct.c_void_p()
        bmp = self.gdi32.CreateDIBSection(hdc, ct.byref(bmi), 0, ct.byref(bits), None, 0)
        try:
            if not bmp or not bits.value:
                raise OSError("CreateDIBSection fehlgeschlagen")
            old = self.gdi32.SelectObject(mem, bmp)
            ct.memset(bits, background, size * size * 4)
            self.user32.DrawIconEx(mem, 0, 0, hicon, size, size, 0, None, 3)  # DI_NORMAL
            self.gdi32.GdiFlush()
            data = ct.string_at(bits, size * size * 4)
            self.gdi32.SelectObject(mem, old)
            return data
        finally:
            if bmp:
                self.gdi32.DeleteObject(bmp)
            self.gdi32.DeleteDC(mem)
            self.user32.ReleaseDC(None, hdc)

    def png(self, path: str, size: int = ICON_SIZE) -> bytes | None:
        hicon = self._hicon(path, size)
        if not hicon:
            return None
        try:
            black = self._render(hicon, size, 0x00)
            white = self._render(hicon, size, 0xFF)
        finally:
            self.user32.DestroyIcon(hicon)
        rgba = unblend(black, white)
        if not any(rgba[3::4]):
            return None  # leeres Symbol
        return png_rgba(size, size, rgba)


# ------------------------------------------------------------ Programmdatei finden
def _reg(root_name: str, path: str, value: str = "") -> str | None:
    if not IS_WINDOWS:
        return None
    import winreg

    root = {"HKCR": winreg.HKEY_CLASSES_ROOT, "HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}[root_name]
    try:
        with winreg.OpenKey(root, path) as key:
            return str(winreg.QueryValueEx(key, value)[0])
    except OSError:
        return None


def _exe_from_command(cmd: str | None) -> str | None:
    """'"C:\\x\\Discord\\Update.exe" --processStart Discord.exe' → C:\\x\\Discord\\Update.exe"""
    if not cmd:
        return None
    cmd = os.path.expandvars(cmd.strip())
    m = re.match(r'"([^"]+)"', cmd) or re.match(r"(\S+\.(?:exe|ico|dll))", cmd, re.I)
    path = m.group(1) if m else cmd.split(" ")[0]
    path = re.sub(r",-?\d+$", "", path)  # DefaultIcon-Angabe „datei.exe,0“
    return path if os.path.isfile(path) else None


def _newest(pattern: str) -> str | None:
    hits = sorted(glob.glob(os.path.expandvars(pattern)), key=os.path.getmtime, reverse=True)
    return hits[0] if hits else None


KNOWN_LOCATIONS = {
    "discord": [r"%LOCALAPPDATA%\Discord\app-*\Discord.exe", r"%LOCALAPPDATA%\Discord\Update.exe"],
    "discordptb": [r"%LOCALAPPDATA%\DiscordPTB\app-*\DiscordPTB.exe"],
    "discordcanary": [r"%LOCALAPPDATA%\DiscordCanary\app-*\DiscordCanary.exe"],
    "spotify": [r"%APPDATA%\Spotify\Spotify.exe", r"%LOCALAPPDATA%\Spotify\Spotify.exe"],
    "obs64": [r"%PROGRAMFILES%\obs-studio\bin\64bit\obs64.exe", r"%PROGRAMFILES(X86)%\obs-studio\bin\64bit\obs64.exe",
              r"%PROGRAMFILES(X86)%\Steam\steamapps\common\OBS Studio\bin\64bit\obs64.exe"],
    "steam": [r"%PROGRAMFILES(X86)%\Steam\steam.exe", r"%PROGRAMFILES%\Steam\steam.exe"],
    "chrome": [r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe", r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"],
    "msedge": [r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"],
    "firefox": [r"%PROGRAMFILES%\Mozilla Firefox\firefox.exe"],
    "explorer": [r"%WINDIR%\explorer.exe"],
    "taskmgr": [r"%WINDIR%\System32\Taskmgr.exe"],
    "teamspeak": [r"%PROGRAMFILES%\TeamSpeak\TeamSpeak.exe", r"%LOCALAPPDATA%\Programs\TeamSpeak\TeamSpeak.exe"],
    "ts3client_win64": [r"%PROGRAMFILES%\TeamSpeak 3 Client\ts3client_win64.exe"],
    "vlc": [r"%PROGRAMFILES%\VideoLAN\VLC\vlc.exe"],
}
SCHEME_KEYS = {"discord": "discord", "spotify": "spotify", "steam": "steam", "obs": "obs64"}


def _store_logo(exe: str) -> bytes | None:
    """Microsoft-Store-Apps (z. B. Spotify aus dem Store): Logo aus dem App-Paket lesen."""
    m = re.search(r"^(.*\\WindowsApps\\[^\\]+)\\", exe, re.I)
    if not m:
        return None
    root = Path(m.group(1))
    try:
        manifest = (root / "AppxManifest.xml").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    candidates = re.findall(r'Square(?:150x150|44x44)Logo="([^"]+)"', manifest) + re.findall(r"<Logo>([^<]+)</Logo>", manifest)
    best: tuple[int, Path] | None = None
    for rel in candidates:
        asset = root / rel.replace("/", "\\")
        for f in asset.parent.glob(asset.stem + "*" + asset.suffix):
            try:
                size = f.stat().st_size
            except OSError:
                continue
            if "contrast" in f.name.lower():
                continue
            if best is None or size > best[0]:
                best = (size, f)
    if best:
        try:
            return best[1].read_bytes()
        except OSError:
            return None
    return None


class AppIcons:
    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.available = IS_WINDOWS
        self._win: _Win32Icons | None = None
        self._failed: dict[str, float] = {}
        self._lock = threading.Lock()
        if IS_WINDOWS:
            try:
                self._win = _Win32Icons()
            except Exception as exc:
                self.available = False
                log.warning("Programm-Symbole nicht verfügbar: %s", exc)

    def url(self, key: str) -> str:
        return f"/appicons/{key}.png"

    def cached(self) -> dict[str, str]:
        if not self.folder.exists():
            return {}
        return {p.stem: self.url(p.stem) for p in self.folder.glob("*.png")}

    # ------------------------------------------------------------- suchen
    @staticmethod
    def _running_exe(key: str) -> str | None:
        try:
            import psutil
        except Exception:
            return None
        for proc in psutil.process_iter(["name", "exe"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if safe_key(name) == key and proc.info.get("exe"):
                    return proc.info["exe"]
            except Exception:
                continue
        return None

    def _candidates(self, key: str, target: str | None):
        """Mögliche Programmdateien der Reihe nach (wird erst bei Bedarf berechnet)."""
        if target:
            t = os.path.expandvars(target.strip().strip('"'))
            if os.path.isfile(t):
                yield t
            scheme = re.match(r"^([a-z][a-z0-9+.-]+):", t, re.I)
            if scheme and len(scheme.group(1)) > 1:
                s = scheme.group(1).lower()
                yield _exe_from_command(_reg("HKCR", rf"{s}\shell\open\command"))
                yield _exe_from_command(_reg("HKCR", rf"{s}\DefaultIcon"))
            elif not os.path.isabs(t):
                yield shutil.which(t)
        if key == "browser":
            prog = _reg("HKCU", r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice", "ProgId")
            if prog:
                yield _exe_from_command(_reg("HKCR", rf"{prog}\shell\open\command"))
            return
        yield self._running_exe(key)
        for pattern in KNOWN_LOCATIONS.get(key, []):
            yield _newest(pattern)
        if key == "obs64":
            obs_dir = _reg("HKLM", r"SOFTWARE\OBS Studio")
            if obs_dir:
                yield os.path.join(obs_dir, "bin", "64bit", "obs64.exe")
        if key == "steam":
            yield _reg("HKCU", r"Software\Valve\Steam", "SteamExe")
        for scheme, k in SCHEME_KEYS.items():
            if k == key:
                yield _exe_from_command(_reg("HKCR", rf"{scheme}\shell\open\command"))
        for root in ("HKCU", "HKLM"):
            yield _reg(root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{key}.exe")
        yield shutil.which(key + ".exe")

    def resolve(self, key: str, target: str | None = None, force: bool = False) -> str | None:
        """Liefert die URL des Symbols oder None. Blockierend – im Thread aufrufen."""
        key = safe_key(key)
        if not key or not self._win:
            return None
        path = self.folder / f"{key}.png"
        if path.exists():
            return self.url(key)
        if not force and time.monotonic() - self._failed.get(key, -1e9) < RETRY_AFTER:
            return None
        with self._lock:
            for exe in self._candidates(key, target):
                if not exe or not os.path.exists(exe):
                    continue
                try:
                    data = _store_logo(exe) if "\\windowsapps\\" in exe.lower() else None
                    data = data or self._win.png(exe)
                except Exception as exc:
                    log.debug("Symbol aus %s nicht lesbar: %s", exe, exc)
                    continue
                if data:
                    self.folder.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                    log.info("Programm-Symbol gefunden: %s (%s)", key, exe)
                    self._failed.pop(key, None)
                    return self.url(key)
            self._failed[key] = time.monotonic()
        return None

    def forget(self, key: str) -> None:
        key = safe_key(key)
        try:
            (self.folder / f"{key}.png").unlink()
        except OSError:
            pass
        self._failed.pop(key, None)
