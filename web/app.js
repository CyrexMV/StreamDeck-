/* TabDeck – Tablet-Oberfläche */
"use strict";

/* ====================================================================== Hilfen */
const $ = (sel, el = document) => el.querySelector(sel);

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = v;
    else if (k === "html") el.innerHTML = v;
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (k === "value" || (k in el && typeof v !== "string")) el[k] = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  return el;
}

function fill(el, ...kids) {
  el.replaceChildren(...kids.flat(Infinity).filter((k) => k != null && k !== false));
  return el;
}

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clone = (o) => JSON.parse(JSON.stringify(o));
const safeColor = (c, d = "#2a2e37") => (/^#[0-9a-f]{3,8}$/i.test(c || "") ? c : d);
const appKey = (name) => String(name || "").toLowerCase().replace(/\.exe$/, "");
const uid = () => Math.random().toString(36).slice(2, 8);

const ICONS = {
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/>',
  full: '<path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
  up: '<path d="m18 15-6-6-6 6"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
  move: '<path d="m5 9-3 3 3 3M9 5l3-3 3 3M15 19l-3 3-3-3M19 9l3 3-3 3M2 12h20M12 2v20"/>',
  play: '<path d="M7 4.5v15l12-7.5Z"/>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  rec: '<circle cx="12" cy="12" r="7"/>',
};
const icon = (name) => `<svg class="i" viewBox="0 0 24 24">${ICONS[name]}</svg>`;
const iconEl = (name) => h("span", { html: icon(name), style: { display: "contents" } });

/* ================================================================= Konstanten */
const C = {
  discord: "#5865F2", spotify: "#1DB954", obs: "#3a3f4b", rec: "#d63c3c", sys: "#2f6fde",
  grey: "#2a2e37", dark: "#1b1e25", vol: "#7c5cff", warn: "#c9572b", green: "#2e9e6a",
};
const PALETTE = ["#1b1e25", "#2a2e37", "#3a3f4b", "#5865F2", "#7c5cff", "#b44bd6", "#d9467f", "#d63c3c",
  "#c9572b", "#e0a526", "#1DB954", "#2e9e6a", "#0e7490", "#2f6fde", "#f2f2f2"];
const EMOJIS = ("🎙️ 🔇 🎤 🚫 🎧 🙉 🔊 🔉 🔈 ⏯️ ⏸️ ▶️ ⏭️ ⏮️ ⏹️ ⏺️ 🔴 📡 🎬 🎥 📷 📸 💾 🖼️ ✨ 🎛️ 🎚️ 💬 🗣️ 🎵 🎶 🔀 🔁 " +
  "🌐 📁 📂 📊 ✂️ 🪟 🔒 🔓 😴 🔄 ⏻ 🌙 ☀️ 💡 ⚡ 🔥 ⭐ ❤️ 👍 👋 😂 😎 🤖 🎮 🕹️ 🏆 🎯 🛒 📋 📥 ↩️ ⬅️ ➡️ ⬆️ ⬇️ 🏠 " +
  "⚙️ 🧠 🖥️ 💻 ⌨️ 🖱️ 📝 📧 📅 ⏰ 🕒 ☕ 🍕 🎉 🔔 🔕 ✅ ❌ ⚠️ ❓ 💰 📈 🧹 🗑️ 🔍 🎨 📌 🚀 🐞 🛠️ 🧩 🎁").split(" ");

const KEY_HELP = "Tasten mit + verbinden, z. B. <code>ctrl+shift+m</code>, <code>alt+tab</code>, <code>win+d</code>, <code>f13</code>. " +
  "Namen: ctrl, shift, alt, win, enter, esc, tab, space, delete, up/down/left/right, f1–f24, num0–num9, printscreen, " +
  "play_pause, next, previous, volume_up/down/mute.";

const OBS_OPS = [
  ["scene", "Szene wechseln"], ["record_toggle", "Aufnahme starten/stoppen"], ["record_pause", "Aufnahme pausieren/fortsetzen"],
  ["stream_toggle", "Stream starten/stoppen"], ["mute_toggle", "Audioquelle stumm an/aus"], ["source_toggle", "Quelle ein-/ausblenden"],
  ["virtualcam_toggle", "Virtuelle Kamera an/aus"], ["replay_toggle", "Replay-Puffer an/aus"], ["replay_save", "Replay speichern"],
  ["studio_toggle", "Studio-Modus an/aus"], ["transition", "Übergang ausführen (Studio-Modus)"], ["screenshot", "Screenshot"],
  ["record_start", "Aufnahme starten"], ["record_stop", "Aufnahme stoppen"], ["stream_start", "Stream starten"], ["stream_stop", "Stream stoppen"],
];

const ACTIONS = {
  hotkey: {
    name: "Tastenkombination", group: "Allgemein", defaults: { keys: "", mode: "press" },
    fields: [
      { k: "keys", label: "Tasten", type: "hotkey", ph: "z. B. ctrl+shift+m", help: KEY_HELP },
      { k: "mode", label: "Verhalten", type: "select", options: [["press", "Einmal drücken"], ["hold", "Gedrückt halten, solange die Taste gedrückt ist"]] },
    ],
  },
  text: {
    name: "Text schreiben", group: "Allgemein", defaults: { text: "", enter: false },
    fields: [{ k: "text", label: "Text", type: "textarea" }, { k: "enter", label: "Danach Enter drücken", type: "checkbox" }],
  },
  open: {
    name: "Programm / Datei / Website öffnen", group: "Allgemein", defaults: { target: "", args: "" },
    fields: [
      { k: "target", label: "Pfad oder Adresse", type: "text", ph: "C:\\Pfad\\programm.exe oder https://…",
        help: "Auch möglich: <code>spotify:</code>, <code>discord://</code>, <code>steam://rungameid/730</code>, <code>ms-settings:</code>, <code>explorer.exe</code>" },
      { k: "args", label: "Startparameter (optional)", type: "text" },
    ],
  },
  command: {
    name: "Befehl ausführen", group: "Allgemein", defaults: { command: "" },
    fields: [{ k: "command", label: "Befehl (Eingabeaufforderung)", type: "textarea", ph: "z. B. start notepad" }],
  },
  delay: {
    name: "Warten", group: "Allgemein", defaults: { ms: 500 },
    fields: [{ k: "ms", label: "Millisekunden", type: "number", min: 0, max: 60000, step: 50 }],
  },
  media: {
    name: "Medien (alle Player)", group: "Medien & Ton", defaults: { op: "play_pause" },
    fields: [{ k: "op", label: "Funktion", type: "select", options: [["play_pause", "Play/Pause"], ["next", "Nächster Titel"], ["previous", "Vorheriger Titel"], ["stop", "Stopp"]] }],
  },
  spotify: {
    name: "Spotify", group: "Medien & Ton", defaults: { op: "play_pause" },
    fields: [
      { k: "op", label: "Funktion", type: "select", options: [["play_pause", "Play/Pause"], ["next", "Nächster Titel"], ["previous", "Vorheriger Titel"],
        ["volume_up", "Spotify lauter (in der App)"], ["volume_down", "Spotify leiser (in der App)"], ["volume_set", "Spotify-Lautstärke auf Wert setzen"],
        ["mute_toggle", "Spotify stumm an/aus (in der App)"], ["like", "Titel liken / entfernen (❤️)"],
        ["shuffle", "Zufallswiedergabe an/aus"], ["repeat", "Wiederholen umschalten"]] },
      { k: "step", label: "Schritt in %", type: "number", min: 1, max: 100, show: (a) => a.op === "volume_up" || a.op === "volume_down" },
      { k: "step", label: "Lautstärke in %", type: "number", min: 0, max: 100, show: (a) => a.op === "volume_set" },
      { k: "_hint", type: "info", show: (a) => ["volume_up", "volume_down", "volume_set", "mute_toggle", "like"].includes(a.op),
        html: "Ändert die Lautstärke <b>direkt in der Spotify-App</b>. Dafür einmalig unter ⚙️ Einstellungen → Spotify verbinden (Spotify Premium nötig)." },
    ],
  },
  volume: {
    name: "Lautstärke", group: "Medien & Ton", defaults: { target: "master", op: "up", step: 5, app: "" },
    fields: [
      { k: "target", label: "Ziel", type: "select", options: [["master", "PC-Lautstärke"], ["mic", "Mikrofon (Windows)"], ["app", "Einzelnes Programm"]] },
      { k: "app", label: "Programm", type: "datalist", source: "audioApps", ph: "z. B. Spotify.exe", show: (a) => a.target === "app",
        help: "Programme erscheinen in der Liste, sobald sie Ton abspielen. Du kannst den Namen auch eintippen (z. B. Discord.exe, chrome.exe)." },
      { k: "op", label: "Funktion", type: "select", options: [["up", "Lauter"], ["down", "Leiser"], ["set", "Auf festen Wert setzen"], ["toggle_mute", "Stumm an/aus"], ["mute", "Stumm schalten"], ["unmute", "Stumm aufheben"]] },
      { k: "step", label: "Schritt in %", type: "number", min: 1, max: 100, show: (a) => a.op === "up" || a.op === "down" },
      { k: "step", label: "Lautstärke in %", type: "number", min: 0, max: 100, show: (a) => a.op === "set" },
    ],
  },
  obs: {
    name: "OBS Studio", group: "Programme", defaults: { op: "scene", scene: "" },
    fields: [
      { k: "op", label: "Funktion", type: "select", options: OBS_OPS },
      { k: "scene", label: "Szene", type: "datalist", source: "obsScenes", show: (a) => a.op === "scene" || a.op === "source_toggle",
        help: "Die Liste wird aus OBS geladen, sobald OBS verbunden ist." },
      { k: "source", label: "Quelle", type: "datalist", source: "obsSources", show: (a) => a.op === "source_toggle" },
      { k: "input", label: "Audioquelle", type: "datalist", source: "obsInputs", show: (a) => a.op === "mute_toggle" },
    ],
  },
  discord: {
    name: "Discord", group: "Programme", defaults: { op: "mute" },
    help: "Drückt die Tastenkombination aus Einstellungen → Discord. Diese muss in Discord unter Einstellungen → Tastenbelegung genauso eingetragen sein.",
    fields: [{ k: "op", label: "Funktion", type: "select", options: [["mute", "Mikrofon stumm an/aus"], ["deafen", "Ton aus (taub) an/aus"], ["ptt", "Push-to-Talk (halten)"]] }],
  },
  system: {
    name: "Windows", group: "Programme", defaults: { op: "lock" },
    fields: [{ k: "op", label: "Funktion", type: "select", options: [["lock", "PC sperren"], ["monitor_off", "Monitor ausschalten"], ["sleep", "Energiesparmodus"], ["restart", "Neu starten"], ["shutdown", "Herunterfahren"], ["logoff", "Abmelden"]] }],
  },
  page: { name: "Seite / Ordner öffnen", group: "Navigation", defaults: { page: "" }, fields: [{ k: "page", label: "Seite", type: "page" }] },
  back: { name: "Zurück zur vorherigen Seite", group: "Navigation", defaults: {}, fields: [] },
  home: { name: "Zur ersten Seite", group: "Navigation", defaults: {}, fields: [] },
};
const CLIENT_ACTIONS = new Set(["page", "back", "home"]);

const WIDGETS = [["", "Keine (normale Taste)"], ["clock", "Uhr"], ["cpu", "CPU-Auslastung"], ["ram", "Arbeitsspeicher"],
  ["volume", "PC-Lautstärke"], ["nowplaying", "Läuft gerade (Cover)"]];

/* --------------------------------------------------------------- Vorlagen */
const T = (label, icon, color, actions, extra = {}) => ({ label, icon, color, actions, ...extra });
const ACT = (icon, label, color = C.rec) => ({ ...(icon ? { icon } : {}), ...(label ? { label } : {}), color });
const TEMPLATES = [
  { group: "Discord", items: [
    T("Mikro", "🎙️", C.discord, [{ type: "discord", op: "mute" }], { active: ACT("🔇", "Stumm") }),
    T("Taub", "🎧", C.discord, [{ type: "discord", op: "deafen" }], { active: ACT("🙉", "Taub") }),
    T("Push-to-Talk", "🗣️", C.discord, [{ type: "discord", op: "ptt" }]),
    T("Discord leiser", "🔉", C.vol, [{ type: "volume", target: "app", app: "Discord.exe", op: "down", step: 5 }]),
    T("Discord lauter", "🔊", C.vol, [{ type: "volume", target: "app", app: "Discord.exe", op: "up", step: 5 }]),
    T("Discord öffnen", "💬", C.discord, [{ type: "open", target: "discord://" }]),
  ] },
  { group: "Spotify", items: [
    T("", "🎵", C.dark, [{ type: "spotify", op: "play_pause" }], { widget: "nowplaying" }),
    T("Play/Pause", "⏯️", C.spotify, [{ type: "spotify", op: "play_pause" }], { active: ACT("⏸️", "Pause", C.spotify) }),
    T("Weiter", "⏭️", C.spotify, [{ type: "spotify", op: "next" }]),
    T("Zurück", "⏮️", C.spotify, [{ type: "spotify", op: "previous" }]),
    T("Zufall", "🔀", C.spotify, [{ type: "spotify", op: "shuffle" }], { active: ACT(null, "Zufall an", "#14833b") }),
    T("Spotify leiser", "🔉", C.spotify, [{ type: "spotify", op: "volume_down", step: 10 }]),
    T("Spotify lauter", "🔊", C.spotify, [{ type: "spotify", op: "volume_up", step: 10 }]),
    T("Spotify stumm", "🔈", C.spotify, [{ type: "spotify", op: "mute_toggle" }], { active: ACT("🔇", "Spotify aus") }),
    T("Gefällt mir", "🤍", C.spotify, [{ type: "spotify", op: "like" }], { active: ACT("💚", "Gespeichert", "#14833b") }),
    T("Spotify öffnen", "🎧", C.spotify, [{ type: "open", target: "spotify:" }]),
  ] },
  { group: "OBS", items: [
    T("Aufnahme", "⏺️", C.obs, [{ type: "obs", op: "record_toggle" }], { active: ACT("🔴", "REC") }),
    T("Stream", "📡", C.obs, [{ type: "obs", op: "stream_toggle" }], { active: ACT("🔴", "LIVE") }),
    T("Szene", "🖼️", C.obs, [{ type: "obs", op: "scene", scene: "" }], { active: ACT(null, null, C.green) }),
    T("Mikrofon", "🎙️", C.obs, [{ type: "obs", op: "mute_toggle", input: "Mikrofon/AUX" }], { active: ACT("🔇", "Mikro stumm") }),
    T("Quelle", "👁️", C.obs, [{ type: "obs", op: "source_toggle", scene: "", source: "" }], { active: ACT(null, null, C.green) }),
    T("Replay speichern", "💾", C.obs, [{ type: "obs", op: "replay_save" }]),
    T("Virtuelle Kamera", "📷", C.obs, [{ type: "obs", op: "virtualcam_toggle" }], { active: ACT(null, "Kamera an") }),
  ] },
  { group: "Ton & Windows", items: [
    T("Lauter", "🔊", C.vol, [{ type: "volume", target: "master", op: "up", step: 5 }]),
    T("Leiser", "🔉", C.vol, [{ type: "volume", target: "master", op: "down", step: 5 }]),
    T("Ton", "🔊", C.vol, [{ type: "volume", target: "master", op: "toggle_mute" }], { active: ACT("🔇", "Ton aus") }),
    T("PC-Mikro", "🎤", C.grey, [{ type: "volume", target: "mic", op: "toggle_mute" }], { active: ACT("🚫", "Mikro aus") }),
    T("Sperren", "🔒", C.grey, [{ type: "system", op: "lock" }]),
    T("Screenshot", "✂️", C.grey, [{ type: "hotkey", keys: "win+shift+s", mode: "press" }]),
    T("Task-Manager", "📊", C.grey, [{ type: "hotkey", keys: "ctrl+shift+esc", mode: "press" }]),
    T("Programm", "🚀", C.sys, [{ type: "open", target: "" }]),
    T("Website", "🌐", C.sys, [{ type: "open", target: "https://" }]),
    T("Text", "📝", C.grey, [{ type: "text", text: "", enter: false }]),
  ] },
  { group: "Anzeigen & Navigation", items: [
    T("", "🕒", C.dark, [], { widget: "clock" }),
    T("", "🧠", C.dark, [], { widget: "cpu" }),
    T("", "💾", C.dark, [], { widget: "ram" }),
    T("", "🔊", C.dark, [], { widget: "volume" }),
    T("Ordner", "📁", C.sys, [{ type: "page", page: "" }]),
    T("Zurück", "⬅️", C.dark, [{ type: "back" }]),
  ] },
];

/* ===================================================================== Zustand */
const App = {
  ws: null,
  token: "",
  config: null,
  state: { obs: {}, audio: {}, media: {}, stats: {}, discord: {}, toggles: {} },
  features: {},
  version: "",
  pageId: null,
  history: [],
  editing: false,
  transposed: false,
  moveFrom: null,
  rpcSeq: 0,
  rpcPending: new Map(),
  retry: 0,
  audioApps: [],
  modalCount: 0,
};

/* =============================================================== Verbindung */
function initToken() {
  const params = new URLSearchParams(location.search);
  const fromUrl = params.get("token");
  if (fromUrl) {
    App.token = fromUrl;
    try { localStorage.setItem("tabdeck.token", fromUrl); } catch {}
    params.delete("token");
    const q = params.toString();
    history.replaceState(null, "", location.pathname + (q ? "?" + q : ""));
  } else {
    try { App.token = localStorage.getItem("tabdeck.token") || ""; } catch {}
  }
}

function connect() {
  if (!App.token) { showLogin(); return; }
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws?token=${encodeURIComponent(App.token)}`);
  App.ws = ws;
  ws.onmessage = (e) => { try { onMessage(JSON.parse(e.data)); } catch (err) { console.error(err); } };
  ws.onclose = (e) => {
    if (App.ws !== ws) return;
    App.ws = null;
    setStatus(false);
    for (const p of App.rpcPending.values()) p.reject(new Error("Verbindung getrennt"));
    App.rpcPending.clear();
    if (e.code === 4001 || e.code === 4003) {
      showLogin(e.code === 4001 ? "Der Verbindungscode stimmt nicht." : (e.reason || "Zu viele Fehlversuche."));
      return;
    }
    const delay = Math.min(10000, 800 * 2 ** App.retry++);
    setTimeout(connect, delay);
  };
}

function send(msg) {
  if (App.ws && App.ws.readyState === WebSocket.OPEN) { App.ws.send(JSON.stringify(msg)); return true; }
  return false;
}

function rpc(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++App.rpcSeq;
    if (!send({ type: "rpc", id, method, params })) { reject(new Error("Keine Verbindung zum PC")); return; }
    App.rpcPending.set(id, { resolve, reject });
    setTimeout(() => {
      if (App.rpcPending.has(id)) { App.rpcPending.delete(id); reject(new Error("Der PC antwortet nicht")); }
    }, 20000);
  });
}

function onMessage(msg) {
  switch (msg.type) {
    case "hello": {
      App.retry = 0;
      App.config = msg.config;
      App.features = msg.features || {};
      App.version = msg.version;
      Object.assign(App.state, msg.state || {});
      closeLogin();
      setStatus(true);
      let saved = null;
      try { saved = sessionStorage.getItem("tabdeck.page"); } catch {}
      if (!App.pageId || !getPage(App.pageId)) App.pageId = getPage(saved) ? saved : App.config.pages[0].id;
      renderAll();
      break;
    }
    case "config":
      App.config = msg.config;
      if (!getPage(App.pageId)) App.pageId = App.config.pages[0].id;
      renderAll();
      break;
    case "state":
      Object.assign(App.state, msg.state || {});
      refreshFaces();
      document.dispatchEvent(new CustomEvent("tabdeck:state", { detail: Object.keys(msg.state || {}) }));
      break;
    case "result":
      if (!msg.ok) {
        toast(msg.error || "Aktion fehlgeschlagen", "error");
        if (msg.page === App.pageId) {
          const el = slotEl(msg.slot);
          if (el) { el.classList.remove("err"); void el.offsetWidth; el.classList.add("err"); setTimeout(() => el.classList.remove("err"), 600); }
        }
      }
      break;
    case "rpc_result": {
      const p = App.rpcPending.get(msg.id);
      if (!p) break;
      App.rpcPending.delete(msg.id);
      msg.ok ? p.resolve(msg.result) : p.reject(new Error(msg.error || "Fehler"));
      break;
    }
  }
}

function setStatus(ok) {
  const el = $("#status");
  el.classList.toggle("ok", ok);
  el.title = ok ? "Mit dem PC verbunden" : "Nicht verbunden – versuche erneut …";
}

/* ================================================================= Darstellung */
const getPage = (id) => App.config?.pages.find((p) => p.id === id) || null;
const currentPage = () => getPage(App.pageId) || App.config.pages[0];
const S = () => App.config.settings;
const slotEl = (slot) => $(`#grid .slot[data-slot="${slot}"]`);

function renderAll() {
  applySettings();
  renderTabs();
  renderGrid();
}

function applySettings() {
  const s = S();
  const root = document.documentElement.style;
  root.setProperty("--gap", `${s.gap ?? 12}px`);
  root.setProperty("--radius", `${s.radius ?? 18}px`);
  document.body.classList.toggle("no-tabs", s.show_tabs === false);
  layout();
}

function layout() {
  if (!App.config) return;
  const s = S();
  const deck = $("#deck");
  const cs = getComputedStyle(deck);
  const w = deck.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  const hgt = deck.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
  // Im Hochformat das Raster drehen (z. B. 8×4 → 4×8), damit die Fläche genutzt wird
  const transposed = s.rotate_portrait !== false && hgt > w && s.columns > s.rows;
  const cols = transposed ? s.rows : s.columns;
  const rows = transposed ? s.columns : s.rows;
  const gap = s.gap ?? 12;
  const cell = Math.floor(Math.min((w - gap * (cols - 1)) / cols, (hgt - gap * (rows - 1)) / rows));
  const root = document.documentElement.style;
  root.setProperty("--cols", cols);
  root.setProperty("--cell", `${Math.max(40, cell)}px`);
  if (transposed !== App.transposed) {
    App.transposed = transposed;
    if ($("#grid").childElementCount) renderGrid();
  }
}

function renderTabs() {
  const nav = $("#tabs");
  nav.replaceChildren(...App.config.pages.filter((p) => !p.hidden || p.id === App.pageId).map((p) =>
    h("button", { class: "tab" + (p.id === App.pageId ? " active" : ""), text: p.name, onclick: () => gotoPage(p.id, true) })));
}

function renderGrid() {
  const grid = $("#grid");
  const s = S();
  const page = currentPage();
  const count = s.columns * s.rows;
  const slots = [];
  for (let i = 0; i < count; i++) {
    const btn = page.buttons[String(i)];
    const el = h("div", { class: "slot" + (btn ? "" : " empty"), "data-slot": String(i) });
    if (btn) { el._html = faceHTML(btn, page.id, i); el.innerHTML = el._html; }
    if (App.moveFrom === i) el.classList.add("move-src");
    if (App.transposed) {
      el.style.gridRow = String((i % s.columns) + 1);
      el.style.gridColumn = String(Math.floor(i / s.columns) + 1);
    }
    slots.push(el);
  }
  grid.replaceChildren(...slots);
  document.body.classList.toggle("editing", App.editing);
  document.body.classList.toggle("moving", App.moveFrom !== null);
  $("#edithint").hidden = !App.editing;
  $("#edithint span").textContent = App.moveFrom !== null
    ? "Tippe auf das Ziel-Feld, um die Taste dorthin zu verschieben."
    : "Bearbeitungsmodus – tippe auf eine Taste oder ein leeres Feld.";
  $("#btn-edit").classList.toggle("on", App.editing);
}

function refreshFaces() {
  if (!App.config) return;
  const page = currentPage();
  for (const el of document.querySelectorAll("#grid .slot:not(.empty)")) {
    const slot = el.dataset.slot;
    const btn = page.buttons[slot];
    if (!btn) continue;
    const html = faceHTML(btn, page.id, slot);
    if (el._html !== html) { el.innerHTML = html; el._html = html; }
  }
}

function gotoPage(id, fromTabs = false) {
  if (!getPage(id) || id === App.pageId) return;
  if (fromTabs) App.history = [];
  else App.history.push(App.pageId);
  setPage(id);
}

function goBack() {
  let prev = App.history.pop();
  while (prev && (!getPage(prev) || prev === App.pageId)) prev = App.history.pop();
  setPage(prev || App.config.pages[0].id);
}

function setPage(id) {
  if (!getPage(id)) return;
  App.pageId = id;
  App.moveFrom = null;
  try { sessionStorage.setItem("tabdeck.page", id); } catch {}
  renderTabs();
  renderGrid();
}

/* ----------------------------------------------------------- Tasten-Inhalt */
function luminance(hex) {
  let c = hex.replace("#", "");
  if (c.length === 3) c = c.split("").map((x) => x + x).join("");
  const [r, g, b] = [0, 2, 4].map((i) => {
    const v = parseInt(c.substr(i, 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
const autoFg = (bg) => (luminance(bg) > 0.45 ? "#111318" : "#ffffff");

function actionActive(a) {
  const st = App.state;
  const o = st.obs || {}, au = st.audio || {}, m = st.media || {};
  switch (a.type) {
    case "obs": {
      if (!o.connected) return false;
      switch (a.op) {
        case "scene": return o.current_scene === a.scene;
        case "record_toggle": case "record_start": case "record_stop": return !!o.recording;
        case "record_pause": return !!o.record_paused;
        case "stream_toggle": case "stream_start": case "stream_stop": return !!o.streaming;
        case "mute_toggle": return !!(o.muted || {})[a.input];
        case "virtualcam_toggle": return !!o.virtualcam;
        case "replay_toggle": return !!o.replay_buffer;
        case "studio_toggle": return !!o.studio_mode;
        case "source_toggle": return !!((o.sources || {})[a.scene || o.current_scene] || {})[a.source];
      }
      return null;
    }
    case "volume": {
      if (!["toggle_mute", "mute", "unmute"].includes(a.op)) return null;
      const t = a.target === "app" ? (au.apps || {})[appKey(a.app)] : au[a.target];
      return !!(t && t.muted);
    }
    case "spotify":
      if (a.op === "play_pause") return !!m.spotify_playing;
      if (a.op === "shuffle") return !!m.spotify_shuffle;
      if (a.op === "like") return !!st.spotify?.liked;
      if (a.op === "mute_toggle") return st.spotify?.volume === 0;
      return null;
    case "media":
      return a.op === "play_pause" ? !!m.playing : null;
    case "discord":
      return a.op === "mute" || a.op === "deafen" ? !!(st.discord || {})[a.op] : null;
  }
  return null;
}

function isActive(btn, pageId, slot) {
  if (btn.toggle) return !!(App.state.toggles || {})[`${pageId}:${slot}`];
  for (const a of btn.actions || []) {
    const r = actionActive(a);
    if (r !== null) return r;
  }
  return false;
}

function valueText(btn) {
  const a = (btn.actions || [])[0];
  if (a && a.type === "spotify" && /^volume_/.test(a.op || "")) {
    const v = App.state.spotify?.volume;
    return v != null ? `${v}%` : "";
  }
  if (!a || a.type !== "volume" || !["up", "down", "set"].includes(a.op)) return "";
  const au = App.state.audio || {};
  const t = a.target === "app" ? (au.apps || {})[appKey(a.app)] : au[a.target];
  return t && t.level != null ? `${t.level}%` : "";
}

function gauge(pct, title, color) {
  const r = 40, c = 2 * Math.PI * r;
  const p = pct == null ? 0 : Math.max(0, Math.min(100, pct));
  return `<div class="w-gauge" style="--g:${color}"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="${r}" class="g-bg"/>` +
    `<circle cx="50" cy="50" r="${r}" class="g-fg" stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${(c * (1 - p / 100)).toFixed(1)}"/></svg>` +
    `<div class="g-text"><b>${pct == null ? "–" : Math.round(pct) + "%"}</b><span>${esc(title)}</span></div></div>`;
}
const loadColor = (p) => (p == null ? "#7c5cff" : p < 60 ? "#30a46c" : p < 85 ? "#e0a526" : "#e5484d");

function widgetHTML(btn, label) {
  const st = App.state;
  switch (btn.widget) {
    case "clock": {
      const d = new Date();
      const time = d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
      const date = d.toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "short" });
      return `<div class="w-clock"><span class="w-time">${time}</span><span class="w-date">${esc(label || date)}</span></div>`;
    }
    case "cpu": return gauge(st.stats?.cpu, label || "CPU", loadColor(st.stats?.cpu));
    case "ram": return gauge(st.stats?.ram, label || "RAM", loadColor(st.stats?.ram));
    case "volume": {
      const m = st.audio?.master;
      return gauge(m ? m.level : null, m && m.muted ? "🔇 stumm" : (label || "Lautstärke"), m && m.muted ? "#e5484d" : "#7c5cff");
    }
    case "nowplaying": {
      const m = st.media || {};
      if (!m.title) {
        return `<div class="w-np empty"><span class="icon">${esc(btn.icon || "🎵")}</span>` +
          `<span class="label">${esc(m.available === false ? "Läuft gerade (nur Windows)" : "Gerade läuft nichts")}</span></div>`;
      }
      const bg = m.cover ? ` style="background-image:url('${m.cover.replace(/'/g, "%27")}')"` : "";
      const playing = m.shown_playing ?? m.playing;
      return `<div class="w-np"${bg}><div class="shade"></div><span class="np-state">${playing ? "▶️" : "⏸️"}</span>` +
        `<div class="np-text"><b>${esc(m.title)}</b><span>${esc(m.artist)}</span></div></div>`;
    }
  }
  return "";
}

function faceHTML(btn, pageId, slot, forceActive = null) {
  const active = forceActive ?? isActive(btn, pageId, slot);
  const alt = active && btn.active ? btn.active : {};
  const color = safeColor(alt.color || btn.color);
  const fg = autoFg(color);
  const ico = alt.icon || btn.icon || "";
  const label = alt.label || btn.label || "";
  const showLabels = S().show_labels !== false;
  let inner, cls = "face";
  if (btn.widget) {
    inner = widgetHTML(btn, label);
  } else {
    const visual = btn.image
      ? `<img class="img" src="${esc(btn.image)}" alt="" draggable="false">`
      : ico ? `<span class="icon">${esc(ico)}</span>` : "";
    if (btn.image && btn.image_fill) cls += " img-fill";
    inner = visual + (showLabels && label ? `<span class="label">${esc(label)}</span>` : "");
    const val = valueText(btn);
    if (val) inner += `<span class="value">${val}</span>`;
  }
  if (active) {
    cls += " active";
    const pulsing = (btn.actions || []).some((a) => a.type === "obs" && /^(record|stream)_/.test(a.op || ""));
    if (pulsing) cls += " pulse";
  }
  return `<div class="${cls}" style="--b:${color};--f:${fg}">${inner}</div>`;
}

/* ================================================================ Bedienung */
function setupGrid() {
  const grid = $("#grid");
  grid.addEventListener("contextmenu", (e) => e.preventDefault());

  grid.addEventListener("pointerdown", (e) => {
    const el = e.target.closest(".slot");
    if (!el || App.editing || el.classList.contains("empty")) return;
    e.preventDefault();
    try { el.setPointerCapture(e.pointerId); } catch {}
    pressStart(el);
  });
  const end = (e) => {
    const el = e.target.closest?.(".slot");
    if (el && el._down) pressEnd(el);
  };
  grid.addEventListener("pointerup", end);
  grid.addEventListener("pointercancel", end);
  grid.addEventListener("lostpointercapture", end);

  grid.addEventListener("click", (e) => {
    if (!App.editing) return;
    const el = e.target.closest(".slot");
    if (!el) return;
    const slot = Number(el.dataset.slot);
    if (App.moveFrom !== null) { finishMove(slot); return; }
    openEditor(slot);
  });
}

async function pressStart(el) {
  const page = currentPage();
  const slot = el.dataset.slot;
  const btn = page.buttons[slot];
  if (!btn) return;
  if (btn.confirm) {
    const ok = await confirmDialog(`„${btn.label || "Aktion"}“ wirklich ausführen?`, "Ausführen");
    if (!ok) return;
    if (!send({ type: "down", page: page.id, slot })) { toast("Keine Verbindung zum PC", "error"); return; }
    send({ type: "up", page: page.id, slot });
    runClientActions(btn);
    return;
  }
  el._down = true;
  el.classList.add("pressed");
  if (S().haptics !== false && navigator.vibrate) navigator.vibrate(12);
  const hasServerActions = (btn.actions || []).some((a) => !CLIENT_ACTIONS.has(a.type));
  if (hasServerActions || btn.toggle) {
    if (!send({ type: "down", page: page.id, slot })) toast("Keine Verbindung zum PC", "error");
  }
  if ((btn.actions || []).some((a) => CLIENT_ACTIONS.has(a.type))) {
    pressEnd(el);
    runClientActions(btn);
  }
}

function pressEnd(el) {
  el._down = false;
  el.classList.remove("pressed");
  send({ type: "up", page: App.pageId, slot: el.dataset.slot });
}

function runClientActions(btn) {
  for (const a of btn.actions || []) {
    if (a.type === "page" && a.page) { gotoPage(a.page); return; }
    if (a.type === "back") { goBack(); return; }
    if (a.type === "home") { App.history = []; setPage(App.config.pages[0].id); return; }
  }
}

function setEditing(on) {
  App.editing = on;
  App.moveFrom = null;
  renderGrid();
}

async function saveConfig(cfg, okMsg) {
  try {
    await rpc("save_config", { config: cfg });
    App.config = cfg;
    renderAll();
    if (okMsg) toast(okMsg, "ok");
    return true;
  } catch (err) {
    toast("Speichern fehlgeschlagen: " + err.message, "error");
    return false;
  }
}

function finishMove(target) {
  const from = App.moveFrom;
  App.moveFrom = null;
  if (from === target) { renderGrid(); return; }
  const cfg = clone(App.config);
  const page = cfg.pages.find((p) => p.id === App.pageId);
  const a = page.buttons[String(from)], b = page.buttons[String(target)];
  delete page.buttons[String(from)];
  delete page.buttons[String(target)];
  if (a) page.buttons[String(target)] = a;
  if (b) page.buttons[String(from)] = b;
  saveConfig(cfg);
}

/* ================================================================== Dialoge */
function openModal({ title, body, footer = [], sheet = false, small = false, onClose, closable = true, head = [] }) {
  const modal = h("div", { class: "modal" + (small ? " small" : "") },
    title ? h("div", { class: "m-head" }, h("h2", { text: title }), head,
      closable ? h("button", { class: "icon-btn", html: icon("x"), "aria-label": "Schließen", onclick: () => close() }) : null) : null,
    body,
    footer.length ? h("div", { class: "m-foot" }, footer) : null);
  const back = h("div", { class: "backdrop" + (sheet ? " sheet" : "") }, modal);
  back.addEventListener("pointerdown", (e) => { if (e.target === back && closable) back._downOnBack = true; });
  back.addEventListener("click", (e) => { if (e.target === back && back._downOnBack) close(); back._downOnBack = false; });
  const onKey = (e) => {
    if (e.key !== "Escape" || !closable) return;
    const all = document.querySelectorAll(".backdrop");
    if (all[all.length - 1] === back) close();  // nur den obersten Dialog schließen
  };
  document.addEventListener("keydown", onKey);
  document.body.append(back);
  App.modalCount++;
  let closed = false;
  function close(result) {
    if (closed) return;
    closed = true;
    App.modalCount--;
    document.removeEventListener("keydown", onKey);
    back.remove();
    onClose && onClose(result);
  }
  return { close, el: modal, back };
}

function confirmDialog(text, okLabel = "OK", danger = true) {
  return new Promise((resolve) => {
    let result = false;
    const m = openModal({
      title: "Bitte bestätigen", small: true,
      body: h("div", { class: "m-body" }, h("p", { text, style: { margin: 0, fontSize: "16px", lineHeight: 1.5 } })),
      footer: [
        h("div", { class: "spacer" }),
        h("button", { class: "btn ghost", text: "Abbrechen", onclick: () => m.close() }),
        h("button", { class: "btn " + (danger ? "danger" : "primary"), text: okLabel, onclick: () => { result = true; m.close(); } }),
      ],
      onClose: () => resolve(result),
    });
  });
}

function toast(text, kind = "") {
  const el = h("div", { class: "toast " + kind, text });
  $("#toasts").append(el);
  setTimeout(() => el.remove(), kind === "error" ? 5000 : 2600);
}

/* ------------------------------------------------------------------ Login */
let loginModal = null;
function showLogin(error) {
  if (loginModal) { loginModal.close(); loginModal = null; }
  const input = h("input", { type: "text", maxlength: "12", placeholder: "XXXX-XXXX", autocapitalize: "characters", autocomplete: "off", spellcheck: "false", value: "" });
  const go = () => {
    const v = input.value.trim();
    if (!v) return;
    App.token = v;
    try { localStorage.setItem("tabdeck.token", v); } catch {}
    loginModal.close();
    loginModal = null;
    App.retry = 0;
    connect();
  };
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
  loginModal = openModal({
    small: true, closable: false,
    body: h("div", { class: "m-body login" },
      h("div", { class: "big", text: "🎛️" }),
      h("h2", { text: "Mit dem PC verbinden", style: { margin: "0 0 8px" } }),
      h("p", { class: "help", style: { fontSize: "14px" }, html: "Gib den Verbindungscode ein, der im TabDeck-Fenster auf deinem PC angezeigt wird – oder scanne den QR-Code unter <code>http://localhost:8765/connect</code> am PC." }),
      error ? h("p", { text: error, style: { color: "#ff7b7f", fontWeight: 600 } }) : null,
      input,
      h("button", { class: "btn primary", text: "Verbinden", style: { width: "100%", justifyContent: "center" }, onclick: go })),
  });
  setTimeout(() => input.focus(), 100);
}
function closeLogin() { if (loginModal) { loginModal.close(); loginModal = null; } }

/* ================================================================== Editor */
function previewEl(btn, active = false) {
  const el = h("div", { class: "preview" });
  el.innerHTML = faceHTML(btn, App.pageId, -1, active);
  return el;
}

async function readImage(file) {
  if (file.type === "image/gif" && file.size < 1.5e6) {
    return await new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(file); });
  }
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error("Bild konnte nicht geladen werden")); i.src = url; });
    const max = 288;
    const scale = Math.min(1, max / Math.max(img.width, img.height));
    const canvas = h("canvas", { width: Math.round(img.width * scale), height: Math.round(img.height * scale) });
    canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/png");
  } finally {
    URL.revokeObjectURL(url);
  }
}

function sourceOptions(source, action) {
  const o = App.state.obs || {};
  switch (source) {
    case "obsScenes": return o.scenes || [];
    case "obsInputs": return o.inputs || [];
    case "obsSources": return Object.keys((o.sources || {})[action.scene || o.current_scene] || {});
    case "audioApps": return App.audioApps;
  }
  return [];
}

function keyNameFromEvent(e) {
  if (/^Digit\d$/.test(e.code)) return e.code.slice(5);
  if (/^F\d{1,2}$/.test(e.code)) return e.code.toLowerCase();
  if (/^Numpad\d$/.test(e.code)) return "num" + e.code.slice(6);
  const map = {
    Space: "space", Enter: "enter", NumpadEnter: "enter", Escape: "esc", Tab: "tab", Backspace: "backspace", Delete: "delete",
    Insert: "insert", Home: "home", End: "end", PageUp: "pageup", PageDown: "pagedown", ArrowUp: "up", ArrowDown: "down",
    ArrowLeft: "left", ArrowRight: "right", PrintScreen: "printscreen", Pause: "pause", ContextMenu: "menu",
    NumpadAdd: "numplus", NumpadSubtract: "numminus", NumpadMultiply: "nummultiply", NumpadDivide: "numdivide", NumpadDecimal: "numdecimal",
    MediaPlayPause: "play_pause", MediaTrackNext: "next", MediaTrackPrevious: "previous",
    AudioVolumeUp: "volume_up", AudioVolumeDown: "volume_down", AudioVolumeMute: "volume_mute",
  };
  if (map[e.code]) return map[e.code];
  if (e.key && e.key.length === 1) {
    const k = e.key.toLowerCase();
    return k === "+" ? "plus" : k === "," ? "comma" : k;
  }
  return null;
}

/* ---------------------------------------------------- Tastenauswahl (ohne Tastatur) */
const MOD_KEYS = [["ctrl", "Strg"], ["shift", "Umschalt"], ["alt", "Alt"], ["win", "Win"]];
const MOD_ALIAS = { ctrl: "ctrl", strg: "ctrl", control: "ctrl", shift: "shift", umschalt: "shift", alt: "alt", win: "win", windows: "win", cmd: "win", meta: "win" };
const range = (a, b, fn) => Array.from({ length: b - a + 1 }, (_, i) => fn(a + i));
const PICK_KEYS = [
  ["F13–F24 (kollisionsfrei, ideal für Discord)", range(13, 24, (i) => [`f${i}`, `F${i}`])],
  ["F1–F12", range(1, 12, (i) => [`f${i}`, `F${i}`])],
  ["Buchstaben", range(97, 122, (c) => [String.fromCharCode(c), String.fromCharCode(c).toUpperCase()])],
  ["Zahlen", range(0, 9, (i) => [String(i), String(i)])],
  ["Ziffernblock", [...range(0, 9, (i) => [`num${i}`, `Num ${i}`]), ["numplus", "Num +"], ["numminus", "Num −"], ["nummultiply", "Num ×"], ["numdivide", "Num ÷"]]],
  ["Sondertasten", [["space", "Leertaste"], ["enter", "Enter"], ["esc", "Esc"], ["tab", "Tab"], ["backspace", "Rücktaste"],
    ["delete", "Entf"], ["insert", "Einfg"], ["home", "Pos1"], ["end", "Ende"], ["pageup", "Bild ↑"], ["pagedown", "Bild ↓"],
    ["up", "Pfeil ↑"], ["down", "Pfeil ↓"], ["left", "Pfeil ←"], ["right", "Pfeil →"], ["printscreen", "Druck"], ["pause", "Pause"]]],
  ["Medientasten", [["play_pause", "Play/Pause"], ["next", "Nächster Titel"], ["previous", "Vorheriger Titel"],
    ["volume_up", "Lauter"], ["volume_down", "Leiser"], ["volume_mute", "Stumm"]]],
];
const KEY_LABELS = Object.fromEntries(PICK_KEYS.flatMap(([, items]) => items));

function splitCombo(value) {
  const parts = String(value || "").toLowerCase().split("+").map((x) => x.trim()).filter(Boolean);
  const mods = new Set();
  let key = "";
  for (const p of parts) {
    if (MOD_ALIAS[p]) mods.add(MOD_ALIAS[p]);
    else key = p;
  }
  return { mods, key };
}
const joinCombo = (mods, key) => [...MOD_KEYS.map(([m]) => m).filter((m) => mods.has(m)), key].filter(Boolean).join("+");
const prettyCombo = (value) => {
  const { mods, key } = splitCombo(value);
  return [...MOD_KEYS.filter(([m]) => mods.has(m)).map(([, l]) => l), KEY_LABELS[key] || key.toUpperCase()].filter(Boolean).join(" + ");
};

/* Tastenkombination wählen: per Antippen (Tablet), per Tastatur aufnehmen oder eintippen.
   opts.send: zusätzlich „An PC senden“ (zum Einlernen in Discord & Co.) */
function hotkeyInput(action, f, onChange, opts = {}) {
  const wrap = h("div", { class: "hotkey" });
  let listening = false;
  const set = (v) => { action[f.k] = v; onChange(); render(); };

  const onKey = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (["Control", "Shift", "Alt", "Meta", "AltGraph", "OS"].includes(e.key)) return;
    const name = keyNameFromEvent(e);
    if (!name) return;
    const mods = new Set();
    if (e.ctrlKey) mods.add("ctrl");
    if (e.shiftKey) mods.add("shift");
    if (e.altKey) mods.add("alt");
    if (e.metaKey) mods.add("win");
    stopListening();
    set(joinCombo(mods, name));
  };
  const stopListening = () => { listening = false; window.removeEventListener("keydown", onKey, true); };

  function render() {
    const { mods, key } = splitCombo(action[f.k]);
    const known = key === "" || key in KEY_LABELS;
    fill(wrap,
      h("div", { class: "row wrap" },
        MOD_KEYS.map(([m, label]) => h("button", { class: "chip" + (mods.has(m) ? " on" : ""), text: label,
          onclick: () => { mods.has(m) ? mods.delete(m) : mods.add(m); set(joinCombo(mods, key)); } })),
        h("span", { class: "plus", text: "+" }),
        h("select", { class: "key-select", value: known ? key : "__custom", onchange: (e) => { if (e.target.value !== "__custom") set(joinCombo(mods, e.target.value)); } },
          h("option", { value: "", text: "– Taste wählen –" }),
          known ? null : h("option", { value: "__custom", text: key.toUpperCase() }),
          PICK_KEYS.map(([group, items]) => h("optgroup", { label: group }, items.map(([v, l]) => h("option", { value: v, text: l })))))),
      h("div", { class: "row", style: { marginTop: "8px" } },
        h("input", { type: "text", value: action[f.k] ?? "", placeholder: f.ph || "", autocapitalize: "off", spellcheck: "false",
          oninput: (e) => { action[f.k] = e.target.value.trim(); onChange(); }, onchange: () => render() }),
        h("button", { class: "btn small" + (listening ? " primary" : ""), html: listening ? "Tasten drücken …" : icon("rec") + "Tastatur",
          title: "Mit angeschlossener Tastatur (z. B. Book Cover Keyboard oder am PC) aufnehmen",
          onclick: () => {
            if (listening) { stopListening(); render(); return; }
            listening = true; window.addEventListener("keydown", onKey, true); render();
          } }),
        opts.send ? sendButton(() => action[f.k]) : null),
      action[f.k] ? h("div", { class: "help", text: "Ergebnis: " + prettyCombo(action[f.k]) }) : null,
    );
  }
  render();
  return wrap;
}

/* Sendet eine Kombination nach kurzem Countdown an den PC – zum Einlernen in Discord */
function sendButton(getKeys) {
  const btn = h("button", { class: "btn small", html: icon("play") + "An PC senden" });
  btn.onclick = async () => {
    const keys = getKeys();
    if (!keys) { toast("Bitte zuerst eine Taste wählen", "error"); return; }
    btn.disabled = true;
    for (let i = 2; i > 0; i--) { btn.textContent = `Sende in ${i} …`; await new Promise((r) => setTimeout(r, 1000)); }
    try {
      await rpc("send_keys", { keys, delay: 0 });
      btn.textContent = "Gesendet ✓";
    } catch (err) {
      toast(err.message, "error");
      btn.textContent = "Fehler";
    }
    setTimeout(() => { btn.disabled = false; btn.innerHTML = icon("play") + "An PC senden"; }, 1500);
  };
  return btn;
}

function fieldEl(action, f, rerender, onChange) {
  const val = action[f.k];
  let input;
  if (f.type === "info") return h("div", { class: "help", html: f.html, style: { marginBottom: "10px" } });
  switch (f.type) {
    case "select":
      input = h("select", { value: val ?? f.options[0][0], onchange: (e) => { action[f.k] = e.target.value; onChange(); rerender(); } },
        f.options.map(([v, l]) => h("option", { value: v, text: l })));
      break;
    case "page":
      input = h("select", { value: val ?? "", onchange: (e) => { action[f.k] = e.target.value; onChange(); } },
        h("option", { value: "", text: "– Seite wählen –" }),
        App.config.pages.map((p) => h("option", { value: p.id, text: p.name })));
      break;
    case "checkbox":
      return h("label", { class: "check" }, h("input", { type: "checkbox", checked: !!val, onchange: (e) => { action[f.k] = e.target.checked; onChange(); } }), f.label);
    case "number":
      input = h("input", { type: "number", value: val ?? "", min: f.min, max: f.max, step: f.step || 1, inputmode: "numeric",
        oninput: (e) => { action[f.k] = e.target.value === "" ? "" : Number(e.target.value); onChange(); } });
      break;
    case "textarea":
      input = h("textarea", { value: val ?? "", placeholder: f.ph || "", spellcheck: "false", oninput: (e) => { action[f.k] = e.target.value; onChange(); } });
      break;
    case "hotkey":
      input = hotkeyInput(action, f, onChange);
      break;
    case "datalist": {
      const id = "dl-" + uid();
      const opts = sourceOptions(f.source, action);
      input = h("div", {},
        h("input", { type: "text", value: val ?? "", placeholder: f.ph || (opts.length ? "Auswählen oder eintippen" : ""), list: id, spellcheck: "false",
          oninput: (e) => { action[f.k] = e.target.value; onChange(); }, onchange: () => rerender() }),
        h("datalist", { id }, opts.map((o) => h("option", { value: o }))));
      break;
    }
    default:
      input = h("input", { type: "text", value: val ?? "", placeholder: f.ph || "", spellcheck: "false", oninput: (e) => { action[f.k] = e.target.value; onChange(); } });
  }
  return h("div", { class: "field" }, h("label", { text: f.label }), input, f.help ? h("div", { class: "help", html: f.help }) : null);
}

function actionTypeSelect(action, onPick) {
  const groups = {};
  for (const [type, def] of Object.entries(ACTIONS)) (groups[def.group] ||= []).push([type, def.name]);
  return h("select", { value: action.type, onchange: (e) => onPick(e.target.value) },
    Object.entries(groups).map(([g, items]) => h("optgroup", { label: g }, items.map(([v, l]) => h("option", { value: v, text: l })))));
}

function openEditor(slot) {
  const page = currentPage();
  const existing = page.buttons[String(slot)];
  const draft = existing ? clone(existing) : { label: "", icon: "⭐", color: C.grey, actions: [] };
  draft.actions ||= [];
  if (!App.audioApps.length && App.features.audio?.ok) {
    rpc("audio_apps").then((list) => { App.audioApps = list || []; }).catch(() => {});
  }

  const body = h("div", { class: "m-body" });
  const preview = h("div", { class: "row", style: { gap: "10px" } });
  const updatePreview = () => {
    fill(preview, previewEl(draft, false), draft.active || draft.toggle ? previewEl(draft, true) : null);
  };

  const render = () => {
    const scroll = body.scrollTop;
    fill(body,
      h("div", { class: "editor-top" }, preview,
        h("div", { style: { display: "flex", flexDirection: "column", gap: "8px" } },
          h("button", { class: "btn", html: icon("grid") + "Vorlage wählen", onclick: () => openTemplates((tpl) => {
            Object.assign(draft, clone(tpl));
            for (const k of ["image", "image_fill", "toggle", "confirm", "active", "widget"]) if (!(k in tpl)) delete draft[k];
            render();
          }) }),
          h("div", { class: "help", text: (draft.active || draft.toggle) ? "Links normal, rechts im aktiven Zustand." : "Vorschau" }))),
      appearanceSection(draft, render, updatePreview),
      actionsSection(draft, render, updatePreview),
      activeSection(draft, render, updatePreview),
    );
    updatePreview();
    body.scrollTop = scroll;
  };

  const save = async () => {
    const cfg = clone(App.config);
    const p = cfg.pages.find((x) => x.id === page.id);
    for (const a of draft.actions) if (a.type === "volume" && (a.step === "" || a.step == null)) a.step = a.op === "set" ? 50 : 5;
    p.buttons[String(slot)] = draft;
    if (await saveConfig(cfg)) m.close();
  };
  const remove = async () => {
    if (!existing) { m.close(); return; }
    if (!(await confirmDialog("Diese Taste löschen?", "Löschen"))) return;
    const cfg = clone(App.config);
    delete cfg.pages.find((x) => x.id === page.id).buttons[String(slot)];
    if (await saveConfig(cfg)) m.close();
  };
  const move = () => {
    m.close();
    App.moveFrom = slot;
    renderGrid();
  };
  const duplicate = async () => {
    const cfg = clone(App.config);
    const p = cfg.pages.find((x) => x.id === page.id);
    const total = S().columns * S().rows;
    let free = -1;
    for (let i = 0; i < total; i++) if (!p.buttons[String(i)]) { free = i; break; }
    if (free < 0) { toast("Kein freies Feld auf dieser Seite", "error"); return; }
    p.buttons[String(slot)] = clone(draft);
    p.buttons[String(free)] = clone(draft);
    if (await saveConfig(cfg, "Taste dupliziert")) m.close();
  };

  const m = openModal({
    title: existing ? "Taste bearbeiten" : "Neue Taste", sheet: true, body,
    footer: [
      existing ? h("button", { class: "btn danger", html: icon("trash"), title: "Löschen", onclick: remove }) : null,
      existing ? h("button", { class: "btn", html: icon("move"), title: "Verschieben", onclick: move }) : null,
      existing ? h("button", { class: "btn", html: icon("copy"), title: "Duplizieren", onclick: duplicate }) : null,
      h("div", { class: "spacer" }),
      h("button", { class: "btn ghost", text: "Abbrechen", onclick: () => m.close() }),
      h("button", { class: "btn primary", text: "Speichern", onclick: save }),
    ],
  });
  render();
  const onState = () => updatePreview();
  document.addEventListener("tabdeck:state", onState);
  const origClose = m.close;
  m.close = (r) => { document.removeEventListener("tabdeck:state", onState); origClose(r); };
}

function appearanceSection(draft, render, updatePreview) {
  const emojiGrid = h("div", { class: "emoji-grid", hidden: true },
    EMOJIS.map((e) => h("button", { text: e, onclick: () => { draft.icon = e; iconInput.value = e; updatePreview(); } })));
  const iconInput = h("input", { type: "text", value: draft.icon || "", placeholder: "Emoji", style: { width: "90px", textAlign: "center", fontSize: "22px" },
    oninput: (e) => { draft.icon = e.target.value; updatePreview(); } });
  const fileInput = h("input", { type: "file", accept: "image/*", hidden: true, onchange: async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const data = await readImage(file);
      const res = await rpc("upload_icon", { data });
      draft.image = res.url;
      render();
    } catch (err) { toast("Bild-Upload fehlgeschlagen: " + err.message, "error"); }
  } });
  const swatches = h("div", { class: "swatches" },
    PALETTE.map((c) => h("button", { class: "swatch" + (safeColor(draft.color) === c ? " sel" : ""), style: { background: c }, title: c,
      onclick: () => { draft.color = c; render(); } })),
    h("input", { type: "color", value: safeColor(draft.color), oninput: (e) => { draft.color = e.target.value; updatePreview(); }, onchange: () => render() }));

  return h("div", { class: "section" },
    h("h3", { text: "Aussehen" }),
    h("div", { class: "field" }, h("label", { text: "Beschriftung" }),
      h("input", { type: "text", value: draft.label || "", placeholder: "z. B. Mikro stumm", oninput: (e) => { draft.label = e.target.value; updatePreview(); } })),
    h("div", { class: "field" }, h("label", { text: "Symbol" }),
      h("div", { class: "row" }, iconInput,
        h("button", { class: "btn", text: "Emoji-Auswahl", onclick: () => { emojiGrid.hidden = !emojiGrid.hidden; } }),
        h("button", { class: "btn", html: icon("image") + (draft.image ? "Anderes Bild" : "Bild"), onclick: () => fileInput.click() }),
        fileInput),
      emojiGrid,
      draft.image ? h("div", { class: "row", style: { marginTop: "6px", flexWrap: "wrap" } },
        h("label", { class: "check" }, h("input", { type: "checkbox", checked: !!draft.image_fill, onchange: (e) => { draft.image_fill = e.target.checked; updatePreview(); } }), "Bild füllt die ganze Taste"),
        h("button", { class: "btn small danger", text: "Bild entfernen", onclick: () => { delete draft.image; delete draft.image_fill; render(); } })) : null),
    h("div", { class: "field" }, h("label", { text: "Farbe" }), swatches),
    h("div", { class: "field" }, h("label", { text: "Anzeige" }),
      h("select", { value: draft.widget || "", onchange: (e) => { if (e.target.value) draft.widget = e.target.value; else delete draft.widget; render(); } },
        WIDGETS.map(([v, l]) => h("option", { value: v, text: l })))),
  );
}

function actionsSection(draft, render, updatePreview) {
  const list = draft.actions;
  const cards = list.map((a, i) => {
    const def = ACTIONS[a.type] || { name: a.type, fields: [] };
    const card = h("div", { class: "action-card" });
    const renderCard = () => {
      fill(card,
        h("div", { class: "action-head" },
          actionTypeSelect(a, (type) => { list[i] = { type, ...clone(ACTIONS[type].defaults) }; render(); }),
          !CLIENT_ACTIONS.has(a.type) ? h("button", { class: "icon-btn", html: icon("play"), title: "Testen", onclick: async () => {
            try { await rpc("test_action", { action: a }); toast("Ausgeführt ✓", "ok"); } catch (err) { toast(err.message, "error"); }
          } }) : null,
          h("button", { class: "icon-btn", html: icon("up"), title: "Nach oben", disabled: i === 0, onclick: () => { [list[i - 1], list[i]] = [list[i], list[i - 1]]; render(); } }),
          h("button", { class: "icon-btn", html: icon("down"), title: "Nach unten", disabled: i === list.length - 1, onclick: () => { [list[i + 1], list[i]] = [list[i], list[i + 1]]; render(); } }),
          h("button", { class: "icon-btn", html: icon("trash"), title: "Entfernen", onclick: () => { list.splice(i, 1); render(); } })),
        def.help ? h("div", { class: "help", text: def.help, style: { marginBottom: "10px" } }) : null,
        def.fields.filter((f) => !f.show || f.show(a)).map((f) => fieldEl(a, f, renderCard, updatePreview)),
      );
    };
    renderCard();
    return card;
  });
  return h("div", { class: "section" },
    h("h3", { text: "Aktionen" }),
    list.length ? null : h("p", { class: "help", text: draft.widget ? "Anzeige-Tasten brauchen keine Aktion – du kannst aber trotzdem eine hinzufügen." : "Noch keine Aktion. Mehrere Aktionen werden nacheinander ausgeführt." }),
    cards,
    h("button", { class: "btn", html: icon("plus") + "Aktion hinzufügen", onclick: () => { list.push({ type: "hotkey", ...clone(ACTIONS.hotkey.defaults) }); render(); } }),
  );
}

function activeSection(draft, render, updatePreview) {
  const act = draft.active || {};
  const setAct = (k, v) => {
    draft.active = { ...(draft.active || {}) };
    if (v) draft.active[k] = v; else delete draft.active[k];
    if (!Object.keys(draft.active).length) delete draft.active;
    updatePreview();
  };
  return h("div", { class: "section" },
    h("h3", { text: "Aktiver Zustand & Optionen" }),
    h("p", { class: "help", text: "Viele Tasten wissen automatisch, ob sie aktiv sind (OBS-Szene, Aufnahme, Stummschaltung, Spotify spielt …). Hier legst du fest, wie sie dann aussehen." }),
    h("div", { class: "row" },
      h("div", { class: "field" }, h("label", { text: "Symbol (aktiv)" }), h("input", { type: "text", value: act.icon || "", placeholder: "wie normal", oninput: (e) => setAct("icon", e.target.value) })),
      h("div", { class: "field" }, h("label", { text: "Beschriftung (aktiv)" }), h("input", { type: "text", value: act.label || "", placeholder: "wie normal", oninput: (e) => setAct("label", e.target.value) }))),
    h("div", { class: "field" }, h("label", { text: "Farbe (aktiv)" }),
      h("div", { class: "swatches" },
        h("button", { class: "btn small" + (act.color ? "" : " primary"), text: "wie normal", onclick: () => { setAct("color", ""); render(); } }),
        PALETTE.map((c) => h("button", { class: "swatch" + (act.color === c ? " sel" : ""), style: { background: c }, onclick: () => { setAct("color", c); render(); } })))),
    h("label", { class: "check" }, h("input", { type: "checkbox", checked: !!draft.toggle, onchange: (e) => { draft.toggle = e.target.checked; if (!draft.toggle) delete draft.toggle; render(); } }),
      "Umschalt-Taste: merkt sich selbst an/aus (für Aktionen ohne automatische Erkennung)"),
    h("label", { class: "check" }, h("input", { type: "checkbox", checked: !!draft.confirm, onchange: (e) => { draft.confirm = e.target.checked; if (!draft.confirm) delete draft.confirm; } }),
      "Vor dem Ausführen nachfragen (z. B. für Herunterfahren)"),
  );
}

function openTemplates(onPick) {
  const m = openModal({
    title: "Vorlage wählen",
    body: h("div", { class: "m-body" }, TEMPLATES.map((g) => h("div", { class: "tpl-group" },
      h("h4", { text: g.group }),
      h("div", { class: "tpl-list" }, g.items.map((tpl) => h("button", { class: "tpl", onclick: () => { m.close(); onPick(tpl); } },
        previewEl(tpl), tpl.label || WIDGETS.find((w) => w[0] === tpl.widget)?.[1] || ""))),
    ))),
  });
}

/* ============================================================= Einstellungen */
function openSettings() {
  const draft = clone(App.config);
  const s = draft.settings;
  let tab = "general";
  const tabsBar = h("div", { class: "tabs2" });
  const body = h("div", { class: "m-body" });
  const TABS = [["general", "Allgemein"], ["pages", "Seiten"], ["discord", "Discord"], ["spotify", "Spotify"], ["obs", "OBS"], ["backup", "Sicherung"], ["info", "Info"]];

  const num = (obj, key, label, min, max, help) => h("div", { class: "field" }, h("label", { text: label }),
    h("input", { type: "number", min, max, value: obj[key], inputmode: "numeric", oninput: (e) => { const v = Number(e.target.value); if (v >= min && v <= max) obj[key] = v; } }),
    help ? h("div", { class: "help", text: help }) : null);
  const txt = (obj, key, label, help, type = "text") => h("div", { class: "field" }, h("label", { text: label }),
    h("input", { type, value: obj[key] ?? "", spellcheck: "false", autocapitalize: "off", oninput: (e) => { obj[key] = e.target.value; } }),
    help ? h("div", { class: "help", html: help }) : null);
  const chk = (obj, key, label) => h("label", { class: "check" }, h("input", { type: "checkbox", checked: obj[key] !== false, onchange: (e) => { obj[key] = e.target.checked; } }), label);

  const views = {
    general: () => [
      h("div", { class: "section" }, h("h3", { text: "Raster" }),
        h("div", { class: "row" }, num(s, "columns", "Spalten", 1, 16), num(s, "rows", "Zeilen", 1, 10)),
        h("div", { class: "help", text: "Für das Galaxy Tab S12 Ultra im Querformat passen 8 × 4 oder 9 × 5 Tasten sehr gut. Tasten außerhalb des Rasters bleiben gespeichert." }),
        h("div", { class: "row", style: { marginTop: "12px" } }, num(s, "gap", "Abstand (px)", 0, 40), num(s, "radius", "Eckenradius (px)", 0, 60))),
      h("div", { class: "section" }, h("h3", { text: "Anzeige" }),
        chk(s, "show_tabs", "Seiten-Leiste oben anzeigen"),
        chk(s, "show_labels", "Beschriftungen auf den Tasten anzeigen"),
        chk(s, "rotate_portrait", "Raster im Hochformat drehen (Spalten werden zu Zeilen)"),
        chk(s, "haptics", "Vibration beim Drücken")),
    ],
    pages: () => {
      const rows = draft.pages.map((p, i) => h("div", { class: "page-row" },
        h("input", { type: "text", value: p.name, oninput: (e) => { p.name = e.target.value; } }),
        h("label", { class: "check", title: "In der Seiten-Leiste anzeigen" }, h("input", { type: "checkbox", checked: !p.hidden, onchange: (e) => { if (e.target.checked) delete p.hidden; else p.hidden = true; } }), "Leiste"),
        h("button", { class: "icon-btn", html: icon("up"), disabled: i === 0, onclick: () => { [draft.pages[i - 1], draft.pages[i]] = [draft.pages[i], draft.pages[i - 1]]; show(); } }),
        h("button", { class: "icon-btn", html: icon("down"), disabled: i === draft.pages.length - 1, onclick: () => { [draft.pages[i + 1], draft.pages[i]] = [draft.pages[i], draft.pages[i + 1]]; show(); } }),
        h("button", { class: "icon-btn", html: icon("trash"), disabled: draft.pages.length < 2, onclick: async () => {
          const n = Object.keys(p.buttons || {}).length;
          if (n && !(await confirmDialog(`Seite „${p.name}“ mit ${n} Tasten löschen?`, "Löschen"))) return;
          draft.pages.splice(i, 1); show();
        } })));
      return [h("div", { class: "section" }, h("h3", { text: "Seiten" }),
        h("p", { class: "help", text: "Die erste Seite ist die Startseite. Seiten ohne Häkchen bei „Leiste“ erreichst du über Ordner-Tasten (Aktion „Seite / Ordner öffnen“)." }),
        rows,
        h("button", { class: "btn", html: icon("plus") + "Neue Seite", onclick: () => {
          draft.pages.push({ id: "p-" + uid(), name: "Seite " + (draft.pages.length + 1), buttons: {} }); show();
        } }))];
    },
    obs: () => {
      const o = App.state.obs || {};
      const status = !draft.obs.enabled ? h("span", { class: "pill", text: "deaktiviert" })
        : o.connected ? h("span", { class: "pill ok", text: `verbunden · Szene „${o.current_scene || "–"}“` })
          : h("span", { class: "pill bad", text: o.error || "nicht verbunden" });
      return [
        h("div", { class: "section" }, h("h3", { text: "Verbindung zu OBS Studio" }),
          h("p", { class: "help", html: "In OBS: <b>Werkzeuge → WebSocket-Servereinstellungen</b> → „WebSocket-Server aktivieren“ anhaken. Port und Passwort („Verbindungsinformationen anzeigen“) hier eintragen." }),
          h("div", { style: { margin: "4px 0 14px" } }, status),
          chk(draft.obs, "enabled", "OBS-Anbindung aktivieren"),
          h("div", { class: "row" }, txt(draft.obs, "host", "Adresse", "Läuft OBS auf demselben PC: <code>127.0.0.1</code>"), num(draft.obs, "port", "Port", 1, 65535)),
          txt(draft.obs, "password", "Passwort", null, "password"),
          h("button", { class: "btn", text: "Neu verbinden", onclick: () => rpc("obs_reconnect").then(() => toast("Verbinde mit OBS …")).catch((e) => toast(e.message, "error")) })),
        h("div", { class: "section" }, h("h3", { text: "Automatisch erstellen" }),
          h("p", { class: "help", text: "Erstellt eine Seite „OBS-Szenen“ mit einer Taste für jede Szene und jede Audioquelle aus deinem OBS." }),
          h("button", { class: "btn primary", disabled: !o.connected, html: icon("grid") + "Szenen-Seite erzeugen", onclick: () => { buildObsPage(draft); toast("Seite „OBS-Szenen“ erstellt – jetzt speichern", "ok"); } })),
      ];
    },
    discord: () => [
      h("div", { class: "section" }, h("h3", { text: "Discord-Tasten festlegen" }),
        h("p", { class: "help", html: "Discord lässt sich von außen nur über <b>globale Tastenbelegungen</b> steuern. Discords eingebaute Kürzel wie Strg+Umschalt+M wirken nur, wenn das Discord-Fenster vorne ist. Deshalb einmalig so einrichten:" }),
        h("ol", { class: "steps" },
          h("li", { html: "Unten für jede Funktion eine Taste wählen. Am besten <b>F13–F24</b>: Die gibt es auf normalen Tastaturen nicht, sie stören also nie." }),
          h("li", { html: "Am PC in Discord: <b>Benutzereinstellungen (⚙️) → Tastenbelegung → „Eine Tastenbelegung hinzufügen“</b>." }),
          h("li", { html: "Aktion wählen (<b>Stummschalten umschalten</b> / <b>Ein- und Ausgabe deaktivieren umschalten</b> bzw. <b>Push-to-Talk</b>), dann <b>„Tastenbelegung aufnehmen“</b> klicken." }),
          h("li", { html: "Hier am Tablet bei der passenden Funktion <b>„An PC senden“</b> tippen. Nach 2 Sekunden drückt TabDeck die Taste und Discord übernimmt sie. Dann in Discord <b>„Aufnahme stoppen“</b> klicken." }),
          h("li", { html: "Unten auf <b>Speichern</b> tippen." })),
        hotkeyRow(s.discord, "mute", "🎙️ Stummschalten umschalten"),
        hotkeyRow(s.discord, "deafen", "🎧 Ton aus („taub“) umschalten"),
        hotkeyRow(s.discord, "ptt", "🗣️ Push-to-Talk (wird gehalten, solange du die Taste drückst)")),
      h("div", { class: "section" }, h("h3", { text: "Anzeige-Status" }),
        h("p", { class: "help", text: "Ob Discord stumm ist, kann TabDeck nicht auslesen. Es merkt sich deine Tastendrücke. Stimmt die Anzeige nicht mehr (z. B. weil du in Discord direkt geklickt hast), setze sie hier zurück." }),
        h("button", { class: "btn", text: "Status zurücksetzen (nicht stumm)", onclick: () => rpc("discord_reset").then(() => toast("Zurückgesetzt", "ok")).catch((e) => toast(e.message, "error")) })),
    ],
    spotify: () => spotifySettings(),
    backup: () => [
      h("div", { class: "section" }, h("h3", { text: "Sichern" }),
        h("p", { class: "help", text: "Lädt deine komplette Tastenbelegung als Datei herunter." }),
        h("button", { class: "btn", text: "Konfiguration exportieren", onclick: () => {
          const blob = new Blob([JSON.stringify(App.config, null, 2)], { type: "application/json" });
          const a = h("a", { href: URL.createObjectURL(blob), download: `tabdeck-${new Date().toISOString().slice(0, 10)}.json` });
          document.body.append(a); a.click(); a.remove();
        } })),
      h("div", { class: "section" }, h("h3", { text: "Wiederherstellen" }),
        h("p", { class: "help", text: "Ersetzt die aktuelle Belegung durch eine exportierte Datei." }),
        h("input", { type: "file", accept: "application/json,.json", onchange: async (e) => {
          const file = e.target.files[0];
          if (!file) return;
          try {
            const cfg = JSON.parse(await file.text());
            if (!Array.isArray(cfg.pages)) throw new Error("Keine gültige TabDeck-Datei");
            if (!(await confirmDialog("Aktuelle Belegung durch die Datei ersetzen?", "Ersetzen"))) return;
            delete cfg.server;
            if (await saveConfig(cfg, "Konfiguration wiederhergestellt")) m.close();
          } catch (err) { toast("Import fehlgeschlagen: " + err.message, "error"); }
        } })),
    ],
    info: () => {
      const f = App.features || {};
      const line = (name, feat) => h("div", {}, h("span", { class: "pill " + (feat?.ok ? "ok" : "bad"), text: feat?.ok ? "aktiv" : "aus" }),
        h("span", {}, h("b", { text: name }), feat?.ok ? "" : h("span", { class: "help", text: " – " + (feat?.error || "nicht verfügbar") })));
      return [
        h("div", { class: "section" }, h("h3", { text: "TabDeck " + (App.version || "") }),
          h("div", { class: "feature-list" },
            line("Tastatur & Medientasten", f.keyboard), line("Lautstärke pro Programm", f.audio), line("Läuft gerade / Spotify", f.media),
            line("CPU & RAM", f.stats),
            line("Spotify-App-Lautstärke", { ok: !!App.state.spotify?.connected, error: App.state.spotify?.error || "nicht verbunden (Einstellungen → Spotify)" }),
            line("OBS", { ok: !!App.state.obs?.connected, error: App.state.obs?.error || (draft.obs.enabled ? "nicht verbunden" : "deaktiviert") }))),
        h("div", { class: "section" }, h("h3", { text: "Tipps fürs Tablet" }),
          h("ul", { class: "help", style: { paddingLeft: "18px", margin: 0 } },
            h("li", { text: "Im Browser-Menü „Zum Startbildschirm hinzufügen“ wählen – dann startet TabDeck wie eine App." }),
            h("li", { text: "Vollbild-Taste oben rechts blendet die Android-Leisten aus." }),
            h("li", { text: "Damit der Bildschirm nicht ausgeht: Android-Einstellungen → Anzeige → Bildschirm-Timeout erhöhen (oder Tablet am Ladekabel lassen und „Wach bleiben“ in den Entwickleroptionen aktivieren)." }),
            h("li", { text: "Auf diesem Gerät abmelden: unten „Verbindungscode vergessen“." }))),
        h("button", { class: "btn danger", text: "Verbindungscode vergessen", onclick: () => {
          try { localStorage.removeItem("tabdeck.token"); } catch {}
          location.reload();
        } }),
      ];
    },
  };

  let shownTab = null;
  const cleanup = () => { for (const c of body.children) c._cleanup?.(); };
  const show = () => {
    tabsBar.replaceChildren(...TABS.map(([id, label]) => h("button", { class: tab === id ? "on" : "", text: label, onclick: () => { tab = id; show(); } })));
    const scroll = body.scrollTop;
    cleanup();
    fill(body, views[tab]());
    body.scrollTop = shownTab === tab ? scroll : 0;
    shownTab = tab;
  };
  const onState = (e) => {
    const keys = e.detail || [];
    if ((tab === "obs" && keys.includes("obs")) || (tab === "info" && (keys.includes("obs") || keys.includes("spotify")))) show();
  };
  document.addEventListener("tabdeck:state", onState);

  const m = openModal({
    title: "Einstellungen",
    body: h("div", { style: { display: "flex", flexDirection: "column", minHeight: 0, flex: 1 } }, tabsBar, body),
    footer: [h("div", { class: "spacer" }),
      h("button", { class: "btn ghost", text: "Abbrechen", onclick: () => m.close() }),
      h("button", { class: "btn primary", text: "Speichern", onclick: async () => {
        s.columns = Math.max(1, Math.min(16, Math.round(s.columns)));
        s.rows = Math.max(1, Math.min(10, Math.round(s.rows)));
        draft.obs.port = Number(draft.obs.port) || 4455;
        if (await saveConfig(draft, "Gespeichert")) m.close();
      } })],
    onClose: () => { document.removeEventListener("tabdeck:state", onState); cleanup(); },
  });
  show();
}

function spotifySettings() {
  const box = h("div");
  const st = () => App.state.spotify || {};
  const idInput = h("input", { type: "text", placeholder: "32 Zeichen, z. B. 1a2b3c…", spellcheck: "false", autocapitalize: "off" });
  const copyRow = (text) => h("div", { class: "copy-row" }, h("code", { text }),
    h("button", { class: "btn small", text: "Kopieren", onclick: () => navigator.clipboard?.writeText(text).then(() => toast("Kopiert", "ok")).catch(() => toast("Bitte manuell markieren", "error")) }));
  const render = (info) => {
    const sp = st();
    if (info?.client_id && !idInput.value) idInput.value = info.client_id;
    const status = sp.connected
      ? h("span", { class: "pill ok", text: `verbunden${sp.user ? " als " + sp.user : ""}${sp.premium === false ? " · kein Premium!" : ""}${sp.volume != null ? ` · Lautstärke ${sp.volume}%` : ""}` })
      : h("span", { class: "pill bad", text: sp.configured ? "noch nicht angemeldet" : "nicht eingerichtet" });
    fill(box,
      h("div", { class: "section" }, h("h3", { text: "Lautstärke direkt in der Spotify-App" }),
        h("p", { class: "help", html: "Windows kann nur die Mixer-Lautstärke ändern (das hörst du nur auf dem Kopfhörer, der Regler in Spotify bleibt gleich). Für den <b>echten Spotify-Regler</b> verbindet sich TabDeck mit deinem Spotify-Konto. <b>Spotify verlangt dafür Premium.</b>" }),
        h("div", { style: { margin: "6px 0 14px" } }, status),
        sp.error && sp.connected ? h("p", { class: "help", style: { color: "#ff7b7f" }, text: sp.error }) : null,
        h("ol", { class: "steps" },
          h("li", { html: "Am PC <b>developer.spotify.com/dashboard</b> öffnen, mit deinem Spotify-Konto anmelden und <b>„Create app“</b> wählen." }),
          h("li", { html: "Name z. B. <b>TabDeck</b>, Beschreibung beliebig, bei <b>„Which API/SDKs“</b> den Haken bei <b>Web API</b> setzen." }),
          h("li", { html: "Als <b>Redirect URI</b> genau diese Adresse eintragen und auf „Add“ klicken:" })),
        info ? copyRow(info.redirect_uri) : h("p", { class: "help", text: "lädt …" }),
        h("ol", { class: "steps", start: 4, style: { marginTop: "12px" } },
          h("li", { html: "Speichern, dann in der App unter <b>Settings</b> die <b>Client ID</b> kopieren und hier einfügen:" })),
        h("div", { class: "row" }, idInput,
          h("button", { class: "btn primary", text: "Mit Spotify verbinden", onclick: async () => {
            try {
              const res = await rpc("spotify_setup", { client_id: idInput.value });
              toast(res.opened ? "Am PC hat sich der Browser geöffnet – dort bei Spotify zustimmen" : "Öffne am PC: " + res.login_url, "ok");
            } catch (err) { toast(err.message, "error"); }
          } })),
        h("p", { class: "help", style: { marginTop: "10px" }, html: info ? `Öffnet sich am PC kein Browser, dort diese Adresse aufrufen: <code>${esc(info.login_url)}</code>` : "" }),
        sp.connected ? h("button", { class: "btn danger", style: { marginTop: "8px" }, text: "Spotify trennen", onclick: () => rpc("spotify_disconnect").then(() => toast("Getrennt")).catch((e) => toast(e.message, "error")) }) : null),
      h("div", { class: "section" }, h("h3", { text: "Ohne Verbindung" }),
        h("p", { class: "help", text: "Play/Pause, Weiter, Zurück, Zufall und „Läuft gerade“ funktionieren auch ohne Spotify-Anmeldung und ohne Premium – nur die Lautstärke in der App und „Gefällt mir“ brauchen die Verbindung." })),
    );
  };
  let info = null;
  rpc("spotify_info").then((r) => { info = r; render(info); }).catch(() => render(null));
  const onState = (e) => { if ((e.detail || []).includes("spotify")) render(info); };
  document.addEventListener("tabdeck:state", onState);
  box._cleanup = () => document.removeEventListener("tabdeck:state", onState);
  render(null);
  return [box];
}

function hotkeyRow(obj, key, label) {
  const a = { keys: obj[key] || "" };
  return h("div", { class: "field card" }, h("label", { text: label }),
    hotkeyInput(a, { k: "keys", ph: "z. B. f14" }, () => { obj[key] = a.keys; }, { send: true }));
}

function buildObsPage(cfg) {
  const o = App.state.obs || {};
  let page = cfg.pages.find((p) => p.id === "obs-scenes");
  if (!page) { page = { id: "obs-scenes", name: "OBS-Szenen", buttons: {} }; cfg.pages.push(page); }
  const cols = cfg.settings.columns, total = cols * cfg.settings.rows;
  const b = {};
  let i = 0;
  b[i++] = { label: "Zurück", icon: "⬅️", color: C.dark, actions: [{ type: "back" }] };
  b[i++] = T("Aufnahme", "⏺️", C.obs, [{ type: "obs", op: "record_toggle" }], { active: ACT("🔴", "REC") });
  b[i++] = T("Stream", "📡", C.obs, [{ type: "obs", op: "stream_toggle" }], { active: ACT("🔴", "LIVE") });
  i = cols; // Szenen ab zweiter Zeile
  for (const scene of o.scenes || []) {
    if (i >= total) break;
    b[i++] = T(scene, "🖼️", C.obs, [{ type: "obs", op: "scene", scene }], { active: ACT(null, null, C.green) });
  }
  if (i % cols) i += cols - (i % cols);
  for (const input of o.inputs || []) {
    if (i >= total) break;
    b[i++] = T(input, "🎙️", C.obs, [{ type: "obs", op: "mute_toggle", input }], { active: ACT("🔇", null) });
  }
  page.buttons = Object.fromEntries(Object.entries(b).map(([k, v]) => [String(k), v]));
}

/* ============================================================ Vollbild & Co. */
async function toggleFullscreen() {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen({ navigationUI: "hide" });
  } catch { toast("Vollbild wird von diesem Browser nicht unterstützt", "error"); }
}

let wakeLock = null;
async function keepAwake() {
  if (!("wakeLock" in navigator) || wakeLock) return;
  try {
    wakeLock = await navigator.wakeLock.request("screen");
    wakeLock.addEventListener("release", () => { wakeLock = null; });
  } catch {}
}

/* ==================================================================== Start */
function init() {
  $("#btn-edit").innerHTML = icon("edit");
  $("#btn-settings").innerHTML = icon("settings");
  $("#btn-fullscreen").innerHTML = icon("full");
  $("#btn-edit").onclick = () => App.config && setEditing(!App.editing);
  $("#btn-done").onclick = () => setEditing(false);
  $("#btn-settings").onclick = () => App.config && openSettings();
  $("#btn-fullscreen").onclick = toggleFullscreen;

  setupGrid();
  window.addEventListener("resize", layout);
  document.addEventListener("fullscreenchange", () => setTimeout(layout, 50));
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      keepAwake();
      if (!App.ws && App.token) { App.retry = 0; connect(); }
    }
  });
  document.addEventListener("pointerdown", keepAwake, { once: true });
  // Uhr-Widgets jede Sekunde aktualisieren
  setInterval(() => { if (App.config && document.querySelector("#grid .w-clock")) refreshFaces(); }, 1000);

  if ("serviceWorker" in navigator && window.isSecureContext) navigator.serviceWorker.register("/sw.js").catch(() => {});

  initToken();
  connect();
}

init();
