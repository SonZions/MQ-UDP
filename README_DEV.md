# Entwicklerdokumentation

Diese Dokumentation beschreibt Aufbau und Zusammenspiel der Module des MQ-UDP-Projekts. Sie richtet sich an Entwicklerinnen und Entwickler, die den Code warten oder erweitern möchten.

## Gesamtüberblick

MQ-UDP kombiniert drei Kernfunktionen:

1. **MQTT/UDP-Brücke** (`app.py`): Bidirektionale Weiterleitung von Nachrichten zwischen einem MQTT-Topic und einem UDP-Endpunkt, inklusive automatisierter Veröffentlichungen.
2. **Datenaufbereitung** (`loxone_data.py`): Laden und Normalisieren der `LoxAPP3.json` eines Loxone Miniservers, inklusive optionaler Statusauflösung einzelner UUIDs.
3. **Weboberfläche und Automatikverwaltung** (`web_app.py` & `templates/controls.html`): Anzeige der verfügbaren Loxone-Steuerelemente, Verwaltung der Automatik-Konfiguration und Hintergrundstart der Brücke.

Das Modul `auto_config.py` stellt einen persistenten Speicher für die Automatik-Auswahl bereit, der sowohl von der Brücke als auch von der Weboberfläche genutzt wird.

## Modulübersicht

### `app.py`

`app.py` bündelt alle Funktionen rund um die MQTT/UDP-Brücke und den Automatikmodus:

- `Config`: Dataclass mit Broker-, Topic- und UDP-Zieldaten sowie optionalen Zugangsdaten und dem Intervall für die Automatik.【F:app.py†L27-L35】【F:app.py†L118-L149】
- MQTT → UDP: `create_mqtt_client`, `create_on_message`, `mqtt_to_udp` abonnieren das konfigurierte Topic und leiten Nachrichten per UDP weiter, wobei lokal veröffentlichte Nachrichten erkannt und unterdrückt werden (`record_local_mqtt_message`, `should_ignore_mqtt_message`).【F:app.py†L52-L115】【F:app.py†L164-L191】
- UDP → MQTT: `udp_to_mqtt` lauscht auf dem UDP-Port, veröffentlicht eingehende Pakete auf dem MQTT-Topic und markiert sie als lokal erzeugt.【F:app.py†L193-L211】
- Argument- und Umgebungs-Parsing: `parse_args` erzeugt eine `Config` aus CLI-Argumenten, `config_from_env` liest dieselben Einstellungen aus Umgebungsvariablen.【F:app.py†L213-L259】
- Automatikmodus: `automatic_mode` lädt periodisch Loxone-Daten, filtert aktivierte Controls über `AutoConfigStore`, erzeugt Payloads via `format_control_message` und veröffentlicht sie unter einem abgeleiteten Topic (`resolve_target_topic`). Deaktivierte Controls erhalten ein leeres JSON, um den Zustand zurückzusetzen.【F:app.py†L261-L356】
- `main` startet die Brücke als eigenständige Anwendung und betreibt die MQTT- und UDP-Threads.【F:app.py†L358-L372】

### `auto_config.py`

`AutoConfigStore` verwaltet, welche Controls im Automatikmodus aktiv sind:

- Die Konfiguration wird als JSON-Datei gespeichert und thread-sicher über ein Lock aktualisiert.【F:auto_config.py†L10-L53】
- `set_enabled` / `is_enabled` schalten einzelne UUIDs um, `enabled_ids` liefert alle aktivierten Controls.【F:auto_config.py†L35-L45】
- `sync_from` entfernt verwaiste Einträge, wenn Controls im Loxone-Datensatz nicht mehr vorhanden sind.【F:auto_config.py†L47-L53】

### `loxone_data.py`

Dieses Modul kapselt das Laden der `LoxAPP3.json` sowie Hilfsfunktionen für die Anzeige und den Automatikmodus:

- `LoxoneDataSource` beschreibt, ob Daten per HTTP oder aus einer lokalen Datei bezogen werden. `from_env` leitet die Konfiguration aus Umgebungsvariablen ab und generiert bei Bedarf ein Status-URL-Template für einzelne UUID-Abfragen.【F:loxone_data.py†L13-L63】
- `LoxoneDataFetcher.load` lädt die JSON-Daten über `requests` (falls `url` gesetzt ist) oder eine lokale Datei, wobei relative Pfade relativ zum Repository-Verzeichnis aufgelöst werden.【F:loxone_data.py†L68-L111】
- `resolve_state_value` nutzt das Status-Template, um Live-Werte einzelner UUIDs nachzuladen; alle Antworten werden gecacht und in menschenlesbare Strings umgewandelt.【F:loxone_data.py†L113-L180】
- `extract_controls` transformiert den `controls`-Abschnitt in `ControlRow`-Datensätze inklusive Raum- und Kategorie-Auflösung, sortiert nach Raum und Name.【F:loxone_data.py†L182-L224】
- Hilfsfunktionen `_build_lookup`, `_extract_state_payload`, `_flatten_mapping`, `_stringify` normalisieren verschachtelte Strukturen in einfache Key/Value-Listen für Anzeige und Textausgabe.【F:loxone_data.py†L226-L276】

### `web_app.py`

Die FastAPI-Anwendung orchestriert Brücke und Anzeige:

- Abhängigkeiten (`get_fetcher`, `get_auto_config_store`, `get_bridge_config`) sind über `lru_cache` memoisiert, um Prozesse und Threads zu teilen.【F:web_app.py†L30-L48】
- Beim `startup`-Event werden MQTT/UDP-Brücke und Automatikmodus in Daemon-Threads gestartet, sofern die Broker-Konfiguration vorhanden ist.【F:web_app.py†L50-L74】
- Der `/`-Handler lädt die Loxone-Daten, erzeugt Metadaten, synchronisiert den `AutoConfigStore` und rendert das Template `controls.html` mit allen Controls und der aktuellen Automatik-Konfiguration.【F:web_app.py†L76-L114】
- Die JSON-API `/api/auto-config` liefert bzw. aktualisiert die Automatik-Auswahl und wird vom Frontend genutzt, um Toggle-States zu laden bzw. zu speichern.【F:web_app.py†L116-L131】
- Die `main`-Funktion erlaubt das Starten via CLI oder Umgebungsvariablen und ruft Uvicorn mit den gewünschten Parametern auf.【F:web_app.py†L133-L180】

### `templates/controls.html`

Das Jinja2-Template rendert die Tabelle der Controls und bindet die Automatik-Schalter:

- Tabellarische Darstellung von Name, Typ, Raum, Kategorie, Details, Zuständen und Links jedes Controls.【F:templates/controls.html†L1-L129】
- Für den Automatikmodus enthält jede Zeile einen Switch, der über `data-uuid` identifiziert wird.【F:templates/controls.html†L130-L170】
- Ein JavaScript-Snippet lädt initial den aktuellen Status aus `/api/auto-config` und synchronisiert Änderungen per `fetch`-POST-Anfrage.【F:templates/controls.html†L172-L211】

## Datenflüsse und Parsing

1. **Konfiguration**: CLI (`parse_args`) oder Umgebungsvariablen (`config_from_env`, `LoxoneDataSource.from_env`) bestimmen Broker- und Loxone-Zugriff. Die Web-App nutzt ausschließlich die Umgebungsvarianten, um Brücke und Fetcher konsistent zu starten.【F:app.py†L213-L259】【F:loxone_data.py†L41-L63】【F:web_app.py†L30-L74】
2. **Loxone JSON**: `LoxoneDataFetcher.load` liest das Roh-JSON; `extract_controls` normalisiert `controls`, `rooms`, `cats` zu `ControlRow`-Instanzen; `_flatten_mapping` wandelt `details`/`states` in sortierte Listen um.【F:loxone_data.py†L68-L224】【F:loxone_data.py†L244-L266】
3. **MQTT/UDP**: `mqtt_to_udp` registriert ein On-Message-Callback, das Nachrichten dekodiert, mit `should_ignore_mqtt_message` filtert und via `send_udp_message` weiterleitet. `udp_to_mqtt` empfängt UDP-Pakete, markiert sie als lokal (`record_local_mqtt_message`) und veröffentlicht sie über `mqtt.Client.publish`.【F:app.py†L52-L206】
4. **Automatikmodus**: `automatic_mode` ruft periodisch `fetcher.load()` auf, filtert aktivierte UUIDs (`AutoConfigStore.enabled_ids`), generiert Textpayloads (`format_control_message` + optional `resolve_state_value`) und publiziert sie auf `resolve_target_topic`. deaktivierte UUIDs erhalten `{}` zur Rücksetzung.【F:app.py†L261-L356】【F:auto_config.py†L35-L47】【F:loxone_data.py†L113-L180】
5. **Frontend**: `render_controls` übergibt `controls`, `metadata`, `auto_config` an `controls.html`. Das Template rendert Schalter, deren Status per JavaScript geladen und aktualisiert wird. Änderungen rufen `/api/auto-config/{uuid}` auf, welches den Store aktualisiert und sofortiges Feedback liefert.【F:web_app.py†L76-L131】【F:templates/controls.html†L130-L211】

## Zusammenarbeit der Module

- `web_app.py` importiert und startet `automatic_mode`, `mqtt_to_udp` und `udp_to_mqtt` aus `app.py`, sodass die Weboberfläche und die Brücke innerhalb eines Prozesses laufen können.【F:web_app.py†L18-L70】
- Sowohl `automatic_mode` als auch die Web-API greifen auf denselben `AutoConfigStore` zu, wodurch UI-Änderungen unmittelbar in den automatischen Veröffentlichungen berücksichtigt werden.【F:web_app.py†L76-L131】【F:app.py†L261-L356】【F:auto_config.py†L10-L53】
- `automatic_mode` nutzt `LoxoneDataFetcher` aus `loxone_data.py`, um Controls und Statuswerte aufzubereiten; dieselbe Instanz wird auch für die Webanzeige verwendet, was Mehrfach-Downloads reduziert (via `lru_cache`).【F:web_app.py†L30-L114】【F:loxone_data.py†L68-L224】
- Das Template `controls.html` repräsentiert die Datenstruktur `ControlRow` 1:1 und interagiert ausschließlich über die JSON-APIs der Web-App, womit die Anwendungslogik im Python-Code gebündelt bleibt.【F:templates/controls.html†L1-L211】【F:web_app.py†L76-L131】

## Erweiterungshinweise

- Neue Ausgabeformate oder Zielsysteme sollten auf `format_control_message` aufbauen oder alternative Formatter bereitstellen; `automatic_mode` lässt sich durch Dependency Injection eines alternativen `fetcher_factory` testen oder erweitern.【F:app.py†L261-L356】
- Für zusätzliche Datenquellen können weitere Eigenschaften in `LoxoneDataSource` ergänzt werden; `from_env` ist die zentrale Stelle für Umgebungsvariablen und sollte entsprechend erweitert werden.【F:loxone_data.py†L13-L63】
- Die Weboberfläche nutzt Jinja2-Templates. Erweiterungen erfolgen im Verzeichnis `templates/`, wobei zusätzliche Routen im FastAPI-App-Objekt in `web_app.py` registriert werden.【F:web_app.py†L12-L131】【F:templates/controls.html†L1-L211】

