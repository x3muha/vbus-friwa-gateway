# VBus FriWa Gateway

Gateway-Dienst fuer eine RESOL/PAW Frischwasserstation am VBus.

Ziel:
- VBus ueber USB/Serial lesen und schreiben.
- Live- und Parameterwerte per HTTP/WebSocket bereitstellen.
- EDOMI-LBS kann Ausgaenge nur bei Aenderungen aktualisieren.
- Nach jedem Schreibbefehl wird der Wert von der FriWa neu gelesen und als Readback gesendet.
- Installation aus einem Git-Clone inkl. systemd-Service.

## Status

Aktuell enthalten:
- Profil `profiles/friwa-0x7611.json` fuer RESOL/PAW FriWa Adresse `0x7611`.
- 20 Live-Ausgaenge aus Paket `00_0010_7611_10_0100`.
- 184 Parameter aus `MenuFriwa_1.0.xml`.
- 75 laut XML editierbare Parameter mit passender `input`/`output`-Nummer.
- HTTP API.
- WebSocket API.
- Basic Auth, optional Bearer Token.
- Optional TLS mit eigenem Zertifikat.
- CLI-Testtool `vbus-test`.
- systemd Unit und Installationsscript.

## Voraussetzungen

- Linux, z. B. Raspberry Pi.
- Node.js >= 20.
- npm.
- USB/VBus-Interface, z. B. `/dev/ttyACM0`.
- Benutzer des Dienstes muss Zugriff auf die serielle Schnittstelle haben, normalerweise Gruppe `dialout`.

## Schnellinstallation

```bash
git clone <repo-url> vbus-friwa-gateway
cd vbus-friwa-gateway
sudo ./scripts/install.sh
sudo nano /etc/vbus-friwa-gateway/config.json
sudo systemctl enable --now vbus-friwa-gateway.service
```

Das Installationsscript:
- kopiert das Projekt nach `/opt/vbus-friwa-gateway`,
- legt User `vbus-friwa` an, falls er fehlt,
- installiert Node-Abhaengigkeiten,
- baut `dist/`,
- legt `/etc/vbus-friwa-gateway/config.json` an, falls nicht vorhanden,
- installiert `systemd/vbus-friwa-gateway.service`.

Der Service wird absichtlich nicht automatisch gestartet, damit Port, Auth und TLS vorher geprueft werden koennen.

## Config

Beispiel: `config/example.json`

```json
{
  "serial": {
    "path": "/dev/ttyACM0",
    "baudRate": 9600
  },
  "vbus": {
    "refreshTries": 1,
    "refreshTimeoutMs": 200,
    "actionTries": 2,
    "actionTimeoutMs": 1500
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
  "tls": {
    "enabled": false,
    "certFile": "",
    "keyFile": ""
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

Wichtige Felder:
- `serial.path`: USB/Serial-Port.
- `vbus.refreshTimeoutMs`: kurzer Timeout pro Parameter beim Gesamt-Refresh. Wichtig, damit nicht antwortende XML-Werte den Durchlauf nicht blockieren.
- `vbus.actionTimeoutMs`: laengerer Timeout fuer Einzel-Reads und Writes.
- `server.refreshIntervalMs`: kompletter Parameter-Refresh, Standard `60000`.
- `server.parameterReadMode`: `all`, `writable` oder `none`.
- `auth.username/password`: Basic Auth. Default ist bewusst `admin:admin`, damit ein frischer Test sofort funktioniert.
- `auth.token`: optionaler Bearer Token zusaetzlich zu Basic Auth.
- `tls.enabled`: aktiviert HTTPS/WSS direkt im Gateway.
- `writes.enabled`: globaler Schreibschalter.
- `writes.deny`: Liste von Keys oder Hex-Indexes, die trotz XML nicht schreibbar sein sollen.

Sicherheit:
- Im privaten LAN ist `admin:admin` praktisch fuer den Start.
- Fuer produktiven Betrieb Passwort aendern.
- Wenn ueber Netzgrenzen hinweg erreichbar, TLS aktivieren und Token setzen.
- Unverschluesseltes HTTP/WS ist nur fuer lokale/private Netze gedacht.

## Start ohne systemd

```bash
npm install
npm run build
node dist/index.js --config config/example.json
```

## Testtool

Das Tool nutzt dieselbe Config und dieselbe Werteskalierung wie der Service.
Standard ist der Zugriff auf den laufenden Gateway-Dienst per HTTP API. Dadurch kann `vbus-test` parallel zum systemd-Service benutzt werden, ohne den Serial-Port direkt zu belegen.
Mit `--direct` greift das Tool wie frueher direkt auf die serielle VBus-Schnittstelle zu.

```bash
# alle Parameter lesen
node dist/cli.js --config config/example.json --read --all

# einen Parameter lesen
node dist/cli.js --config config/example.json --read 0x0130

# Wert schreiben, automatisch skaliert: 65 °C -> raw 650
node dist/cli.js --config config/example.json --write 0x0130 65

# Rohwert schreiben
node dist/cli.js --config config/example.json --write 0x0130 650 --raw

# direkter Serial-Test ohne Gateway-Service
node dist/cli.js --config config/example.json --direct --read 0x0130
```

Nach jedem Write liest das Tool den Wert erneut aus der FriWa.

## HTTP API

Auth:
- Basic Auth: `admin:admin` laut Config.
- Oder `Authorization: Bearer <token>`, wenn `auth.token` gesetzt ist.

Endpoints:

```text
GET  /health
GET  /api/profile
GET  /api/state
POST /api/read
POST /api/write
WS   /ws
```

Mehrere Clients:
- Mehrere EDOMI-Bausteine, Browser, CLI-Aufrufe oder andere Clients duerfen gleichzeitig auf denselben Gateway zugreifen.
- Wichtig ist nur: Es darf nur ein Prozess direkt am seriellen VBus-Port haengen.
- Genau dafuer gibt es den Gateway als zentralen Dienst.
- Alle normalen Clients sprechen HTTP/WebSocket mit dem Gateway und oeffnen den Serial-Port nicht selbst.
- Innerhalb des Gateway werden VBus-Reads und Writes per Lock nacheinander ausgefuehrt.
- Dadurch laufen gleichzeitige API-Anfragen nicht parallel auf dem Bus, sondern werden seriell abgearbeitet.
- `vbus-test` nutzt standardmaessig ebenfalls die HTTP API des laufenden Dienstes.
- Nur `vbus-test --direct` greift direkt auf Serial/VBus zu und sollte nicht parallel zum systemd-Service benutzt werden.

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
- Basic Auth Header, falls Client das kann.
- Oder Query-Token: `/ws?token=<token>`.

Events:

```json
{
  "type": "snapshot",
  "ts": "2026-06-16T10:00:00.000Z",
  "data": []
}
```

```json
{
  "type": "change",
  "ts": "2026-06-16T10:00:01.000Z",
  "data": {
    "key": "live.warmwassersolltemperatur",
    "raw": 60,
    "value": 60,
    "text": "60 °C",
    "source": "live",
    "output": 16
  }
}
```

```json
{
  "type": "writeResult",
  "ts": "2026-06-16T10:00:02.000Z",
  "data": {
    "ok": true,
    "key": "param.0x0130.warmwassersoll",
    "index": "0x0130",
    "requestedRaw": 600,
    "before": 450,
    "after": 600
  }
}
```

Der Service sendet:
- `snapshot` beim WebSocket-Verbindungsaufbau,
- `change` nur bei Aenderung,
- erzwungenes `change`/`writeResult` nach einem Write-Readback.

## EDOMI-Mapping

Das Profil enthaelt fuer jedes Feld die Gateway-Nummern `input`/`output` und zusaetzlich EDOMI-Varianten unter `edomi.full` und `edomi.light`.

Regeln:
- Full-LBS `19100832`: Live-Werte `A1..A20`, Parameter ab `A25`, Status `A209..A215`.
- Light-LBS `19100833`: Live-Werte `A1..A20`, praxisnahe Schreibwerte `E16/A16` und `E21/A21..E44/A44`, `A45` frei, Status `A46..A52`.
- Schreibbare Werte haben in der jeweiligen EDOMI-Variante grundsaetzlich Eingang gleich Ausgang.
- Ausnahme Light: `0x0130 WarmwasserSoll` nutzt bewusst `E16/A16`, weil `A16` der Live-Readback `Warmwassersolltemperatur` ist.
- Sichtbare E/A-Namen enthalten keine `0x...`-Indexnummern; die Indexzuordnung steht in der LBS-Hilfe und in der IO-Map.
- Wenn ein Eingang im EDOMI-Baustein beschrieben wird, sendet der LBS einen Write an den zugeordneten Gateway-Key.
- Danach liest der Gateway-Service den Wert erneut und der LBS setzt den echten Readback-Ausgang.
- Vollstaendige Listen: `docs/IO_MAP.md` und `docs/IO_MAP_LIGHT.md`.

Der EDOMI-LBS soll keine eigene VBus-Logik enthalten. Er spricht nur HTTP/WebSocket mit dem Gateway.

### EDOMI-Namen und Overrides

Die technischen Rohdaten kommen aus der RESOL-XML:

- XML-Value-ID, z. B. `WarmwasserSoll`
- Parameterindex, z. B. `0x0130`
- Datentyp, z. B. `TemperatureShort`
- Bereich, z. B. `45..65`
- Einheit und Skalierungsfaktor

Die sichtbaren Namen im EDOMI-Baustein muessen nicht 1:1 aus der XML kommen. Fuer Light werden sprechende Namen im Profil hinterlegt:

```json
{
  "key": "param.0x0130.warmwassersoll",
  "edomi": {
    "light": {
      "input": 16,
      "output": 16,
      "label": "Warmwasser Soll"
    }
  }
}
```

Regel:
- Gateway-Logik nutzt `key` und `indexHex`.
- EDOMI-Porttexte nutzen `edomi.<variant>.label`, wenn vorhanden.
- Fehlt ein Override, wird das XML-Label verwendet.
- Hex-Indizes stehen nicht im Portnamen, sondern in der Baustein-Hilfe und in `docs/IO_MAP_LIGHT.md`.

### EDOMI-Ablauf

Normaler Read:

1. EDOMI triggert E9 oder der Baustein-Timer laeuft ab.
2. LBS startet seinen EXEC-Teil.
3. EXEC ruft `GET /api/state` am Gateway auf.
4. Gateway liefert den letzten bekannten State.
5. Der LBS mappt Gateway-Keys auf EDOMI-Ausgaenge.
6. Ausgaenge werden nur gesetzt, wenn sich der Wert geaendert hat.

Write:

1. Ein schreibbarer Eingang wird beschrieben, z. B. `E16 = 60`.
2. LBS erkennt den Refresh dieses Eingangs.
3. EXEC sendet:

```json
{
  "key": "param.0x0130.warmwassersoll",
  "value": 60
}
```

4. Gateway skaliert `60` mit Faktor `0.1` auf raw `600`.
5. Gateway liest den alten Wert.
6. Gateway schreibt raw `600` auf `0x0130`.
7. Gateway liest `0x0130` erneut.
8. LBS setzt den passenden Ausgang mit dem echten Readback.

Beispiel Light:

```text
E16 Warmwasser Soll = 60
POST /api/write key=param.0x0130.warmwassersoll value=60
Gateway schreibt raw 600
Gateway liest 0x0130 zurueck
A16 Warmwassersolltemperatur = echter Readback-Wert
```

Wenn der Regler einen Wert begrenzt oder ablehnt, ist der Readback entscheidend. EDOMI zeigt dann nicht blind den Wunschwert, sondern den Wert, den die FriWa danach wirklich liefert.

## Messung

Auf der aktuellen FriWa-Node dauerte ein Gateway-Read-All ueber HTTP/API mit kurzen Refresh-Timeouts etwa `33.4 s`.
Dabei wurden im Test `20` Live-Werte und `128` erfolgreich gelesene Parameterwerte im State gemeldet. Nicht jeder der `184` XML-Parameter antwortet als normaler Value-Index; solche Werte werden beim Refresh uebersprungen.

## Profil neu erzeugen

Das Profil wird nicht aus mitgelieferten RESOL-XMLs erzeugt, sondern aus lokal extrahierten XML-Dateien. Jeder Nutzer soll das RSC-Paket selbst von RESOL beziehen.

RESOL-Seite:

```text
https://www.resol.de/de/produktdetail/170
```

Die Seite ist die Produktseite der ServiceCenter-Software RSC. Dort gibt es im Software-Bereich den RSC-Download. Beim Erstellen dieser Doku war der direkte Paketlink:

```text
https://www.resol.de/software/RSC/RSC.zip
```

Empfohlener Ablauf:

```bash
# 1. RSC.zip selbst von RESOL herunterladen, z. B. nach /tmp/RSC.zip

# 2. benoetigte XMLs lokal extrahieren
npm run extract:resol -- --archive /tmp/RSC.zip

# 3. Profil erzeugen
npm run generate:profile

# 4. EDOMI-Bausteine erzeugen
npm run generate:edomi:full
npm run generate:edomi:light
```

Das Extraktionsscript schreibt:

```text
vendor/resol-rsc/MenuFriwa_1.0.xml
vendor/resol-rsc/VBusSpecificationResol.xml
```

Diese Dateien sind per `.gitignore` ausgeschlossen.

Direkter Profil-Build:

```bash
npm run generate:profile
npm run build
```

Der Generator liest:
- `vendor/resol-rsc/MenuFriwa_1.0.xml`
- `vendor/resol-rsc/VBusSpecificationResol.xml`

und schreibt:
- `profiles/friwa-0x7611.json`

Aktuell ist das Profil fest fuer die FriWa-Adresse `0x7611` ausgelegt. Die Adresse muss beim Standardbefehl nicht extra angegeben werden.

Ausfuehrliche Anleitung:

```text
docs/RESOL_RSC_PROFILE.md
```

EDOMI-LBS neu erzeugen:

```bash
python3 scripts/generate_edomi_lbs.py --profile profiles/friwa-0x7611.json --variant full --out /zwischenspeicher/edomi/LBS/19100832/19100832_lbs.php
python3 scripts/generate_edomi_lbs.py --profile profiles/friwa-0x7611.json --variant light --out /zwischenspeicher/edomi/LBS/19100833/19100833_lbs.php
```

## Bekannte bestaetigte Werte

- `0x0130` `WarmwasserSoll`: raw `600` entspricht `60 °C`.
- `0x0100` `OptionNotbetrieb`: `0/1`.
- `0x0101` `Notbetrieb`: `12..100 %`.

## Entwicklung

```bash
npm install
npm run generate:profile
npm run generate:edomi:full
npm run generate:edomi:light
npm run build
node dist/cli.js --help
```

Keine destruktiven VBus-Writes ohne klare Absicht. Fuer Tests zuerst `--read` nutzen.

## Lizenz und Git-Release

Projektcode:

- MIT License, siehe `LICENSE`.

Abhaengigkeiten:

- `resol-vbus-core`: MIT
- `serialport`: MIT
- `ws`: MIT
- `typescript`: Apache-2.0

Details:

```text
docs/LICENSES.md
docs/GIT_RELEASE_CHECKLIST.md
docs/RESOL_RSC_PROFILE.md
```

Wichtiger Punkt vor einem oeffentlichen Push:
- `profiles/friwa-0x7611.json`, die EDOMI-LBS-Dateien und die IO-Maps koennen aus RESOL ServiceCenter XMLs abgeleitete Mappingdaten enthalten.
- Die XMLs bzw. daraus abgeleitete Mappingdaten koennen RESOL/PAW-Rechten unterliegen.
- Fuer ein privates Repo ist das technisch unkritisch.
- Fuer ein oeffentliches Repo sollte geklaert werden, ob generierte Mappingdaten mitverteilt werden duerfen.
- Sichere oeffentliche Variante: Generator, Extractor und Doku committen; Profil, IO-Maps und EDOMI-LBS lokal aus eigenen RESOL-Dateien erzeugen lassen.
