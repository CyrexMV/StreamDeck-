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
| **Discord** | Mikro stumm, Ton aus („taub“), **Push-to-Talk** (solange du die Taste hältst). Tasten direkt am Tablet festlegen und per „An PC senden“ in Discord einlernen. |
| **Spotify** | Play/Pause, weiter/zurück, Zufallswiedergabe, Wiederholen, **Lautstärke direkt in der Spotify-App**, „Gefällt mir“, **„Läuft gerade“ mit Cover**, **aktueller Songtitel als Lauftext** auf Play/Pause-, Öffnen- und Fader-Kacheln (pro Taste im Editor unter „Songtitel anzeigen“ einstellbar) |
| **Ton** | **Schiebefader** für alles, was Ton abspielt: eigene Seite **„Mixer“** (zeigt automatisch PC, Mikrofon, Spotify, Discord, Browser, Spiele … und OBS-Audioquellen) sowie Fader-Kacheln für jede Seite. Dazu PC-Lautstärke ±/stumm, Lautstärke pro Programm, Windows-Mikrofon stumm. |
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
Discord lässt sich von außen nur über **globale Tastenbelegungen** steuern. Discords eingebaute Kürzel
(`Strg+Umschalt+M` …) wirken nur, solange das Discord-Fenster vorne ist. Deshalb einmalig einrichten,
das geht komplett vom Tablet aus:

1. Tablet: **⚙️ Einstellungen → Discord**. Für jede Funktion eine Taste antippen. Voreingestellt sind
   **F14** (stumm), **F15** (taub) und **F13** (Push-to-Talk). Diese Tasten gibt es auf normalen Tastaturen nicht,
   sie kollidieren also mit nichts.
2. PC: Discord → **Benutzereinstellungen (⚙️) → Tastenbelegung → „Eine Tastenbelegung hinzufügen“**.
3. Aktion **„Stummschalten umschalten“** wählen und auf **„Tastenbelegung aufnehmen“** klicken.
4. Tablet: bei „Stummschalten“ auf **„An PC senden“** tippen. Nach 2 Sekunden drückt TabDeck die Taste
   und Discord übernimmt sie. In Discord „Aufnahme stoppen“.
5. Dasselbe für **„Ein- und Ausgabe deaktivieren umschalten“** (taub) und **Push-to-Talk**. Danach am Tablet **Speichern**.

Da Discord seinen Status nicht verrät, merkt sich TabDeck „stumm/nicht stumm“ selbst. Stimmt die Anzeige nicht mehr
(weil du in Discord direkt geklickt hast), setzt du sie dort mit einem Fingertipp zurück.

### Spotify
**Play/Pause, weiter/zurück, Zufall und „Läuft gerade“** funktionieren ohne Einrichtung. TabDeck nutzt dafür die
Windows-Mediensteuerung und steuert gezielt Spotify, auch wenn nebenbei z. B. ein YouTube-Video läuft.

Für **„Spotify lauter/leiser/stumm“ direkt in der Spotify-App** (der Regler in Spotify bewegt sich mit, nicht nur
der Windows-Mixer) und **„Gefällt mir“** verbindet sich TabDeck mit deinem Spotify-Konto. **Spotify verlangt dafür
Premium.** Einmalig einrichten:

1. Am PC <https://developer.spotify.com/dashboard> öffnen, mit dem Spotify-Konto anmelden und **„Create app“** wählen.
2. Name z. B. *TabDeck*, bei „Which API/SDKs“ den Haken bei **Web API** setzen.
3. Als **Redirect URI** genau `http://127.0.0.1:8765/spotify/callback` eintragen (steht auch zum Kopieren in den
   TabDeck-Einstellungen) und speichern.
4. Die **Client ID** der App kopieren. Tablet: **⚙️ Einstellungen → Spotify** → einfügen → **„Mit Spotify verbinden“**.
5. Am PC öffnet sich der Browser: bei Spotify zustimmen. Fertig.

### Andere Programme
Fast jedes Programm lässt sich über **Tastenkombinationen** steuern, zum Beispiel Teams, Zoom, Spiele, Photoshop oder
Premiere. Im Editor wählst du die Kombination per Fingertipp (Strg/Umschalt/Alt/Win plus Taste). Mit angeschlossener
Tastatur (Book Cover Keyboard oder am PC-Browser) geht es auch über den Knopf **„Tastatur“**.

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
3. **Speichern**. Mit 🗑 löschst du die Taste, mit ⧉ duplizierst du sie.

**Kacheln verschieben:** Im Bearbeitungsmodus eine Kachel **festhalten und ziehen**:
- auf ein freies Feld: Die Kachel wandert dorthin.
- auf eine andere Kachel: Beide tauschen den Platz.
- auf einen **Seiten-Reiter** oben: Loslassen legt sie ins erste freie Feld dieser Seite. Kurz darüber **halten**
  öffnet die Seite, dann kannst du sie dort genau platzieren.

**Stumm-Anzeige wie in Discord:** Mikrofon-, Kopfhörer- und Lautsprecher-Tasten zeigen ein weißes Symbol. Ist stumm
geschaltet, wird es **rot und durchgestrichen** (bei Discord „taub“ auch das Mikrofon, wie in Discord selbst). Im Editor
unter **„Symbol-Art“** kannst du das für jede Taste wählen.

**Schiebefader:** Auf der Seite **„Mixer“** erscheint für jedes Programm, das gerade Ton abspielt, automatisch ein
Fader. Den Regler mit dem Finger hoch- oder runterschieben. Antippen allein verändert nichts, damit es nie plötzlich laut
wird. 🔊/🔇 unten schaltet stumm. Einzelne Fader legst du auf jede Seite: im Editor bei **„Art der Kachel“** →
*Schiebefader* (oder Vorlage „Schiebefader“), dann wählen, was er steuert. Bei **„Größe“** z. B. *1 breit × 3 hoch*
für einen langen Fader. Dafür müssen die Felder darunter frei sein. Eine weitere Mixer-Seite gibt es unter
⚙️ → Seiten → „Mixer-Seite hinzufügen“.

**OBS-Mixer:** Der Reiter **„OBS-Mixer“** zeigt für jede Quelle, die in deinem **OBS-Audio-Mixer gerade aktiv** ist,
einen Fader mit Pegelanzeige, so wie der Mixer in OBS selbst. Wechselst du die Szene, passen sich die Fader
automatisch an. Fehlt die Seite, gibt es sie unter ⚙️ → OBS → „OBS-Mixer-Seite hinzufügen“. Auch beim Hinzufügen
einzelner OBS-Fader (Kachel oder „Mixer einrichten“) werden nur die aktiven OBS-Quellen angeboten.

**Mixer einrichten:** Auf der Mixer-Seite ✏️ antippen und **„🎚️ Mixer einrichten“** wählen. Bei **„Automatisch“**
erscheint alles, was Ton abspielt. Bei **„Eigene Auswahl“** bestimmst du selbst, welche Regler es gibt: Quellen
hinzufügen (PC, Mikrofon, Spotify-App, jedes Programm, OBS-Quellen oder ein Programm per Name, z. B. ein Spiel),
entfernen, umbenennen und sortieren. Dort stellst du auch die Breite der Regler ein. Passen nicht alle Regler auf den
Bildschirm, wird der Mixer in **Seiten** aufgeteilt: waagerecht wischen (auch direkt auf einem Regler) oder unten
Pfeile/Punkte antippen. Senkrecht ziehen verstellt die Lautstärke.

Seiten, Rastergröße, Abstände und mehr findest du unter **⚙️ Einstellungen**. Dort gibt es unter *Sicherung* auch den
**Export** und **Import** deiner kompletten Belegung.

> Tipp: Du kannst TabDeck auch **am PC im Browser** öffnen (<http://localhost:8765>) und dort bequem mit Maus und
> Tastatur einrichten. Änderungen erscheinen sofort auf dem Tablet.

---

## ⚙️ Für Fortgeschrittene

**Autostart ohne Fenster**: Führe `start.bat` einmal aus. Danach `Win+R` → `shell:startup` öffnen und dort eine
Verknüpfung zu **`start-hidden.vbs`** ablegen. Das Protokoll steht dann in `%APPDATA%\TabDeck\tabdeck.log`.

**Dateien**
Alles liegt unter Windows in **`%APPDATA%\TabDeck`** (im Explorer in die Adresszeile eintippen). Dort bleibt es auch bei
Updates und neuen Programmordnern erhalten:
- `config.json`: deine komplette Belegung (Seiten, Layouts, Tasten, Einstellungen, Port, Verbindungscode,
  Spotify-Anmeldung). Nicht weitergeben!
- `icons\`: hochgeladene Bilder, `appicons\`: ausgelesene Programm-Logos
- Neuer Verbindungscode: in `config.json` den Wert `"token"` leeren und TabDeck neu starten.

**Update auf eine neue Version:** Neue Version herunterladen und entpacken, egal ob in den alten Ordner oder einen neuen
daneben, dann `start.bat` starten. Beim ersten Start übernimmt TabDeck deine bisherige Belegung automatisch (auch aus
einem älteren TabDeck-Ordner im selben Verzeichnis, z. B. *Downloads*). Der Pfad wird im TabDeck-Fenster angezeigt.

**Alte Belegung von Hand übernehmen:** TabDeck schließen, den Ordner **`data`** der alten Version in den neuen
Programmordner ziehen (neben `start.bat`) und `start.bat` starten. TabDeck übernimmt ihn, sichert die bisherige
Belegung als „config vorher …json“ und benennt den Ordner danach in „data (übernommen …)“ um.

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
| Discord reagiert nicht | In Discord unter *Tastenbelegung* muss eine **globale** Belegung mit genau der Taste aus den TabDeck-Einstellungen stehen (siehe oben). Läuft Discord als Administrator, muss auch TabDeck als Administrator laufen. |
| Spotify-Lautstärke: „Premium nötig“ | Spotify erlaubt die Steuerung der App-Lautstärke nur mit Premium. Ohne Premium bleibt nur die Windows-Mixer-Lautstärke (Aktion „Lautstärke → Einzelnes Programm“). |
| Spotify: „Kein aktives Gerät“ | In Spotify einmal auf Play drücken, dann klappt es. |
| CPU/RAM zeigt „–“ | Unter ⚙️ → Info nachsehen, ob „CPU & RAM“ aktiv ist. TabDeck neu starten (`start.bat` installiert fehlende Pakete nach). |
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
    keyboard.py         Tastenkombinationen und Medientasten (Windows SendInput)
    audio.py            Lautstärke pro Programm und Mikrofon (pycaw)
    media.py            Spotify und „Läuft gerade“ (Windows-Medien-API)
    spotify_api.py      Spotify-App-Lautstärke und „Gefällt mir“ (Spotify Web API)
    obs.py              OBS-WebSocket-v5-Client mit Live-Status
    system.py           Öffnen, Befehle, Energie, CPU und RAM
web/                    Tablet-Oberfläche (HTML/CSS/JS, ohne externe Abhängigkeiten)
start.bat               Start unter Windows (installiert alles automatisch)
start-hidden.vbs        Unsichtbarer Start für den Autostart
```
