# EDOMI Handoff: VBus FriWa Gateway

Diese Datei ist die Spezifikation fuer den EDOMI-LBS-Agenten.

## Aufgabe

Baue einen EDOMI-LBS fuer `vbus-friwa-gateway`.

Der LBS:
- verbindet sich zum Gateway,
- aktualisiert Ausgaenge nur bei Aenderung,
- sendet Eingangs-Aenderungen als Writes an das Gateway,
- verlaesst sich nach Writes immer auf den Readback-Wert des Gateways,
- enthaelt keine direkte VBus-/Serial-Logik.

## Gateway

Default:

```text
http://<friwa-node>:8787
ws://<friwa-node>:8787/ws
Basic Auth: admin/admin
```

TLS optional:

```text
https://<friwa-node>:8787
wss://<friwa-node>:8787/ws
```

## LBS Eingangs-Config

Vorschlag:

- `E1` Gateway Host/IP
- `E2` Port
- `E3` TLS an/aus
- `E4` Username
- `E5` Passwort
- `E6` Token
- `E7` Verbinden/aktiv
- `E8` Reconnect Sekunden
- `E9` Voll-Refresh Trigger
- `E10` Debug

Danach Werteingänge aus Profil:
- Fuer Full die Nummern aus `edomi.full` verwenden.
- Fuer Light die Nummern aus `edomi.light` verwenden.
- Schreibbare Werte haben im Normalfall Eingang gleich Ausgang.
- Light-Ausnahme: `0x0130 WarmwasserSoll` nutzt `E16/A16`, weil `A16` schon der Live-Readback `Warmwassersolltemperatur` ist.

## LBS Ausgaenge

Aus `profiles/friwa-0x7611.json`:
- Fuer jedes Live-Feld die Variantennummer als `A#` anlegen.
- Fuer jeden Parameter mit Variantenausgang die Variantennummer als `A#` anlegen.
- Nur bei Aenderung schreiben.
- Beim Start nach `snapshot` alle empfangenen Werte initial setzen.
- Nach `writeResult` und nachfolgenden `change`-Events passende Ausgaenge aktualisieren.

## Write-Protokoll

Wenn ein Werteingang beschrieben wird:

```http
POST /api/write
Authorization: Basic ...
Content-Type: application/json

{
  "key": "param.0x0130.warmwassersoll",
  "value": 60
}
```

Alternativ mit Index:

```json
{
  "index": "0x0130",
  "value": 60
}
```

Der Gateway-Service skaliert selbst:
- `0x0130` `60` wird raw `600`.
- `--raw` gibt es nur im CLI, nicht im LBS-Standard.

Der Gateway-Service liest nach dem Schreiben den Wert neu und sendet das Ergebnis per WebSocket.

## WebSocket Events

`snapshot`:
- beim Connect,
- enthaelt alle aktuellen Werte.

`change`:
- nur wenn Wert anders ist,
- nach Writes erzwungen fuer den Readback-Wert.

`writeResult`:
- technische Write-Bestaetigung,
- fuer Status/Debug-Ausgang nutzen.

## Wichtige Profilregeln

- Full-LBS `19100832`: Live `A1..A20`, Parameter ab `A25`, Status `A209..A215`.
- Light-LBS `19100833`: Live `A1..A20`, Schreibwerte `E16/A16` und `E21/A21..E44/A44`, `A45` frei, Status `A46..A52`.
- Sichtbare E/A-Namen sollen kurz und aussagekraeftig sein; Hex-Indizes gehoeren in Hilfe/Map, nicht in den Portnamen.
- Der LBS muss Gateway-Keys auf EDOMI-Ausgaenge mappen; nicht blind die Gateway-`output`-Nummer aus `/api/state` verwenden.

## Fehlerbehandlung

Der LBS soll anzeigen:
- Verbindungsstatus,
- letzter Fehler,
- letzter Write-Status,
- Timestamp letzter Gateway-Wert.

Keine parallelen Writes fuer denselben Eingang starten.
