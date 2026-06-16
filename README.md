# VBus FriWa Gateway

Gateway-Dienst für eine RESOL/PAW Frischwasserstation am VBus.

Der Gateway läuft auf dem Rechner, an dem das USB/VBus-Interface steckt, z. B. auf einem Raspberry Pi. EDOMI greift danach per HTTP auf diesen Gateway zu. EDOMI selbst spricht nicht direkt mit dem seriellen VBus-Port.

## Ziel

- RESOL/PAW FriWa über VBus lesen und schreiben.
- Live-Werte und Parameterwerte per HTTP/WebSocket bereitstellen.
- Schreibwerte nach jedem Write direkt aus der FriWa zurücklesen.
- EDOMI-Ausgänge nur bei Wertwechsel setzen.
- Mehrere EDOMI-Bausteine oder Clients dürfen denselben Gateway nutzen.
- RESOL-RSC-Dateien nicht mitliefern, sondern lokal vom Nutzer aus dem offiziellen RESOL-Download extrahieren lassen.

## Was im Git-Repo enthalten ist

Enthalten:

- Gateway-Quellcode `src/`
- CLI-Testtool `vbus-test`
- HTTP/WebSocket API
- Basic Auth, optional Bearer Token
- optional TLS/HTTPS
- systemd Unit
- Installationsscript
- Profilgenerator
- EDOMI-LBS-Generator für Full und Light
- Extract-Script für RESOL RSC
- Dokumentation und MIT-Lizenz für den Projektcode

Nicht enthalten:

- RESOL-RSC ZIP/EXE
- RESOL XML-Dateien
- generiertes Profil `profiles/friwa-0x7611.json`
- generierte IO-Maps
- generierte EDOMI-LBS-Dateien
- lokale Config mit echten Zugangsdaten
- `node_modules/`
- `dist/`

Grund: Das Profil und die EDOMI-Mappings enthalten abgeleitete Daten aus RESOL-RSC-XMLs. Da deren Weitergabebedingungen hier nicht geklärt sind, soll jeder Nutzer RSC selbst von RESOL laden und daraus lokal das Profil erzeugen.

## Architektur

```text
FriWa / RESOL Regler
        |
        | VBus
        |
USB/VBus-Interface
        |
        | /dev/ttyACM0
        |
Raspberry Pi / Gateway-Node
        |
        | vbus-friwa-gateway systemd service
        | HTTP :8787
        |
EDOMI
        |
        | LBS 19100833 Light oder 19100832 Full
        |
EDOMI Logik / KNX / Visualisierung
```

Wichtig:

- Nur der Gateway öffnet den seriellen Port.
- Mehrere EDOMI-Bausteine dürfen gleichzeitig die HTTP API nutzen.
- VBus-Reads und Writes werden im Gateway intern per Lock nacheinander ausgeführt.
- `vbus-test` nutzt standardmäßig ebenfalls die HTTP API des laufenden Gateway-Service.
- Nur `vbus-test --direct` greift direkt auf Serial/VBus zu und sollte nicht parallel zum systemd-Service laufen.

## Voraussetzungen

Auf dem Gateway-Node:

- Linux, z. B. Raspberry Pi OS
- Node.js >= 20
- npm
- 7z für die RESOL-RSC-Extraktion
- USB/VBus-Interface, typischerweise `/dev/ttyACM0`
- User des Dienstes braucht Zugriff auf die serielle Schnittstelle, normalerweise Gruppe `dialout`

Debian/Raspberry Pi OS:

```bash
sudo apt-get update
sudo apt-get install -y git nodejs npm 7zip
```

Falls `7zip` auf der Distribution nicht existiert:

```bash
sudo apt-get install -y p7zip-full
```

## Installation Von Git Bis Gateway-Service

### 1. Repo klonen

```bash
git clone https://github.com/x3muha/vbus-friwa-gateway.git
cd vbus-friwa-gateway
```

### 2. RESOL RSC selbst herunterladen

RESOL-Produktseite:

```text
https://www.resol.de/de/produktdetail/170
```

Auf der Seite:

1. Tab `Software` öffnen.
2. `RSC Version 2.5 b35` herunterladen.
3. Datei lokal speichern, z. B. als:

```text
/tmp/RSC.zip
```

Beim Erstellen dieser Doku war der direkte Link:

```text
https://www.resol.de/software/RSC/RSC.zip
```

Solange dieser direkte Link funktioniert, kann der Download auch per `wget` erfolgen:

```bash
wget -O /tmp/RSC.zip https://www.resol.de/software/RSC/RSC.zip
```

Der direkte Link kann sich bei RESOL ändern. Im Zweifel immer die Produktseite verwenden.

### 3. Benötigte XML-Dateien extrahieren

```bash
npm run extract:resol -- --archive /tmp/RSC.zip
```

Das Script extrahiert nur:

```text
vendor/resol-rsc/MenuFriwa_1.0.xml
vendor/resol-rsc/VBusSpecificationResol.xml
```

Diese Dateien werden nicht committed.

Wenn du statt `RSC.zip` direkt den enthaltenen Installer hast, geht auch:

```bash
npm run extract:resol -- --archive /tmp/ServiceCenterFullSetup.exe
```

### 4. Abhängigkeiten installieren

```bash
npm install
```

### 5. FriWa-Profil erzeugen

```bash
npm run generate:profile
```

Erzeugt lokal:

```text
profiles/friwa-0x7611.json
```

Dieses Profil ist für die RESOL/PAW FriWa mit Adresse `0x7611` gebaut.

Aus dem RSC-Mapping werden dabei u. a. erzeugt:

- 20 Live-Werte aus `00_0010_7611_10_0100`
- Parameter aus `MenuFriwa_1.0.xml`
- EDOMI-Varianten `edomi.full` und `edomi.light`
- sinnvolle Light-Namens-Overrides, z. B. `Warmwasser Soll`

### 6. EDOMI-Bausteine erzeugen

```bash
npm run generate:edomi:full
npm run generate:edomi:light
```

Die Standard-Scripts erzeugen die LBS-Dateien lokal unter:

```text
generated/edomi/LBS/19100832/19100832_lbs.php
generated/edomi/LBS/19100833/19100833_lbs.php
```

`generated/` ist per `.gitignore` ausgeschlossen.

Wenn dein EDOMI-LBS-Verzeichnis anders liegt, den Generator direkt mit eigenem Zielpfad starten. Beispiel:

```bash
python3 scripts/generate_edomi_lbs.py --profile profiles/friwa-0x7611.json --variant light --out /pfad/zu/edomi/LBS/19100833/19100833_lbs.php
```

Empfehlung:

- Für normalen Betrieb zuerst `19100833` Light verwenden.
- `19100832` Full nur verwenden, wenn wirklich alle Parameter sichtbar sein sollen.

Light-Mapping:

- A1..A20: Live-Werte
- E16/A16: `0x0130 Warmwasser Soll`, Readback über live `Warmwassersolltemperatur`
- E21/A21..E44/A44: praxisnahe Schreibwerte
- A45: frei
- A46..A52: Statusausgänge

### 7. Projekt bauen

```bash
npm run build
npm run check
```

### 8. Gateway installieren

```bash
sudo ./scripts/install.sh
```

Das Script:

- kopiert das Projekt nach `/opt/vbus-friwa-gateway`
- legt User `vbus-friwa` an, falls er fehlt
- installiert Node-Abhängigkeiten
- baut `dist/`
- legt `/etc/vbus-friwa-gateway/config.json` an, falls nicht vorhanden
- installiert `vbus-friwa-gateway.service`
- startet den Dienst noch nicht automatisch

### 9. Config prüfen

```bash
sudo nano /etc/vbus-friwa-gateway/config.json
```

Wichtig:

```json
{
  "serial": {
    "path": "/dev/ttyACM0",
    "baudRate": 9600
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8787,
    "refreshIntervalMs": 60000,
    "parameterReadMode": "all"
  },
  "auth": {
    "username": "admin",
    "password": "admin",
    "token": ""
  },
  "profile": {
    "file": "./profiles/friwa-0x7611.json"
  },
  "writes": {
    "enabled": true,
    "deny": []
  }
}
```

Felder:

- `serial.path`: VBus-USB-Port
- `server.port`: HTTP-Port für EDOMI, Standard `8787`
- `server.refreshIntervalMs`: kompletter Refresh, Standard `60000`
- `server.parameterReadMode`: `all`, `writable` oder `none`
- `auth.username/password`: Basic Auth, Standard `admin/admin`
- `auth.token`: optionaler Bearer Token
- `tls.enabled`: HTTPS/WSS aktivieren
- `writes.enabled`: globaler Schreibschalter
- `writes.deny`: einzelne Keys oder Hex-Indizes sperren

### 10. Service starten

```bash
sudo systemctl enable --now vbus-friwa-gateway.service
sudo systemctl status vbus-friwa-gateway.service
```

Logs:

```bash
journalctl -u vbus-friwa-gateway.service -f
```

## Funktion Testen

### Health

```bash
curl -u admin:admin http://127.0.0.1:8787/health
```

Erwartung:

```json
{"ok":true,"ts":"..."}
```

### Einzelwert lesen

```bash
vbus-test --config /etc/vbus-friwa-gateway/config.json --read 0x0130
```

Beispiel:

```text
0x0130  param.0x0130.warmwassersoll  raw=600  value=60
```

### Alle lesbaren Werte lesen

```bash
vbus-test --config /etc/vbus-friwa-gateway/config.json --read --all
```

### Wert schreiben

Beispiel Warmwasser Soll auf `60 °C`:

```bash
vbus-test --config /etc/vbus-friwa-gateway/config.json --write 0x0130 60
```

Der Gateway rechnet automatisch:

```text
60 °C -> raw 600
```

Nach dem Write wird `0x0130` direkt erneut gelesen. Der angezeigte Wert ist also der echte Readback.

Direkter Serial-Test ohne Gateway-Service:

```bash
vbus-test --config /etc/vbus-friwa-gateway/config.json --direct --read 0x0130
```

Nur nutzen, wenn der systemd-Service gestoppt ist.

## EDOMI Einrichten

### 1. Light-LBS importieren

Empfohlene Datei:

```text
generated/edomi/LBS/19100833/19100833_lbs.php
```

Baustein:

```text
19100833 VBus FriWa Gateway Light
```

### 2. EDOMI-Eingänge konfigurieren

Wichtige Eingänge:

| Eingang | Bedeutung | Beispiel |
|---:|---|---|
| E1 | Gateway Host/IP | `10.0.1.221` |
| E2 | Gateway Port | `8787` |
| E3 | HTTPS 0/1 | `0` |
| E4 | User | `admin` |
| E5 | Passwort | `admin` |
| E6 | Bearer Token | leer |
| E7 | Aktiv 1/0 | `1` |
| E8 | Intervall Sekunden | `60` |
| E9 | Sofort lesen | Trigger |
| E10 | Debug RAW 1/0 | `0` |
| E11 | SSL prüfen 1/0 | `0` |
| E12 | Timeout Sekunden | `8` |

### 3. Wichtige Light-Eingänge

| Eingang | Ausgang | Index | Name |
|---:|---:|---|---|
| E16 | A16 | `0x0130` | Warmwasser Soll |
| E23 | A23 | `0x0082` | Zirkulation Laufzeit |
| E32 | A32 | `0x0100` | Notbetrieb aktiv |
| E33 | A33 | `0x0101` | Notbetrieb Prozent |
| E43 | A43 | `0x0152` | Maximaler Durchfluss |
| E44 | A44 | `0x0163` | Zapfung Mindestdurchfluss |

Die vollständige Zuordnung steht in der Hilfe des Bausteins und wird lokal als IO-Map erzeugt, wenn die Mappingdaten generiert werden.

### 4. Write-/Readback-Verhalten

Wenn EDOMI z. B. schreibt:

```text
E16 = 60
```

dann passiert:

1. LBS sendet `POST /api/write`.
2. Gateway schreibt `0x0130`.
3. Gateway liest `0x0130` erneut.
4. LBS setzt `A16` mit dem echten Readback.

Wenn der Regler einen Wert begrenzt oder ablehnt, zeigt EDOMI den Readback-Wert und nicht blind den Wunschwert.

## HTTP API

Auth:

- Basic Auth: `admin:admin`
- oder `Authorization: Bearer <token>`, wenn `auth.token` gesetzt ist

Endpoints:

```text
GET  /health
GET  /api/profile
GET  /api/state
POST /api/read
POST /api/write
WS   /ws
```

Beispiele:

```bash
curl -u admin:admin http://127.0.0.1:8787/api/state

curl -u admin:admin -X POST http://127.0.0.1:8787/api/read \
  -H 'content-type: application/json' \
  -d '{"index":"0x0130"}'

curl -u admin:admin -X POST http://127.0.0.1:8787/api/write \
  -H 'content-type: application/json' \
  -d '{"index":"0x0130","value":60}'
```

Write-Antwort:

```json
{
  "ok": true,
  "key": "param.0x0130.warmwassersoll",
  "index": "0x0130",
  "requestedRaw": 600,
  "before": 450,
  "after": 600,
  "value": {
    "key": "param.0x0130.warmwassersoll",
    "raw": 600,
    "value": 60,
    "text": "60"
  }
}
```

## WebSocket API

Pfad:

```text
ws://host:8787/ws
wss://host:8787/ws
```

Auth:

- Basic Auth Header, falls Client das kann
- oder Query-Token: `/ws?token=<token>`

Events:

- `hello`
- `snapshot`
- `change`
- `writeResult`
- `error`

Der Service sendet:

- `snapshot` beim WebSocket-Verbindungsaufbau
- `change` nur bei Änderung
- erzwungenes `change`/`writeResult` nach einem Write-Readback

## Sicherheit

Default ist absichtlich einfach:

```text
admin/admin
HTTP
TLS aus
```

Für private lokale Tests ist das praktisch.

Für produktiven Betrieb:

- Passwort ändern
- optional Bearer Token setzen
- TLS aktivieren, wenn der Gateway nicht nur im vertrauenswürdigen LAN erreichbar ist
- keine TLS-Private-Keys committen
- `writes.deny` für Werte nutzen, die in einer Installation nicht schreibbar sein sollen

## Lizenz Und RESOL-Daten

Projektcode:

- MIT License, siehe `LICENSE`

Abhängigkeiten:

- `resol-vbus-core`: MIT, https://codeberg.org/DanielWippermann/resol-vbus-core
- `serialport`: MIT, https://github.com/serialport/node-serialport
- `ws`: MIT, https://github.com/websockets/ws
- `typescript`: Apache-2.0, https://github.com/microsoft/TypeScript

Die Abhängigkeiten werden nicht als Source-Code in dieses Repo kopiert. Sie werden über `package.json` und `package-lock.json` per npm installiert.

RESOL-Daten:

- RESOL RSC wird nicht mitgeliefert.
- Nutzer laden RSC selbst von RESOL.
- Das lokale Profil wird aus den eigenen RESOL-Dateien erzeugt.
- Öffentliche Repos sollten keine RESOL-XMLs, generierten Profile, IO-Maps oder generierten LBS-Dateien enthalten, solange die Weitergaberechte nicht geklärt sind.

Details:

```text
docs/RESOL_RSC_PROFILE.md
docs/LICENSES.md
docs/GIT_RELEASE_CHECKLIST.md
```

## Entwicklerbefehle

```bash
npm install
npm run extract:resol -- --archive /tmp/RSC.zip
npm run generate:profile
npm run generate:edomi:full
npm run generate:edomi:light
npm run build
npm run check
```

Keine destruktiven VBus-Writes ohne klare Absicht. Für Tests zuerst `--read` nutzen.
