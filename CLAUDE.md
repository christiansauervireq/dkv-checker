# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projekt

DKV Abrechnungs-Checker - Streamlit-Anwendung zur Analyse von DKV-Tankkartenabrechnungen (Kraftstoffverbrauch, Anomalie-Erkennung).

## Befehle

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# Anwendung starten (einfach)
./start.command

# Anwendung starten (manuell)
source venv/bin/activate
streamlit run dkv_checker.py
```

## Architektur

Einzelne Streamlit-App (`dkv_checker.py`, ~2380 Zeilen) mit fünf Tabs:

1. **Import & Analyse**: Multi-Datei-Upload (CSV/PDF), automatischer Import, Duplikatsprüfung, **manuelle Tankvorgänge**
2. **Verbrauchsentwicklung**: Altair-Charts mit Datumsfilter (Von/Bis), Fahrzeugauswahl, monatliche Aggregation
3. **Historie**: Persistente Datenspeicherung, Filter (Fahrzeug, Zeitraum, Quelldatei), CSV-Export, direkte Tabellenbearbeitung, Status-Spalte mit Kurzformen
4. **Auffälligkeiten**: Zentrale Übersicht mit Fahrzeug-Filter, Quittierung (mit Pflichtkommentar), editierbare Tabelle, E-Mail-Benachrichtigung an Besitzer
5. **Einstellungen**: Sub-Tabs für Fahrzeug-Verwaltung (inkl. Verbrauchsgrenzen), E-Mail (SMTP + Vorlage), Benutzerverwaltung

**Datenpersistenz**: JSON-Dateien im Projektverzeichnis (automatisch erstellt).

## Projektstruktur

```
dkv-checker/
├── dkv_checker.py      # Hauptprogramm (~2600 Zeilen)
├── i18n.py             # Mehrsprachigkeit (DE/EN)
├── requirements.txt    # streamlit, pandas, altair, pdfplumber
├── start.command       # Startskript (macOS, ausführbar)
├── docker-compose.yml  # Docker Compose mit Nginx HTTPS
├── nginx.conf          # Nginx Reverse Proxy Konfiguration
├── generate-ssl.sh     # SSL-Zertifikat Generator
├── handbuch.html       # Benutzerhandbuch (HTML)
├── historie.json       # Gespeicherte Tankdaten (wird erstellt)
├── fahrzeuge.json      # Fahrzeug-Besitzer-Zuordnung + Verbrauchsgrenzen (wird erstellt)
├── smtp_config.json    # SMTP-Konfiguration (wird erstellt)
├── email_vorlage.json  # E-Mail-Vorlage (wird erstellt)
├── benutzer.json       # Benutzerverwaltung mit gehashten Passwörtern (wird erstellt)
├── ssl/                # SSL-Zertifikate (wird erstellt, nicht im Git)
├── CLAUDE.md           # Diese Datei
└── venv/               # Virtuelle Python-Umgebung
```

## Datenformat

### CSV (DKV-Abrechnung)
- Semikolon-Delimiter
- Deutsche Zahlenformate (1.234,56)
- Header in Zeile 1, Daten ab Zeile 6
- Relevante Felder: Kennzeichen, km-Stand, Lieferdatum, Menge, Wert incl. USt

### PDF (DKV E-Rechnung)
- Wird mit pdfplumber geparst
- Tabellenextraktion mit Regex-Nachbearbeitung
- Weniger genau als CSV (besonders km-Stände)

### Tankvorgang-Datenstruktur
```json
{
  "kennzeichen": "AB-CD 123",
  "datum": "2025-12-01",
  "zeit": "14:30",
  "km_stand": 85000,
  "menge_liter": 45.5,
  "verbrauch": 8.2,
  "km_differenz": 550,
  "betrag_eur": 75.50,
  "tankstelle": "ARAL Hamburg",
  "warenart": "DIESEL",
  "quelldatei": "abrechnung_2025_12.csv",
  "quittiert": false,
  "quittiert_kommentar": "",
  "quittiert_von": "",
  "quittiert_am": ""
}
```

## Kernfunktionen

| Funktion | Beschreibung |
|----------|--------------|
| `parse_german_number()` | Konvertiert "1.234,56" → 1234.56 |
| `parse_dkv_csv()` | Parst DKV-CSV-Dateien |
| `parse_dkv_pdf()` | Parst DKV-PDF-Rechnungen |
| `berechne_verbrauch()` | Berechnet Verbrauch für Import-Daten |
| `berechne_verbrauch_historie()` | Berechnet Verbrauch für alle Historie-Einträge (sortiert nach Datum+Zeit) |
| `pruefe_auffaelligkeiten()` | Erkennt Probleme mit fahrzeugspezifischen Grenzen |
| `speichere_historie()` | Speichert und berechnet automatisch neu |
| `lade_fahrzeuge()` / `speichere_fahrzeuge()` | Fahrzeug-Besitzer-Verwaltung + Verbrauchsgrenzen |
| `lade_smtp_config()` / `speichere_smtp_config()` | SMTP-Konfiguration |
| `lade_email_vorlage()` / `speichere_email_vorlage()` | E-Mail-Vorlage |
| `erstelle_auffaelligkeiten_email()` | Erstellt HTML-E-Mail mit Platzhaltern |
| `teste_smtp_verbindung()` | Testet SMTP-Serververbindung |
| `sende_benachrichtigung()` | Versendet E-Mail an Besitzer |
| `hash_passwort()` / `pruefe_passwort()` | PBKDF2-SHA256 Passwort-Hashing |
| `authentifiziere_benutzer()` | Login mit gehashtem Passwort |
| `aktueller_benutzer_hat_recht()` | Rechteprüfung für Aktionen |
| `speichere_manuellen_tankvorgang()` | Speichert manuell erfasste Tankvorgänge |
| `_()` / `t()` | Übersetzungsfunktionen für i18n |

## Prüflogik

Warnungen werden generiert bei:
- Fehlenden km-Ständen (Warnung)
- Sinkenden km-Ständen - negatives Delta (Fehler)
- Verbrauch unter Minimum (Warnung) - Standard: 3 L/100km, pro Fahrzeug konfigurierbar
- Verbrauch über Maximum (Fehler) - Standard: 25 L/100km, pro Fahrzeug konfigurierbar

## Auffälligkeiten quittieren

Auffälligkeiten können mit Pflichtkommentar quittiert werden (z.B. "Mietwagen getankt"):
- Quittierte Auffälligkeiten werden standardmäßig ausgeblendet (Filter "Quittierte ausblenden")
- Zählen nicht zum Tab-Zähler und werden nicht per E-Mail gemeldet
- Quittierung speichert: Kommentar, Benutzer, Zeitstempel
- Gespeichert direkt am Tankvorgang in `historie.json`
- Nach Quittierung bleibt Tab aktiv (JavaScript-Workaround mit `st.session_state["aktiver_tab"]`)

## Status-Spalte in Historie

Die Status-Spalte zeigt Auffälligkeiten mit Kurzformen:
- `⚠️ km?` = Fehlender km-Stand (offen)
- `⚠️ km↓` = km-Stand gesunken (offen)
- `⚠️ L↓` = Verbrauch zu niedrig (offen)
- `⚠️ L↑` = Verbrauch zu hoch (offen)
- `✓ km↓` = Quittiert (grün hinterlegt)

Tooltip bei Spaltenüberschrift "Status" erklärt alle Kurzformen.

## Fahrzeugspezifische Verbrauchsgrenzen

Pro Fahrzeug können individuelle Verbrauchsgrenzen definiert werden:

```json
{
  "fahrzeuge": [
    {
      "kennzeichen": "BRB-VQ10",
      "besitzer_name": "Max Mustermann",
      "besitzer_email": "max.mustermann@firma.de",
      "verbrauch_min": 5.0,
      "verbrauch_max": 12.0,
      "notizen": "Transporter"
    }
  ]
}
```

Die Prüflogik in `pruefe_auffaelligkeiten()` verwendet diese Werte, Fallback auf 3/25 L/100km.

## Login-System mit Rollen

Drei Rollen mit unterschiedlichen Rechten:

| Rolle | Beschreibung | Rechte |
|-------|--------------|--------|
| **admin** | Administrator | Vollzugriff inkl. Benutzerverwaltung |
| **manager** | Manager | Daten verwalten, E-Mails senden, Fahrzeuge verwalten |
| **viewer** | Betrachter | Nur Lesezugriff und Export |

**Standard-Login:** `admin` / `admin` (Passwortänderung beim ersten Login erzwungen)

**Passwort-Hashing:** PBKDF2-SHA256 mit 100.000 Iterationen und zufälligem Salt.

## Multi-Datei-Import

- Mehrere CSV/PDF-Dateien gleichzeitig hochladbar
- Automatische Speicherung in Historie (kein Button-Klick nötig)
- Quelldatei wird in jedem Tankvorgang gespeichert
- **Duplikatsprüfung:**
  - Datei bereits importiert → Warnung, Datei wird übersprungen
  - Datensatz bereits vorhanden (Kennzeichen + Datum + Zeit) → wird übersprungen
- Filter in Historie nach Quelldatei möglich

## Bearbeitungsfunktion

Nach Login können Daten direkt in Tabellen bearbeitet werden (je nach Rolle):
- `st.data_editor` für editierbare Tabellen
- Editierbar: km-Stand, Liter, EUR, Tankstelle
- Nicht editierbar (berechnet): km gefahren, L/100km, Quelldatei
- Status-Spalte zeigt Auffälligkeiten mit Kurzform (⚠️ offen, ✓ quittiert)
- Beim Speichern: automatische Neuberechnung aller Verbrauchswerte
- Read-Only-Ansicht: Rot hinterlegt (offen), grün hinterlegt (quittiert)

## Wichtige Implementierungsdetails

1. **Sortierung**: Alle Bereiche sortieren nach Datum UND Zeit (`sort_values(["datum", "zeit"])`), wichtig für mehrere Tankungen am gleichen Tag.

2. **Verbrauchsberechnung**: `berechne_verbrauch_historie()` iteriert pro Fahrzeug chronologisch und berechnet km_differenz und verbrauch für jeden Eintrag basierend auf dem vorherigen km_stand.

3. **Auffälligkeits-IDs**: Format `{kennzeichen}_{datum}_{zeit}` zur eindeutigen Identifikation von Einträgen.

4. **Status-Spalte**: Zeigt Kurzformen (km?, km↓, L↓, L↑) mit ⚠️ (offen) oder ✓ (quittiert). Tooltip erklärt Bedeutung.

5. **Filter in Korrektur-Bereich**: Fahrzeug-Auswahl und Textsuche (Tankstelle, Datum, Quelldatei).

6. **PDF-Parsing**: Komplexe Tabellenstruktur mit mehrzeiligen Zellen. Daten werden mit Regex aus zusammengeführten Zellen extrahiert.

7. **Tab-Navigation**: Einstellungen-Tab verwendet verschachtelte `st.tabs()`. Nach Quittierung: JavaScript-Workaround um im Tab zu bleiben (`components.html` mit Tab-Klick).

8. **Datumsfilter**: Verbrauchsentwicklung hat Von/Bis-Datumsauswahl mit `st.date_input`.

## Bekannte Einschränkungen

- PDF-Import: km-Stände können ungenau sein (PDF-Layout-abhängig)
- Verbrauch wird nur für Kraftstoffe berechnet (DIESEL, SUPER, BENZIN, EURO), nicht für AdBlue
- SMTP-Passwort wird im Klartext in `smtp_config.json` gespeichert

## E-Mail-Benachrichtigung

- Manueller Versand im Tab "Auffälligkeiten"
- SMTP-Konfiguration im Tab "Einstellungen → E-Mail → Server-Einstellungen"
- Anpassbare E-Mail-Vorlage mit Platzhaltern unter "Einstellungen → E-Mail → Vorlage"
- HTML-formatierte E-Mails mit Auffälligkeiten-Tabelle
- Farbcodierung: Fehler rot, Warnungen orange

**E-Mail-Platzhalter:**
- `{besitzer_name}` - Name des Fahrzeug-Besitzers
- `{kennzeichen}` - Fahrzeug-Kennzeichen
- `{anzahl_gesamt}` - Gesamtzahl Auffälligkeiten
- `{anzahl_fehler}` - Anzahl Fehler
- `{anzahl_warnungen}` - Anzahl Warnungen

## Benutzerverwaltung

Gespeichert in `benutzer.json`:

```json
{
  "benutzer": [
    {
      "benutzername": "admin",
      "passwort_hash": "salt$hash",
      "rolle": "admin",
      "name": "Administrator",
      "email": "",
      "aktiv": true,
      "muss_passwort_aendern": false
    }
  ]
}
```

## Manuelle Tankvorgänge

Im Import-Tab können Tankvorgänge manuell erfasst werden (z.B. für private Tankungen):

- Fahrzeugauswahl (aus Historie oder neues Kennzeichen)
- Datum, Uhrzeit, km-Stand, Menge, Betrag
- Tankstelle, Warenart, Zahlungsart, Notiz
- Quelldatei wird als "MANUELL" markiert
- Duplikatsprüfung (Kennzeichen + Datum + Zeit)
- Erfordert Recht "importieren"

## HTTPS mit Nginx

Docker-basiertes Setup mit HTTPS-Unterstützung:

```bash
# 1. SSL-Zertifikat generieren
./generate-ssl.sh

# 2. Container starten
docker-compose up -d

# 3. Öffnen: https://localhost
```

**Architektur:**
- Nginx als Reverse Proxy (Ports 80/443)
- Automatische HTTP→HTTPS Umleitung
- WebSocket-Support für Streamlit
- DKV-Checker nur intern erreichbar (Port 8501)

## Mehrsprachigkeit (i18n)

Unterstützte Sprachen: Deutsch (Standard), English

**Verwendung:**
```python
from i18n import SPRACHEN, t

# Übersetzung abrufen
text = t("login.benutzername", "en")  # "Username"

# Mit Platzhaltern
text = t("import.import_erfolgreich", "de", count=5, files=2)
```

**Sprachauswahl:** In der Sidebar über das Dropdown-Menü.

**Erweiterung:** Neue Strings in `i18n.py` → `TEXTE` Dictionary hinzufügen.

## Nächste mögliche Erweiterungen

- Export als Excel-Datei
- Grafische Darstellung der Auffälligkeiten auf Karte
- Vergleich mit Vorjahreswerten
- Automatische E-Mail-Benachrichtigung bei neuen Auffälligkeiten
- SMTP-Passwort verschlüsselt speichern
