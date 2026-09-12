# Hargassner mit deutscher Übersetzung

Dieser Fork ergänzt Deutsch, Englisch und Französisch über die Home-Assistant-Sprachdateien. Grundlage: [lithium73fr/hargassner-ha](https://github.com/lithium73fr/hargassner-ha).

## Installation / Wechsel

1. Home-Assistant-Backup erstellen.
2. In HACS das benutzerdefinierte Repository `https://github.com/holber0/hargassner-ha` (Integration) verwenden. Die bisherige Quelle nicht zusätzlich unter derselben Integrationsdomäne installieren.
3. Die Dateien in `custom_components/hargassner` aktualisieren und Home Assistant neu starten. Die vorhandene Integration muss nicht gelöscht oder neu eingerichtet werden.
4. Für deutsche Entitätsnamen die Home-Assistant-Systemsprache auf Deutsch stellen; Auswahlwerte und Formulare folgen der Sprache der Oberfläche.

Bestehende Unique IDs und API-Befehle bleiben unverändert. Manuell vergebene Entitätsnamen und Dashboard-Titel überschreibt die Übersetzung nicht. Interne französische Auswahlwerte bleiben für bestehende Automationen erhalten; die Oberfläche zeigt übersetzte Beschriftungen. Eigene Anlagen-/Heizkreisnamen aus der Cloud sowie unbekannte, von der API gelieferte Statustexte werden unverändert übernommen. Es werden keine Heizparameter automatisch geändert.

## Prüfung

`python -m unittest discover -s tests` prüft Übersetzungsschlüssel, Platzhalter und unveränderte Auswahlbefehle ohne Verbindung zur Heizung. Ein Live-Test der Darstellung in Home Assistant steht noch aus.

---

# Hargassner Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Custom integration for Hargassner pellet/biomass boilers via the Hargassner cloud API.

> ⚠️ **Unofficial integration** — reverse-engineered from the Android app v1.10.0. Requires an active Hargassner cloud account.

## Supported Devices

Tested with **Nano.2 12**. Should work with all Touch Tronic devices connected to the Hargassner cloud.

## Features

| Platform | Description |
|---|---|
| `sensor` | Boiler/flue/flow temperatures, fuel stock, outdoor temperature, state |
| `climate` | Thermostat per heating circuit |
| `number` | Day/night setpoints, heating curve slope, deactivation limits, fuel stock |
| `select` | Circuit mode (Auto/Heating/Setback/Off), bathroom heating |

## Installation via HACS

1. HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/lithium73fr/hargassner-ha` → **Integration**
3. Install "Hargassner" → Restart HA

## Manual Installation

Copy `custom_components/hargassner/` into `config/custom_components/` and restart.

## Configuration

Settings → Devices & Services → Add Integration → **Hargassner** → enter your app email and password.

## Contributing

If you have a different model and some entities are missing, open an issue with the output of:
```bash
curl "https://web.hargassner.at/api/installations/{id}/widgets" -H "Authorization: Bearer {token}" -H "Branding: BRANDING_HARGASSNER"
```

## Disclaimer

Not affiliated with or endorsed by Hargassner GmbH.

## Brennstoffverbrauch in kWh (ab v1.0.4)

In den Integrationsoptionen kann ein **fortlaufender Pellet-Verbrauchszähler in kg** ausgewählt werden. Bei der lokalen Nano-PK-Integration ist dies beispielsweise `sensor.nano_pk_pellet_consumption`. Er muss `unit_of_measurement: kg` und `state_class: total_increasing` besitzen. Den Lagerbestand nicht verwenden.

Die Integration legt dann **Brennstoffenergie (berechnet)** an:

`kWh = kumulierter Pelletverbrauch in kg × 4,8 kWh/kg`

Beispiel: 6.548 kg entsprechen 31.430,4 kWh. Das ist die Energie des eingesetzten Brennstoffs unter Annahme von 4,8 kWh/kg, keine gemessene Nutzwärme und kein Jahresverbrauch. Ein Faktor für den Kesselwirkungsgrad wird nicht eingerechnet.

Der Sensor hat die HA-Klassen `energy` und `total_increasing`. Er folgt Änderungen der gewählten Quelle direkt, ohne zusätzliche Cloud-Abfragen. Fehlende, negative oder nichtnumerische Werte werden nicht als Nullverbrauch ausgegeben. Ein tatsächlicher Zählerreset wird an HA weitergereicht; falsche Rücksprünge im Quellzähler können daher auch die Statistik verfälschen. Die Quelle muss ein zuverlässiger Verbrauchszähler sein.

Für Tages-, Monats- und Jahreswerte können Verbrauchszähler-Helfer (Utility Meter) mit diesem Sensor als Quelle angelegt werden. Sie beginnen ab Einrichtung und rekonstruieren keine früheren Perioden. Beim Wechsel auf einen anderen Quellzähler entsteht absichtlich eine neue Sensoridentität. Den bisherigen kWh-Sensor und den neuen nicht gleichzeitig für denselben Verbrauch zählen lassen. Vorhandene Statistiken werden nicht automatisch migriert.

Die Cloud-API liefert im bisher geprüften Code keinen bestätigten kumulierten kg-Verbrauchswert. Diese Funktion benötigt deshalb eine vorhandene kg-Quelle, etwa aus Telnet. Sie ersetzt die lokale Verbrauchserfassung nicht. Eine spätere direkt belegte Cloud-Quelle kann auf dieselbe Berechnung aufsetzen.
