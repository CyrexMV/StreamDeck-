# 🎛️ TabDeck – dein Galaxy Tab als Stream Deck

TabDeck macht dein **Samsung Galaxy Tab S12 Ultra** (oder jedes andere Tablet bzw. Smartphone) zu einem
frei belegbaren Stream Deck für deinen **Windows-PC**. Steuere Discord, Spotify, OBS, die Lautstärke,
Programme, Tastenkombinationen und vieles mehr per Fingertipp.

- **Auf dem PC** läuft ein kleiner Server (Python), der die Aktionen ausführt.
- **Auf dem Tablet** öffnest du einfach den Browser. Eine App aus dem Play Store brauchst du nicht.
- Die Tasten zeigen **live**, was gerade los ist: Aufnahme läuft (pulsiert rot), aktive OBS-Szene,
  Mikro stumm, Spotify spielt, Titel mit Cover, CPU- und RAM-Auslastung, Uhrzeit …

---

## ✨ Funktionen

| Bereich | Was geht |
|---|---|
| **OBS Studio** | Szene wechseln, Aufnahme/Stream starten und stoppen, Aufnahme pausieren, Audioquellen stumm schalten, Quellen ein- und ausblenden, virtuelle Kamera, Replay-Puffer und Replay speichern, Studio-Modus und Übergang, Screenshot. **Live-Status** auf den Tasten, dazu eine automatisch erzeugte Seite mit allen Szenen. |
| **Discord** | Mikro stumm, Ton aus („taub“), **Push-to-Talk** (solange du die Taste hältst), Discord-Lautstärke |
| **Spotify** | Play/Pause, weiter/zurück, Zufallswiedergabe, Wiederholen, Spotify-Lautstärke, **„Läuft gerade“ mit Cover** |
| **Ton** | PC-Lautstärke ±/stumm/fester Wert, **Lautstärke pro Programm**, Windows-Mikrofon stumm |
| **Allgemein** | Beliebige Tastenkombinationen (auch gehalten), Text schreiben, Programme, Dateien und Websites öffnen, Befehle ausführen, PC sperren, Monitor aus, Energiesparen, Neustart, Herunterfahren (mit Sicherheitsabfrage) |
| **Mehrfach-Aktionen** | Eine Taste kann mehrere Aktionen nacheinander ausführen, mit Wartezeit dazwischen. |
| **Ordner & Seiten** | Beliebig viele Seiten, Ordner-Tasten, Zurück-Taste |
| **Anzeigen** | Uhr, CPU, RAM, Lautstärke, „Läuft gerade“ |
| **Gestaltung** | Emoji oder eigenes Bild, Farbe, eigenes Aussehen im aktiven Zustand, Raster frei einstellbar (Standard 8 × 4, im Hochformat automatisch gedreht) |
| **Bedienung** | Alles direkt auf dem Tablet einrichten: Bleistift antippen, dann Taste antippen. Vorlagen, Verschieben, Duplizieren, Aktion testen. |

---

## 🚀 Einrichtung (ca. 5 Minuten)

### 1. Python installieren (einmalig)
Lade **Python 3.10 oder neuer** von <https://www.python.org/downloads/> herunter.
Setze bei der Installation unbedingt den Haken bei **„Add python.exe to PATH“**.

### 2. TabDeck starten
Lade dieses Projekt herunter (grüner Knopf **Code → Download ZIP**), entpacke es und starte per Doppelklick
**`start.bat`**.

Beim ersten Start wird alles automatisch installiert (dauert ca. eine Minute). Danach öffnet sich am PC eine Seite
mit einem **QR-Code**.

> Fragt die **Windows-Firewall** nach, ob Python im Netzwerk kommunizieren darf: **„Zulassen“** für
> *private Netzwerke* wählen. Sonst kann das Tablet den PC nicht erreichen.

### 3. Tablet verbinden
Tablet und PC müssen im **selben WLAN** sein (der PC darf auch per LAN-Kabel am selben Router hängen).

1. Scanne den QR-Code mit der Kamera des Galaxy Tab und öffne den Link. **Fertig.**
2. Alternativ gibst du im Browser des Tablets die Adresse aus dem TabDeck-Fenster ein (z. B. `http://192.168.178.20:8765`)
   und danach den **Verbindungscode** (z. B. `K7P2-QX9M`).

Den QR-Code findest du jederzeit am PC unter <http://localhost:8765/connect>.

### 4. Wie eine App benutzen
- In Chrome oder Samsung Internet im Menü **„Zum Startbildschirm hinzufügen“** wählen.
- Oben rechts auf **⛶ (Vollbild)** tippen. Damit verschwinden die Android-Leisten.
- Damit der Bildschirm anbleibt: *Einstellungen → Anzeige → Bildschirm-Timeout* hochsetzen. Liegt das Tablet dauerhaft
  am Ladekabel, kannst du stattdessen in den Entwickleroptionen **„Wach bleiben“** aktivieren.

---

## 🔌 Programme anbinden

### OBS Studio
1. In OBS: **Werkzeuge → WebSocket-Servereinstellungen**
2. Haken bei **„WebSocket-Server aktivieren“** setzen.
3. Auf **„Verbindungsinformationen anzeigen“** klicken und das Passwort kopieren.
4. Auf dem Tablet: **⚙️ Einstellungen → OBS** → Passwort eintragen → Speichern.

Danach steht dort „verbunden“. Mit **„Szenen-Seite erzeugen“** bekommst du automatisch eine Taste für jede Szene und jede
Audioquelle. Die mitgelieferten Beispieltasten nutzen die Standardnamen eines deutschen OBS („Szene“,
„Mikrofon/AUX“, „Desktop-Audio“). Benenne sie bei Bedarf um.

### Discord
Discord lässt sich von fremden Programmen nicht direkt steuern. TabDeck drückt deshalb die **Tastenkombinationen**, die in
Discord hinterlegt sind:

- Discord-Standard: **Stummschalten = `Strg+Umschalt+M`**, **Ton aus = `Strg+Umschalt+D`**. Beides funktioniert sofort.
- **Push-to-Talk**: In Discord unter *Einstellungen → Sprache & Video* den Eingabemodus „Push-to-Talk“ wählen.
  Unter *Tastenbelegung* „Tastenbelegung aufnehmen“ anklicken und dann die **PTT-Taste auf dem Tablet** drücken.
  TabDeck sendet dafür `F13`, eine Taste, die auf normalen Tastaturen nicht existiert und deshalb nie kollidiert.
- Eigene Kombinationen änderst du unter **⚙️ Einstellungen → Discord**.

Da Discord seinen Status nicht verrät, merkt sich TabDeck „stumm/nicht stumm“ selbst. Stimmt die Anzeige nicht mehr
(weil du in Discord direkt geklickt hast), setzt du sie dort mit einem Fingertipp zurück.

### Spotify
Hier musst du nichts einrichten. TabDeck nutzt die Windows-Mediensteuerung und steuert gezielt **Spotify**, auch wenn
nebenbei z. B. ein YouTube-Video läuft. Die Taste „Läuft gerade“ zeigt Titel, Interpret und Cover.

### Andere Programme
Fast jedes Programm lässt sich über **Tastenkombinationen** steuern, zum Beispiel Teams, Zoom, Spiele, Photoshop oder
Premiere. Im Editor gibt es dafür den Knopf **„Aufnehmen“**: Ist am Tablet (Book Cover Keyboard) oder am PC-Browser eine
Tastatur angeschlossen, drückst du einfach die gewünschte Kombination.

Weitere nützliche Ziele für „Öffnen“: `spotify:`, `discord://`, `steam://rungameid/730`, `ms-settings:sound`,
`explorer.exe`, `C:\Pfad\zum\Programm.exe` oder `https://…`.

---

## ✏️ Tasten bearbeiten

1. Oben auf **✏️** tippen. Die Tasten wackeln, leere Felder zeigen ein **+**.
2. Eine Taste oder ein leeres Feld antippen. Rechts öffnet sich der Editor:
   - **Vorlage wählen**: fertige Tasten für Discord, Spotify, OBS, Windows und Anzeigen
   - **Aussehen**: Beschriftung, Emoji oder eigenes Bild, Farbe, Anzeige (Uhr, CPU …)
   - **Aktionen**: beliebig viele, mit ▶ einzeln testbar
   - **Aktiver Zustand**: anderes Symbol, andere Farbe oder Beschriftung, wenn die Taste „an“ ist
     (z. B. 🎙️ → 🔇 „Stumm“ in Rot)
3. **Speichern**. Mit 🗑 löschst du die Taste, mit ✥ verschiebst du sie (danach Ziel-Feld antippen), mit ⧉ duplizierst du sie.

Seiten, Rastergröße, Abstände und mehr findest du unter **⚙️ Einstellungen**. Dort gibt es unter *Sicherung* auch den
**Export** und **Import** deiner kompletten Belegung.

> Tipp: Du kannst TabDeck auch **am PC im Browser** öffnen (<http://localhost:8765>) und dort bequem mit Maus und
> Tastatur einrichten. Änderungen erscheinen sofort auf dem Tablet.

---

## ⚙️ Für Fortgeschrittene

**Autostart ohne Fenster**: Führe `start.bat` einmal aus. Danach `Win+R` → `shell:startup` öffnen und dort eine
Verknüpfung zu **`start-hidden.vbs`** ablegen. Das Protokoll steht dann in `data\tabdeck.log`.

**Dateien**
- `data/config.json`: deine komplette Belegung, inklusive Port und Verbindungscode
- `data/icons/`: hochgeladene Bilder
- Neuer Verbindungscode: in `data/config.json` den Wert `"token"` leeren und TabDeck neu starten.

**Startoptionen**: `python -m server --port 9000`, `--host 127.0.0.1`, `--debug`, `--open`

**Echter App-Modus (optional)**: Android-Browser erlauben Funktionen wie „Bildschirm anlassen“ und echte App-Installation
nur bei HTTPS oder `localhost`. Zwei Wege dahin:
- Tablet per USB anschließen und am PC `adb reverse tcp:8765 tcp:8765` ausführen. Dann auf dem Tablet
  `http://localhost:8765` öffnen.
- Oder in Chrome `chrome://flags/#unsafely-treat-insecure-origin-as-secure` öffnen und die TabDeck-Adresse
  (z. B. `http://192.168.178.20:8765`) eintragen.

**Sicherheit**: Nur Geräte mit dem Verbindungscode können Tasten auslösen. Nach 10 falschen Versuchen wird die Adresse
für 10 Minuten gesperrt. Die Verbindung im WLAN ist nicht verschlüsselt. Nutze TabDeck daher nur in deinem
Heimnetz und nicht in öffentlichen WLANs.

---

## ❓ Probleme?

| Problem | Lösung |
|---|---|
| Tablet findet den PC nicht | Gleiches WLAN? Windows-Firewall: Python für *private Netzwerke* zulassen. Bei mehreren Adressen im TabDeck-Fenster die andere probieren. Das Netzwerkprofil in Windows sollte „Privat“ sein. |
| „Der Verbindungscode stimmt nicht“ | Den Code aus dem TabDeck-Fenster am PC verwenden. Groß- und Kleinschreibung sowie der Bindestrich sind egal. |
| OBS „nicht erreichbar“ | Läuft OBS? WebSocket-Server aktiviert? Port 4455? |
| OBS „Passwort falsch“ | Passwort in OBS unter *Verbindungsinformationen anzeigen* kopieren und neu eintragen. |
| Discord reagiert nicht | Kombination in Discord unter *Tastenbelegung* prüfen. Läuft Discord als Administrator, muss auch TabDeck als Administrator laufen. |
| Tasten wirken in einem Spiel nicht | Spiele mit Anti-Cheat ignorieren simulierte Tasten oft. Läuft das Spiel als Administrator, `start.bat` ebenfalls als Administrator starten. |
| „Programm spielt gerade keinen Ton ab“ | Die Lautstärke pro Programm geht erst, wenn das Programm einmal Ton ausgegeben hat. |

---

## 🧱 Aufbau

```
server/                 PC-Server (Python, aiohttp)
  app.py                Webserver, WebSocket, Live-Status
  actions.py            Führt die Aktionen einer Taste aus
  config.py             Konfiguration laden und speichern
  default_config.json   Startbelegung (Start, OBS, Discord, Spotify, System)
  integrations/
    keyboard.py         Tastenkombinationen und Medientasten (pynput)
    audio.py            Lautstärke pro Programm und Mikrofon (pycaw)
    media.py            Spotify und „Läuft gerade“ (Windows-Medien-API)
    obs.py              OBS-WebSocket-v5-Client mit Live-Status
    system.py           Öffnen, Befehle, Energie, CPU und RAM
web/                    Tablet-Oberfläche (HTML/CSS/JS, ohne externe Abhängigkeiten)
start.bat               Start unter Windows (installiert alles automatisch)
start-hidden.vbs        Unsichtbarer Start für den Autostart
```
