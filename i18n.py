# -*- coding: utf-8 -*-
"""
Internationalisierung (i18n) für DKV Abrechnungs-Checker
Unterstützte Sprachen: Deutsch (de), Englisch (en)
"""

SPRACHEN = {
    "de": "Deutsch",
    "en": "English"
}

TEXTE = {
    "de": {
        # App-Titel
        "app_title": "DKV Abrechnungs-Checker",

        # Tabs
        "tabs": {
            "import": "Import & Analyse",
            "verbrauch": "Verbrauchsentwicklung",
            "historie": "Historie",
            "auffaelligkeiten": "Auffälligkeiten",
            "einstellungen": "Einstellungen",
            "hilfe": "Hilfe"
        },

        # Login-Bereich
        "login": {
            "benutzer": "Benutzer",
            "benutzername": "Benutzername",
            "passwort": "Passwort",
            "anmelden": "Anmelden",
            "abmelden": "Abmelden",
            "angemeldet_als": "Angemeldet als: {name}",
            "rolle": "Rolle: {rolle}",
            "ungueltige_daten": "Ungültige Anmeldedaten oder Konto deaktiviert",
            "passwort_aendern": "Passwort ändern",
            "neues_passwort": "Neues Passwort",
            "passwort_bestaetigen": "Passwort bestätigen",
            "aktuelles_passwort": "Aktuelles Passwort",
            "passwort_geaendert": "Passwort geändert!",
            "bitte_aendern": "Bitte ändern Sie Ihr Passwort!",
            "mind_6_zeichen": "Passwort muss mindestens 6 Zeichen lang sein",
            "passwort_ungleich": "Passwörter stimmen nicht überein",
            "passwort_falsch": "Aktuelles Passwort ist falsch",
            "aendern": "Ändern"
        },

        # Rollen
        "rollen": {
            "admin": "Administrator",
            "manager": "Manager",
            "viewer": "Betrachter",
            "admin_desc": "Vollzugriff auf alle Funktionen",
            "manager_desc": "Daten verwalten und E-Mails versenden",
            "viewer_desc": "Nur Lesezugriff",
            "admin_rechte": "Vollzugriff",
            "manager_rechte": "Import, Bearbeiten, E-Mails, Fahrzeuge",
            "viewer_rechte": "Nur Lesen"
        },

        # Sidebar
        "sidebar": {
            "info": "Info",
            "anmelden_info": "Melden Sie sich an, um Daten bearbeiten zu können.",
            "spende_text": "Diese Software ist kostenlos.",
            "spende_link": "Entwicklung unterstützen"
        },

        # Import-Tab
        "import": {
            "titel": "Import & Analyse",
            "upload_label": "DKV-Dateien hochladen (CSV oder PDF)",
            "upload_info": "Bitte DKV-Dateien (CSV oder PDF) hochladen, um die Analyse zu starten. Sie können mehrere Dateien gleichzeitig auswählen.",
            "bereits_importiert": "{count} Datei(en) bereits importiert",
            "werden_uebersprungen": "(werden übersprungen)",
            "alle_importiert": "Alle hochgeladenen Dateien wurden bereits importiert.",
            "neue_dateien": "{count} neue Datei(en) werden verarbeitet...",
            "rohdaten": "Rohdaten",
            "verbrauchsanalyse": "Verbrauchsanalyse pro Fahrzeug",
            "zusammenfassung": "Zusammenfassung",
            "warnungen": "Warnungen & Auffälligkeiten",
            "keine_auffaelligkeiten": "Keine Auffälligkeiten gefunden.",
            "auffaelligkeiten_gefunden": "{count} Auffälligkeit(en) gefunden!",
            "import_status": "Import-Status",
            "keine_berechtigung": "Sie haben keine Berechtigung zum Importieren. Melden Sie sich mit einem entsprechenden Konto an.",
            "neue_tankvorgaenge": "Neue Tankvorgänge",
            "dateien_importiert": "Dateien importiert",
            "duplikate_uebersprungen": "Duplikate übersprungen",
            "import_erfolgreich": "Import erfolgreich: {count} neue Tankvorgänge aus {files} Datei(en) gespeichert.",
            "alle_duplikate": "Alle Datensätze waren bereits in der Historie vorhanden (Duplikate).",
            "importierte_anzeigen": "Importierte Dateien anzeigen",
            "keine_daten_pdf": "Keine Daten aus PDF extrahiert",
            "fehler_import": "Fehler beim Import",
            "fehlender_km": "Fehlender km-Stand",
            "tankvorgang_ohne_km": "Tankvorgang ohne km-Angabe ({liter} L)"
        },

        # Manueller Tankvorgang
        "manual": {
            "titel": "Manuellen Tankvorgang erfassen",
            "expander": "Neuen Eintrag hinzufügen",
            "fahrzeug": "Fahrzeug",
            "neues_kennzeichen": "-- Neues Kennzeichen --",
            "kennzeichen_input": "Neues Kennzeichen (falls oben 'Neues Kennzeichen' gewählt)",
            "datum": "Datum",
            "uhrzeit": "Uhrzeit",
            "km_stand": "km-Stand",
            "menge": "Menge (Liter)",
            "betrag": "Betrag (EUR)",
            "tankstelle": "Tankstelle",
            "warenart": "Warenart",
            "zahlungsart": "Zahlungsart",
            "zahlungsart_privat": "Privat (Erstattung)",
            "zahlungsart_firma": "Firmenkreditkarte",
            "zahlungsart_sonstige": "Sonstige",
            "notiz": "Notiz (optional)",
            "speichern": "Tankvorgang speichern",
            "keine_berechtigung": "Melden Sie sich an, um manuelle Tankvorgänge erfassen zu können.",
            "fehler_kennzeichen": "Kennzeichen ist erforderlich",
            "fehler_menge": "Menge muss größer als 0 sein",
            "fehler_km": "km-Stand muss größer als 0 sein",
            "fehler_duplikat": "Ein Tankvorgang mit diesem Kennzeichen, Datum und Uhrzeit existiert bereits",
            "erfolg": "Tankvorgang für {kennzeichen} am {datum} gespeichert!"
        },

        # Verbrauchsentwicklung-Tab
        "verbrauch": {
            "titel": "Verbrauchsentwicklung über Zeit",
            "filter": "Filter",
            "von": "Von",
            "bis": "Bis",
            "fahrzeuge": "Fahrzeuge",
            "pro_tankvorgang": "Verbrauch pro Tankvorgang",
            "monatlich": "Monatlicher Durchschnittsverbrauch",
            "kosten": "Monatliche Kosten",
            "statistik": "Gesamtstatistik",
            "keine_daten": "Keine gültigen Verbrauchsdaten in der Historie.",
            "keine_historie": "Noch keine Daten in der Historie. Importiere zuerst eine CSV-Datei im Tab 'Import & Analyse'.",
            "fahrzeug_waehlen": "Bitte wählen Sie mindestens ein Fahrzeug aus.",
            "keine_daten_zeitraum": "Keine Daten im ausgewählten Zeitraum vorhanden.",
            # Chart-Labels
            "chart_datum": "Datum",
            "chart_verbrauch": "Verbrauch (L/100km)",
            "chart_fahrzeug": "Fahrzeug",
            "chart_monat": "Monat",
            "chart_avg_verbrauch": "Ø Verbrauch (L/100km)",
            "chart_kosten": "Kosten (EUR)",
            "chart_getankt": "Getankt (L)",
            "chart_gesamt_liter": "Gesamt Liter",
            "chart_gesamt_eur": "Gesamt EUR",
            # Statistik-Spalten
            "stat_fahrzeug": "Fahrzeug",
            "stat_avg": "Ø Verbrauch",
            "stat_min": "Min",
            "stat_max": "Max",
            "stat_liter": "Gesamt Liter",
            "stat_eur": "Gesamt EUR",
            "stat_tankvorgaenge": "Tankvorgänge"
        },

        # Historie-Tab
        "historie": {
            "titel": "Gespeicherte Daten",
            "alle_tankvorgaenge": "Alle Tankvorgänge",
            "filter_fahrzeug": "Nach Fahrzeug filtern",
            "filter_zeitraum": "Zeitraum",
            "filter_quelldatei": "Nach Quelldatei filtern",
            "alle": "Alle",
            "letzte_30": "Letzte 30 Tage",
            "letzte_90": "Letzte 90 Tage",
            "letztes_jahr": "Letztes Jahr",
            "bearbeiten_info": "Doppelklicken Sie auf eine Zelle zum Bearbeiten.",
            "keine_daten": "Keine Daten für die ausgewählten Filter gefunden.",
            "daten_verwalten": "Daten verwalten",
            "csv_export": "Historie als CSV exportieren",
            "csv_download": "CSV herunterladen",
            "historie_loeschen": "Gesamte Historie löschen",
            "bestaetigen": "Wirklich alle Daten löschen?",
            "ja_loeschen": "Ja, alles löschen!",
            "geloescht": "Historie gelöscht!",
            "importe": "Durchgeführte Importe",
            "importe_dateien": "{count} Dateien",
            "keine_daten_gespeichert": "Noch keine Daten gespeichert.",
            "aenderungen_speichern": "Änderungen speichern",
            "aenderungen_gespeichert": "{count} Änderung(en) gespeichert!",
            "keine_aenderungen": "Keine Änderungen erkannt."
        },

        # Spalten
        "spalten": {
            "status": "Status",
            "fahrzeug": "Fahrzeug",
            "kennzeichen": "Kennzeichen",
            "datum": "Datum",
            "zeit": "Zeit",
            "km_stand": "km-Stand",
            "km_gefahren": "km gefahren",
            "liter": "Liter",
            "verbrauch": "L/100km",
            "eur": "EUR",
            "tankstelle": "Tankstelle",
            "quelldatei": "Quelldatei",
            "besitzer": "Besitzer",
            "besitzer_name": "Besitzer-Name",
            "email": "E-Mail",
            "min_verbrauch": "Min L/100km",
            "max_verbrauch": "Max L/100km",
            "notizen": "Notizen",
            "problem": "Problem",
            "details": "Details",
            "quittiert": "Quittiert",
            "datei": "Datei"
        },

        # Status-Kurzformen
        "status": {
            "km_fehlt": "km?",
            "km_gesunken": "km↓",
            "verbrauch_niedrig": "L↓",
            "verbrauch_hoch": "L↑",
            "tooltip": "⚠️ = Offen, ✓ = Quittiert\n\nKurzformen:\n• km? = Fehlender km-Stand\n• km↓ = km-Stand gesunken\n• L↓ = Verbrauch zu niedrig\n• L↑ = Verbrauch zu hoch"
        },

        # Auffälligkeiten-Tab
        "auffaelligkeiten": {
            "titel": "Auffälligkeiten & Korrekturen",
            "offen": "Offen",
            "fehler": "Fehler",
            "warnungen": "Warnungen",
            "quittiert": "Quittiert",
            "uebersicht": "Übersicht aller Auffälligkeiten",
            "filter_fahrzeug": "Nach Fahrzeug filtern",
            "quittierte_ausblenden": "Quittierte ausblenden",
            "alle_quittiert": "Alle Auffälligkeiten wurden quittiert ({count} quittiert).",
            "keine_vorhanden": "Keine Auffälligkeiten vorhanden.",
            "quittieren_titel": "Auffälligkeiten quittieren",
            "quittieren_info": "Markieren Sie Auffälligkeiten als geprüft, wenn sie erklärt sind (z.B. Mietwagen getankt).",
            "auswahl": "Auffälligkeit auswählen",
            "begruendung": "Begründung (Pflichtfeld)",
            "begruendung_placeholder": "z.B. 'Mietwagen getankt', 'Tachofehler bekannt', 'Nachtank nach Panne'...",
            "begruendung_hilfe": "Bitte geben Sie eine Erklärung für die Auffälligkeit an.",
            "quittieren_button": "Auffälligkeit quittieren",
            "begruendung_fehler": "Bitte geben Sie eine Begründung ein (mindestens 3 Zeichen).",
            "quittiert_erfolg": "Auffälligkeit quittiert: {typ}",
            "keine_offenen": "Keine offenen Auffälligkeiten zum Quittieren vorhanden.",
            "korrigieren_titel": "Auffällige Einträge korrigieren",
            "korrigieren_info": "Doppelklicken Sie auf eine Zelle zum Bearbeiten. Danach 'Änderungen speichern' klicken.",
            "filter_suche": "Suche (Tankstelle, Datum...)",
            "suchbegriff_eingeben": "Suchbegriff eingeben...",
            "keine_auffaellig": "Keine auffälligen Einträge zum Bearbeiten vorhanden.",
            "keine_berechtigung_quittieren": "Sie benötigen Bearbeitungsrechte, um Auffälligkeiten quittieren zu können.",
            "keine_berechtigung_korrigieren": "Sie benötigen Bearbeitungsrechte, um Daten korrigieren zu können.",
            "benachrichtigen_titel": "Besitzer benachrichtigen",
            "smtp_nicht_konfiguriert": "SMTP-Server nicht vollständig konfiguriert. Bitte im Tab 'Einstellungen' konfigurieren.",
            "mit_email": "Fahrzeuge mit hinterlegter E-Mail-Adresse:",
            "ohne_email": "Fahrzeuge ohne E-Mail-Adresse:",
            "ohne_email_info": "Für diese Fahrzeuge kann keine E-Mail gesendet werden. Bitte im Tab 'Einstellungen' Besitzer-Daten hinterlegen.",
            "auswahl_benachrichtigen": "Fahrzeuge für Benachrichtigung auswählen:",
            "email_senden": "E-Mail-Benachrichtigungen senden",
            "smtp_konfigurieren": "Bitte zuerst SMTP-Server im Tab 'Einstellungen' konfigurieren.",
            "email_erfolg": "{count} E-Mail(s) erfolgreich gesendet!",
            "email_fehler": "Fehler beim Senden:",
            "keine_mit_auff": "Keine Fahrzeuge mit Auffälligkeiten gefunden.",
            "keine_berechtigung_email": "Sie benötigen entsprechende Rechte, um Benachrichtigungen zu versenden.",
            "keine_auffaelligkeiten": "Keine Auffälligkeiten gefunden! Alle Daten sind in Ordnung.",
            "fehlender_km": "Fehlender km-Stand",
            "km_gesunken": "km-Stand gesunken",
            "verbrauch_niedrig": "Verbrauch zu niedrig",
            "verbrauch_hoch": "Verbrauch zu hoch",
            "fahrzeug_auswaehlen": "Fahrzeug auswählen"
        },

        # Einstellungen-Tab
        "einstellungen": {
            "fahrzeuge": "Fahrzeuge",
            "email": "E-Mail",
            "benutzer": "Benutzer",
            "datensicherung": "Datensicherung",
            "ueber": "Über",

            # Fahrzeuge
            "fahrzeug_verwaltung": "Fahrzeug-Verwaltung",
            "fahrzeug_info": "Ordnen Sie Kennzeichen den jeweiligen Besitzern zu, um E-Mail-Benachrichtigungen zu ermöglichen.",
            "ohne_email_count": "{count} Fahrzeug(e) ohne E-Mail-Adresse",
            "verbrauchsgrenzen_info": "**Verbrauchsgrenzen:** Warnungen werden ausgelöst wenn der Verbrauch außerhalb des angegebenen Bereichs liegt.",
            "fahrzeug_speichern": "Fahrzeug-Daten speichern",
            "fahrzeug_gespeichert": "Fahrzeug-Daten gespeichert!",
            "keine_fahrzeuge": "Noch keine Fahrzeuge in der Historie. Importieren Sie zuerst DKV-Daten.",

            # SMTP
            "smtp_titel": "SMTP-Server",
            "server": "Server",
            "port": "Port",
            "smtp_benutzer": "Benutzername",
            "smtp_passwort": "Passwort",
            "absender_name": "Absender-Name",
            "absender_email": "Absender-E-Mail",
            "tls": "TLS verwenden",
            "verbindung_testen": "Verbindung testen",
            "speichern": "Speichern",
            "gespeichert": "Gespeichert!",
            "smtp_hilfe": "Hilfe: Gängige SMTP-Einstellungen",

            # E-Mail-Vorlage
            "vorlage_titel": "E-Mail-Vorlage",
            "vorlage_server": "Server-Einstellungen",
            "vorlage_vorlage": "Vorlage",
            "platzhalter": "Verfügbare Platzhalter",
            "betreff": "Betreff",
            "anrede": "Anrede",
            "einleitung": "Einleitung",
            "abschluss": "Abschluss",
            "fusszeile": "Fußzeile",
            "vorlage_speichern": "Vorlage speichern",
            "standard_wiederherstellen": "Standard wiederherstellen",
            "wiederhergestellt": "Wiederhergestellt!",
            "vorschau": "Vorschau",

            # Benutzer
            "uebersicht": "Übersicht",
            "bearbeiten": "Bearbeiten",
            "neu_anlegen": "Neu anlegen",
            "rollen_uebersicht": "Rollen-Übersicht",
            "benutzername": "Benutzername",
            "name": "Name",
            "email": "E-Mail",
            "passwort": "Passwort",
            "rolle": "Rolle",
            "aktiv": "Aktiv",
            "ja": "Ja",
            "nein": "Nein",
            "pw_reset": "Passwort-Änderung erzwingen",
            "neues_pw": "Neues Passwort (leer = unverändert)",
            "loeschen": "Löschen",
            "benutzer_geloescht": "Benutzer gelöscht",
            "letzter_admin": "Der letzte Administrator kann nicht gelöscht werden",
            "erstellen": "Erstellen",
            "benutzername_erforderlich": "Benutzername erforderlich",
            "passwort_min_zeichen": "Passwort mind. 6 Zeichen",
            "benutzer_erstellt": "Benutzer '{name}' erstellt!",
            "benutzername_vergeben": "Benutzername bereits vergeben",
            "mind_6_zeichen": "Passwort mind. 6 Zeichen",
            "benutzer_gespeichert": "Benutzer gespeichert!",
            "temp_pw_generieren": "Temp. Passwort generieren",
            "temp_pw_generiert": "Temporäres Passwort: **{passwort}**",
            "temp_pw_hinweis": "Teilen Sie dieses Passwort dem Benutzer mit. Bei der nächsten Anmeldung wird eine Passwortänderung erzwungen.",

            # Datensicherung
            "backup_titel": "Datensicherung & Wiederherstellung",
            "backup_erstellen": "Backup erstellen",
            "backup_info": "Erstellt eine ZIP-Datei mit allen Konfigurationsdaten:",
            "backup_button": "Backup erstellen",
            "backup_download": "{name} herunterladen",
            "backup_erfolg": "Backup erfolgreich erstellt!",
            "backup_wiederherstellen": "Backup wiederherstellen",
            "backup_warnung": "**Achtung:** Die Wiederherstellung überschreibt alle bestehenden Daten!",
            "backup_upload": "ZIP-Datei hochladen",
            "backup_bestaetigen": "Ich bestätige, dass alle bestehenden Daten überschrieben werden sollen",
            "wiederherstellen_button": "Wiederherstellen",
            "wiederherstellen_erfolg": "{meldung}",
            "wiederherstellen_info": "Bitte laden Sie die Seite neu, um die wiederhergestellten Daten zu sehen.",

            # Über
            "ueber_titel": "Über diese Software",
            "ueber_name": "DKV Abrechnungs-Checker",
            "ueber_beschreibung": "Analyse von DKV-Tankkartenabrechnungen mit automatischer Erkennung von Auffälligkeiten im Kraftstoffverbrauch.",
            "funktionen": "Funktionen:",
            "funktion_import": "Import von DKV-Abrechnungen (CSV und PDF)",
            "funktion_manual": "Manuelle Erfassung von Tankvorgängen",
            "funktion_verbrauch": "Automatische Verbrauchsberechnung",
            "funktion_anomalien": "Erkennung von Anomalien (ungewöhnlicher Verbrauch, sinkende km-Stände)",
            "funktion_email": "E-Mail-Benachrichtigung an Fahrzeughalter",
            "funktion_benutzer": "Mehrbenutzersystem mit Rollen",
            "funktion_i18n": "Mehrsprachigkeit (Deutsch/Englisch)",
            "unterstuetzen_titel": "Entwicklung unterstützen",
            "unterstuetzen_text": "Diese Software ist **kostenlos** und wird in der Freizeit entwickelt.",
            "unterstuetzen_text2": "Wenn Ihnen die Software gefällt und Sie die Weiterentwicklung unterstützen möchten, freue ich mich über eine kleine Spende:",
            "unterstuetzen_button": "Mit PayPal unterstützen",
            "datenschutz": "Datenschutz",
            "datenschutz_anzeigen": "Datenschutzhinweise anzeigen"
        },

        # Hilfe-Tab / Benutzerhandbuch
        "hilfe": {
            "titel": "Benutzerhandbuch",
            "inhaltsverzeichnis": "Inhaltsverzeichnis",
            "ueberblick": "Überblick",
            "erste_schritte": "Erste Schritte",
            "import_analyse": "Import & Analyse",
            "manueller_tankvorgang": "Manueller Tankvorgang",
            "verbrauchsentwicklung": "Verbrauchsentwicklung",
            "historie": "Historie",
            "auffaelligkeiten": "Auffälligkeiten",
            "einstellungen": "Einstellungen",
            "faq": "Häufige Fragen",
            "datenschutz": "Datenschutz & DSGVO",
            "kontakt": "Kontakt & Unterstützung",
            "support_button": "☕ Mit PayPal unterstützen",

            # Komplette Texte für jeden Abschnitt
            "ueberblick_text": """Der **DKV Abrechnungs-Checker** ist eine Anwendung zur Analyse von DKV-Tankkartenabrechnungen.
Die Software erkennt automatisch Auffälligkeiten im Kraftstoffverbrauch und hilft bei der Kontrolle der Tankkartennutzung.

**Hauptfunktionen:**
- 📤 Import von DKV-Abrechnungen (CSV und PDF)
- ✏️ Manuelle Erfassung von Tankvorgängen
- 📊 Visualisierung der Verbrauchsentwicklung
- 📚 Vollständige Historie aller Tankvorgänge
- ⚠️ Automatische Erkennung von Auffälligkeiten
- 📧 E-Mail-Benachrichtigung an Fahrzeughalter
- 👥 Mehrbenutzersystem mit Rollen
- 🌐 Mehrsprachigkeit (Deutsch/Englisch)""",

            "erste_schritte_text": """#### 1. Anmeldung
- Klicken Sie in der **Seitenleiste** auf "Anmelden"
- Standard-Zugangsdaten: `admin` / `admin`
- Beim ersten Login werden Sie aufgefordert, das Passwort zu ändern

#### 2. Benutzerrollen
| Rolle | Beschreibung |
|-------|--------------|
| **Administrator** | Vollzugriff auf alle Funktionen inkl. Benutzerverwaltung |
| **Manager** | Daten verwalten, E-Mails senden, Fahrzeuge verwalten |
| **Betrachter** | Nur Lesezugriff und Datenexport |

#### 3. Erste Daten importieren
1. Gehen Sie zum Tab "Import & Analyse"
2. Laden Sie eine DKV-Abrechnungsdatei hoch (CSV oder PDF)
3. Die Daten werden automatisch analysiert und gespeichert""",

            "import_text": """#### Unterstützte Dateiformate

**CSV-Dateien (empfohlen):**
- Direkt aus dem DKV-Portal exportiert
- Semikolon als Trennzeichen
- Deutsche Zahlenformate (1.234,56)
- Höchste Genauigkeit bei km-Ständen

**PDF-Dateien:**
- DKV E-Rechnungen
- Werden automatisch geparst
- Hinweis: km-Stände können ungenauer sein

#### Import-Ablauf
1. Dateien per Drag & Drop oder Dateiauswahl hochladen
2. Mehrere Dateien gleichzeitig möglich
3. Automatische Duplikatsprüfung
4. Neue Daten werden sofort gespeichert""",

            "manueller_tankvorgang_text": """Tankvorgänge können auch manuell erfasst werden, z.B. für:
- Tankungen an Stationen ohne DKV-Akzeptanz
- Private Tankungen mit Erstattungsanspruch
- Korrekturen fehlerhafter Importe

**Pflichtfelder:** Fahrzeug, Datum, Uhrzeit, km-Stand, Menge

Manuelle Einträge werden mit Quelldatei "MANUELL" gekennzeichnet und können nach verschiedenen Zahlungsarten kategorisiert werden.""",

            "verbrauch_text": """Dieser Tab zeigt die **grafische Auswertung** des Kraftstoffverbrauchs.

#### Filteroptionen
- **Zeitraum:** Von-Bis-Datumsauswahl
- **Fahrzeuge:** Einzelauswahl oder alle

#### Diagramme
- **Verbrauch über Zeit:** L/100km pro Tankvorgang
- **Monatlicher Durchschnitt:** Aggregiert nach Monat
- **Monatliche Kosten:** Übersicht der Tankkosten

Die Charts sind interaktiv mit Zoom und Tooltips.""",

            "historie_text": """Die **vollständige Übersicht** aller importierten Tankvorgänge.

#### Filteroptionen
- Nach Fahrzeug, Zeitraum oder Quelldatei filtern

#### Status-Symbole
- `⚠️ km?` = Fehlender Kilometerstand
- `⚠️ km↓` = Kilometerstand gesunken
- `⚠️ L↓` = Verbrauch zu niedrig
- `⚠️ L↑` = Verbrauch zu hoch
- `✓` = Quittiert (grün hinterlegt)

#### Funktionen
- **Bearbeiten:** Nach Anmeldung Daten direkt korrigieren
- **Exportieren:** Als CSV-Datei herunterladen
- **Löschen:** Gesamte Historie löschen (Admin)""",

            "auffaelligkeiten_text": """Hier werden **automatisch erkannte Probleme** angezeigt.

#### Erkannte Auffälligkeiten
| Typ | Beschreibung | Schwere |
|-----|--------------|---------|
| Fehlender km-Stand | Ohne Kilometerangabe | ⚠️ Warnung |
| km-Stand gesunken | Niedriger als vorher | 🔴 Fehler |
| Verbrauch zu niedrig | Unter Minimalwert | ⚠️ Warnung |
| Verbrauch zu hoch | Über Maximalwert | 🔴 Fehler |

#### Quittieren
1. Auffälligkeit auswählen
2. Begründung eingeben (Pflicht)
3. Klicken Sie auf "Quittieren"

Quittierte Einträge werden ausgeblendet und nicht per E-Mail gemeldet.""",

            "einstellungen_text": """#### 🚗 Fahrzeuge
- Besitzer-Name und E-Mail hinterlegen
- Individuelle Verbrauchsgrenzen pro Fahrzeug
- Notizen hinzufügen

#### 📧 E-Mail
- SMTP-Server konfigurieren
- E-Mail-Vorlage anpassen
- Verbindung testen

#### 👥 Benutzer (nur Admin)
- Benutzer anlegen, bearbeiten, löschen
- Rollen zuweisen
- Passwörter zurücksetzen

#### 💾 Datensicherung
- Backup erstellen (ZIP-Datei)
- Backup wiederherstellen""",

            "faq_text": """**F: Warum wird der Verbrauch nicht berechnet?**
> Der Verbrauch kann nur berechnet werden, wenn aktuelle UND vorherige Tankung einen gültigen km-Stand haben.

**F: Was bedeutet "km-Stand gesunken"?**
> Der aktuelle Kilometerstand ist niedriger als beim vorherigen Tankvorgang. Mögliche Ursachen: Falscher Eintrag, verschiedene Personen.

**F: Welche Verbrauchswerte sind normal?**
> PKW Benzin: 6-10 L/100km | PKW Diesel: 5-8 L/100km | Transporter: 8-15 L/100km

**F: Wie kann ich eine Auffälligkeit ignorieren?**
> Quittieren Sie sie mit einem erklärenden Kommentar. Sie wird dann ausgeblendet.

**F: Werden AdBlue-Tankungen ausgewertet?**
> Nein, nur Kraftstoffe (Diesel, Super, Benzin, Euro).""",

            "datenschutz_text": """**Wichtiger Hinweis:** Der **Betreiber** dieser Software ist der Verantwortliche im Sinne der DSGVO.

**Gespeicherte Daten:**
- Fahrzeug-Kennzeichen und Tankvorgänge
- Namen und E-Mail-Adressen
- Anmeldedaten (Passwörter werden gehasht)

**Speicherort:**
- Alle Daten werden **ausschließlich lokal** gespeichert
- Keine Übermittlung an externe Server""",

            "kontakt_text": """Bei Fragen oder Problemen wenden Sie sich an den Administrator Ihrer Organisation.

---

**Software-Version:** 1.1 (15.02.2026)
**Entwicklung:** Christian Sauer

Diese Software ist kostenlos. Wenn Sie die Weiterentwicklung unterstützen möchten:"""
        },

        # Passwort-Reset
        "passwort_reset": {
            "vergessen": "Passwort vergessen?",
            "info": "Geben Sie Ihren Benutzernamen ein. Falls eine E-Mail-Adresse hinterlegt ist, erhalten Sie ein temporäres Passwort.",
            "senden": "Zurücksetzen",
            "benutzername_fehlt": "Bitte geben Sie einen Benutzernamen ein.",
            "zu_frueh": "Bitte warten Sie einen Moment, bevor Sie erneut anfordern.",
            "email_gesendet_info": "Falls der Benutzer existiert und eine E-Mail hinterlegt ist, wurde ein temporäres Passwort versendet.",
            "smtp_nicht_konfiguriert": "E-Mail-Versand ist nicht konfiguriert. Bitte wenden Sie sich an den Administrator.",
            "betreff": "DKV Checker: Passwort zurückgesetzt",
            "titel": "Passwort zurückgesetzt",
            "anrede": "Hallo {name},",
            "text": "Ihr Passwort für den DKV Abrechnungs-Checker wurde zurückgesetzt. Ihr temporäres Passwort lautet:",
            "hinweis": "Bitte ändern Sie Ihr Passwort nach der nächsten Anmeldung.",
            "fusszeile": "Diese E-Mail wurde automatisch vom DKV Abrechnungs-Checker generiert."
        },

        # Allgemein
        "allgemein": {
            "alle": "Alle",
            "ja": "Ja",
            "nein": "Nein",
            "speichern": "Speichern",
            "abbrechen": "Abbrechen",
            "loeschen": "Löschen",
            "bearbeiten": "Bearbeiten",
            "fehler": "Fehler",
            "warnung": "Warnung",
            "erfolg": "Erfolg",
            "info": "Info",
            "gesamt": "Gesamt"
        }
    },

    # ========== ENGLISCH ==========
    "en": {
        # App-Titel
        "app_title": "DKV Invoice Checker",

        # Tabs
        "tabs": {
            "import": "Import & Analysis",
            "verbrauch": "Consumption Trends",
            "historie": "History",
            "auffaelligkeiten": "Anomalies",
            "einstellungen": "Settings",
            "hilfe": "Help"
        },

        # Login-Bereich
        "login": {
            "benutzer": "User",
            "benutzername": "Username",
            "passwort": "Password",
            "anmelden": "Login",
            "abmelden": "Logout",
            "angemeldet_als": "Logged in as: {name}",
            "rolle": "Role: {rolle}",
            "ungueltige_daten": "Invalid credentials or account disabled",
            "passwort_aendern": "Change password",
            "neues_passwort": "New password",
            "passwort_bestaetigen": "Confirm password",
            "aktuelles_passwort": "Current password",
            "passwort_geaendert": "Password changed!",
            "bitte_aendern": "Please change your password!",
            "mind_6_zeichen": "Password must be at least 6 characters",
            "passwort_ungleich": "Passwords do not match",
            "passwort_falsch": "Current password is incorrect",
            "aendern": "Change"
        },

        # Rollen
        "rollen": {
            "admin": "Administrator",
            "manager": "Manager",
            "viewer": "Viewer",
            "admin_desc": "Full access to all features",
            "manager_desc": "Manage data and send emails",
            "viewer_desc": "Read-only access",
            "admin_rechte": "Full access",
            "manager_rechte": "Import, Edit, Emails, Vehicles",
            "viewer_rechte": "Read only"
        },

        # Sidebar
        "sidebar": {
            "info": "Info",
            "anmelden_info": "Please log in to edit data.",
            "spende_text": "This software is free.",
            "spende_link": "Support development"
        },

        # Import-Tab
        "import": {
            "titel": "Import & Analysis",
            "upload_label": "Upload DKV files (CSV or PDF)",
            "upload_info": "Please upload DKV files (CSV or PDF) to start the analysis. You can select multiple files at once.",
            "bereits_importiert": "{count} file(s) already imported",
            "werden_uebersprungen": "(will be skipped)",
            "alle_importiert": "All uploaded files have already been imported.",
            "neue_dateien": "{count} new file(s) being processed...",
            "rohdaten": "Raw data",
            "verbrauchsanalyse": "Consumption analysis per vehicle",
            "zusammenfassung": "Summary",
            "warnungen": "Warnings & Anomalies",
            "keine_auffaelligkeiten": "No anomalies found.",
            "auffaelligkeiten_gefunden": "{count} anomaly(ies) found!",
            "import_status": "Import status",
            "keine_berechtigung": "You don't have permission to import. Please log in with an appropriate account.",
            "neue_tankvorgaenge": "New refueling entries",
            "dateien_importiert": "Files imported",
            "duplikate_uebersprungen": "Duplicates skipped",
            "import_erfolgreich": "Import successful: {count} new refueling entries from {files} file(s) saved.",
            "alle_duplikate": "All records were already in history (duplicates).",
            "importierte_anzeigen": "Show imported files",
            "keine_daten_pdf": "No data extracted from PDF",
            "fehler_import": "Import error",
            "fehlender_km": "Missing odometer",
            "tankvorgang_ohne_km": "Refueling without odometer reading ({liter} L)"
        },

        # Manueller Tankvorgang
        "manual": {
            "titel": "Add Manual Refueling Entry",
            "expander": "Add new entry",
            "fahrzeug": "Vehicle",
            "neues_kennzeichen": "-- New license plate --",
            "kennzeichen_input": "New license plate (if 'New license plate' selected above)",
            "datum": "Date",
            "uhrzeit": "Time",
            "km_stand": "Odometer",
            "menge": "Amount (liters)",
            "betrag": "Amount (EUR)",
            "tankstelle": "Gas station",
            "warenart": "Fuel type",
            "zahlungsart": "Payment method",
            "zahlungsart_privat": "Private (reimbursement)",
            "zahlungsart_firma": "Company credit card",
            "zahlungsart_sonstige": "Other",
            "notiz": "Note (optional)",
            "speichern": "Save refueling entry",
            "keine_berechtigung": "Please log in to add manual refueling entries.",
            "fehler_kennzeichen": "License plate is required",
            "fehler_menge": "Amount must be greater than 0",
            "fehler_km": "Odometer must be greater than 0",
            "fehler_duplikat": "A refueling entry with this license plate, date and time already exists",
            "erfolg": "Refueling entry for {kennzeichen} on {datum} saved!"
        },

        # Verbrauchsentwicklung-Tab
        "verbrauch": {
            "titel": "Consumption Trends Over Time",
            "filter": "Filter",
            "von": "From",
            "bis": "To",
            "fahrzeuge": "Vehicles",
            "pro_tankvorgang": "Consumption per refueling",
            "monatlich": "Monthly average consumption",
            "kosten": "Monthly costs",
            "statistik": "Overall statistics",
            "keine_daten": "No valid consumption data in history.",
            "keine_historie": "No data in history yet. First import a CSV file in the 'Import & Analysis' tab.",
            "fahrzeug_waehlen": "Please select at least one vehicle.",
            "keine_daten_zeitraum": "No data available for the selected period.",
            # Chart-Labels
            "chart_datum": "Date",
            "chart_verbrauch": "Consumption (L/100km)",
            "chart_fahrzeug": "Vehicle",
            "chart_monat": "Month",
            "chart_avg_verbrauch": "Avg. Consumption (L/100km)",
            "chart_kosten": "Costs (EUR)",
            "chart_getankt": "Refueled (L)",
            "chart_gesamt_liter": "Total Liters",
            "chart_gesamt_eur": "Total EUR",
            # Statistik-Spalten
            "stat_fahrzeug": "Vehicle",
            "stat_avg": "Avg. Consumption",
            "stat_min": "Min",
            "stat_max": "Max",
            "stat_liter": "Total Liters",
            "stat_eur": "Total EUR",
            "stat_tankvorgaenge": "Refuelings"
        },

        # Historie-Tab
        "historie": {
            "titel": "Stored Data",
            "alle_tankvorgaenge": "All refueling entries",
            "filter_fahrzeug": "Filter by vehicle",
            "filter_zeitraum": "Time period",
            "filter_quelldatei": "Filter by source file",
            "alle": "All",
            "letzte_30": "Last 30 days",
            "letzte_90": "Last 90 days",
            "letztes_jahr": "Last year",
            "bearbeiten_info": "Double-click on a cell to edit.",
            "keine_daten": "No data found for selected filters.",
            "daten_verwalten": "Manage data",
            "csv_export": "Export history as CSV",
            "csv_download": "Download CSV",
            "historie_loeschen": "Delete entire history",
            "bestaetigen": "Really delete all data?",
            "ja_loeschen": "Yes, delete everything!",
            "geloescht": "History deleted!",
            "importe": "Completed imports",
            "importe_dateien": "{count} files",
            "keine_daten_gespeichert": "No data stored yet.",
            "aenderungen_speichern": "Save changes",
            "aenderungen_gespeichert": "{count} change(s) saved!",
            "keine_aenderungen": "No changes detected."
        },

        # Spalten
        "spalten": {
            "status": "Status",
            "fahrzeug": "Vehicle",
            "kennzeichen": "License plate",
            "datum": "Date",
            "zeit": "Time",
            "km_stand": "Odometer",
            "km_gefahren": "km driven",
            "liter": "Liters",
            "verbrauch": "L/100km",
            "eur": "EUR",
            "tankstelle": "Gas station",
            "quelldatei": "Source file",
            "besitzer": "Owner",
            "besitzer_name": "Owner name",
            "email": "Email",
            "min_verbrauch": "Min L/100km",
            "max_verbrauch": "Max L/100km",
            "notizen": "Notes",
            "problem": "Problem",
            "details": "Details",
            "quittiert": "Acknowledged",
            "datei": "File"
        },

        # Status-Kurzformen
        "status": {
            "km_fehlt": "km?",
            "km_gesunken": "km↓",
            "verbrauch_niedrig": "L↓",
            "verbrauch_hoch": "L↑",
            "tooltip": "⚠️ = Open, ✓ = Acknowledged\n\nShort forms:\n• km? = Missing odometer\n• km↓ = Odometer decreased\n• L↓ = Consumption too low\n• L↑ = Consumption too high"
        },

        # Auffälligkeiten-Tab
        "auffaelligkeiten": {
            "titel": "Anomalies & Corrections",
            "offen": "Open",
            "fehler": "Errors",
            "warnungen": "Warnings",
            "quittiert": "Acknowledged",
            "uebersicht": "Overview of all anomalies",
            "filter_fahrzeug": "Filter by vehicle",
            "quittierte_ausblenden": "Hide acknowledged",
            "alle_quittiert": "All anomalies have been acknowledged ({count} acknowledged).",
            "keine_vorhanden": "No anomalies present.",
            "quittieren_titel": "Acknowledge anomalies",
            "quittieren_info": "Mark anomalies as reviewed when they have been explained (e.g., rental car refueled).",
            "auswahl": "Select anomaly",
            "begruendung": "Reason (required)",
            "begruendung_placeholder": "e.g., 'Rental car refueled', 'Known odometer error', 'Refuel after breakdown'...",
            "begruendung_hilfe": "Please provide an explanation for the anomaly.",
            "quittieren_button": "Acknowledge anomaly",
            "begruendung_fehler": "Please provide a reason (at least 3 characters).",
            "quittiert_erfolg": "Anomaly acknowledged: {typ}",
            "keine_offenen": "No open anomalies to acknowledge.",
            "korrigieren_titel": "Correct anomalous entries",
            "korrigieren_info": "Double-click on a cell to edit. Then click 'Save changes'.",
            "filter_suche": "Search (gas station, date...)",
            "suchbegriff_eingeben": "Enter search term...",
            "keine_auffaellig": "No anomalous entries to edit.",
            "keine_berechtigung_quittieren": "You need edit permissions to acknowledge anomalies.",
            "keine_berechtigung_korrigieren": "You need edit permissions to correct data.",
            "benachrichtigen_titel": "Notify owners",
            "smtp_nicht_konfiguriert": "SMTP server not fully configured. Please configure in 'Settings' tab.",
            "mit_email": "Vehicles with email address on file:",
            "ohne_email": "Vehicles without email address:",
            "ohne_email_info": "No email can be sent for these vehicles. Please add owner data in the 'Settings' tab.",
            "auswahl_benachrichtigen": "Select vehicles for notification:",
            "email_senden": "Send email notifications",
            "smtp_konfigurieren": "Please configure SMTP server in 'Settings' tab first.",
            "email_erfolg": "{count} email(s) sent successfully!",
            "email_fehler": "Error sending:",
            "keine_mit_auff": "No vehicles with anomalies found.",
            "keine_berechtigung_email": "You need appropriate permissions to send notifications.",
            "keine_auffaelligkeiten": "No anomalies found! All data is in order.",
            "fehlender_km": "Missing odometer",
            "km_gesunken": "Odometer decreased",
            "verbrauch_niedrig": "Consumption too low",
            "verbrauch_hoch": "Consumption too high",
            "fahrzeug_auswaehlen": "Select vehicle"
        },

        # Einstellungen-Tab
        "einstellungen": {
            "fahrzeuge": "Vehicles",
            "email": "Email",
            "benutzer": "Users",
            "datensicherung": "Backup",
            "ueber": "About",

            # Fahrzeuge
            "fahrzeug_verwaltung": "Vehicle Management",
            "fahrzeug_info": "Assign license plates to their owners to enable email notifications.",
            "ohne_email_count": "{count} vehicle(s) without email address",
            "verbrauchsgrenzen_info": "**Consumption limits:** Warnings are triggered when consumption is outside the specified range.",
            "fahrzeug_speichern": "Save vehicle data",
            "fahrzeug_gespeichert": "Vehicle data saved!",
            "keine_fahrzeuge": "No vehicles in history yet. Import DKV data first.",

            # SMTP
            "smtp_titel": "SMTP Server",
            "server": "Server",
            "port": "Port",
            "smtp_benutzer": "Username",
            "smtp_passwort": "Password",
            "absender_name": "Sender name",
            "absender_email": "Sender email",
            "tls": "Use TLS",
            "verbindung_testen": "Test connection",
            "speichern": "Save",
            "gespeichert": "Saved!",
            "smtp_hilfe": "Help: Common SMTP settings",

            # E-Mail-Vorlage
            "vorlage_titel": "Email Template",
            "vorlage_server": "Server Settings",
            "vorlage_vorlage": "Template",
            "platzhalter": "Available placeholders",
            "betreff": "Subject",
            "anrede": "Greeting",
            "einleitung": "Introduction",
            "abschluss": "Closing",
            "fusszeile": "Footer",
            "vorlage_speichern": "Save template",
            "standard_wiederherstellen": "Restore default",
            "wiederhergestellt": "Restored!",
            "vorschau": "Preview",

            # Benutzer
            "uebersicht": "Overview",
            "bearbeiten": "Edit",
            "neu_anlegen": "Create new",
            "rollen_uebersicht": "Roles overview",
            "benutzername": "Username",
            "name": "Name",
            "email": "Email",
            "passwort": "Password",
            "rolle": "Role",
            "aktiv": "Active",
            "ja": "Yes",
            "nein": "No",
            "pw_reset": "Force password change",
            "neues_pw": "New password (empty = unchanged)",
            "loeschen": "Delete",
            "benutzer_geloescht": "User deleted",
            "letzter_admin": "The last administrator cannot be deleted",
            "erstellen": "Create",
            "benutzername_erforderlich": "Username required",
            "passwort_min_zeichen": "Password min. 6 characters",
            "benutzer_erstellt": "User '{name}' created!",
            "benutzername_vergeben": "Username already taken",
            "mind_6_zeichen": "Password min. 6 characters",
            "benutzer_gespeichert": "User saved!",
            "temp_pw_generieren": "Generate temp. password",
            "temp_pw_generiert": "Temporary password: **{passwort}**",
            "temp_pw_hinweis": "Share this password with the user. A password change will be enforced on next login.",

            # Datensicherung
            "backup_titel": "Backup & Restore",
            "backup_erstellen": "Create backup",
            "backup_info": "Creates a ZIP file with all configuration data:",
            "backup_button": "Create backup",
            "backup_download": "Download {name}",
            "backup_erfolg": "Backup created successfully!",
            "backup_wiederherstellen": "Restore backup",
            "backup_warnung": "**Warning:** Restoring will overwrite all existing data!",
            "backup_upload": "Upload ZIP file",
            "backup_bestaetigen": "I confirm that all existing data should be overwritten",
            "wiederherstellen_button": "Restore",
            "wiederherstellen_erfolg": "{meldung}",
            "wiederherstellen_info": "Please reload the page to see the restored data.",

            # Über
            "ueber_titel": "About this software",
            "ueber_name": "DKV Invoice Checker",
            "ueber_beschreibung": "Analysis of DKV fuel card invoices with automatic detection of consumption anomalies.",
            "funktionen": "Features:",
            "funktion_import": "Import DKV invoices (CSV and PDF)",
            "funktion_manual": "Manual entry of refueling records",
            "funktion_verbrauch": "Automatic consumption calculation",
            "funktion_anomalien": "Detection of anomalies (unusual consumption, decreasing odometer)",
            "funktion_email": "Email notification to vehicle owners",
            "funktion_benutzer": "Multi-user system with roles",
            "funktion_i18n": "Multi-language support (German/English)",
            "unterstuetzen_titel": "Support development",
            "unterstuetzen_text": "This software is **free** and developed in spare time.",
            "unterstuetzen_text2": "If you like the software and want to support its development, I appreciate a small donation:",
            "unterstuetzen_button": "Support via PayPal",
            "datenschutz": "Privacy",
            "datenschutz_anzeigen": "Show privacy notice"
        },

        # Hilfe-Tab / Benutzerhandbuch
        "hilfe": {
            "titel": "User Manual",
            "inhaltsverzeichnis": "Table of Contents",
            "ueberblick": "Overview",
            "erste_schritte": "Getting Started",
            "import_analyse": "Import & Analysis",
            "manueller_tankvorgang": "Manual Refueling Entry",
            "verbrauchsentwicklung": "Consumption Trends",
            "historie": "History",
            "auffaelligkeiten": "Anomalies",
            "einstellungen": "Settings",
            "faq": "FAQ",
            "datenschutz": "Privacy & GDPR",
            "kontakt": "Contact & Support",
            "support_button": "☕ Support via PayPal",

            # Complete texts for each section
            "ueberblick_text": """The **DKV Invoice Checker** is an application for analyzing DKV fuel card invoices.
The software automatically detects consumption anomalies and helps control fuel card usage.

**Main features:**
- 📤 Import DKV invoices (CSV and PDF)
- ✏️ Manual entry of refueling records
- 📊 Visualization of consumption trends
- 📚 Complete history of all refueling entries
- ⚠️ Automatic detection of anomalies
- 📧 Email notification to vehicle owners
- 👥 Multi-user system with roles
- 🌐 Multi-language support (German/English)""",

            "erste_schritte_text": """#### 1. Login
- Click "Login" in the **sidebar**
- Default credentials: `admin` / `admin`
- On first login, you will be asked to change your password

#### 2. User Roles
| Role | Description |
|------|-------------|
| **Administrator** | Full access to all features including user management |
| **Manager** | Manage data, send emails, manage vehicles |
| **Viewer** | Read-only access and data export |

#### 3. Import First Data
1. Go to the "Import & Analysis" tab
2. Upload a DKV invoice file (CSV or PDF)
3. Data will be automatically analyzed and saved""",

            "import_text": """#### Supported File Formats

**CSV files (recommended):**
- Directly exported from the DKV portal
- Semicolon as delimiter
- German number formats (1,234.56)
- Highest accuracy for odometer readings

**PDF files:**
- DKV e-invoices
- Automatically parsed
- Note: Odometer readings may be less accurate

#### Import Process
1. Upload files via drag & drop or file selection
2. Multiple files can be uploaded at once
3. Automatic duplicate detection
4. New data is saved immediately""",

            "manueller_tankvorgang_text": """Refueling entries can also be added manually, e.g., for:
- Refueling at stations without DKV acceptance
- Private refueling with reimbursement claim
- Corrections of erroneous imports

**Required fields:** Vehicle, date, time, odometer, amount

Manual entries are marked with source file "MANUAL" and can be categorized by payment method.""",

            "verbrauch_text": """This tab shows the **graphical analysis** of fuel consumption.

#### Filter Options
- **Time period:** From-To date selection
- **Vehicles:** Single selection or all

#### Charts
- **Consumption over time:** L/100km per refueling
- **Monthly average:** Aggregated by month
- **Monthly costs:** Overview of fuel costs

The charts are interactive with zoom and tooltips.""",

            "historie_text": """The **complete overview** of all imported refueling entries.

#### Filter Options
- Filter by vehicle, time period, or source file

#### Status Symbols
- `⚠️ km?` = Missing odometer reading
- `⚠️ km↓` = Odometer decreased
- `⚠️ L↓` = Consumption too low
- `⚠️ L↑` = Consumption too high
- `✓` = Acknowledged (green background)

#### Functions
- **Edit:** After login, correct data directly
- **Export:** Download as CSV file
- **Delete:** Delete entire history (admin only)""",

            "auffaelligkeiten_text": """Here, **automatically detected problems** are displayed.

#### Detected Anomalies
| Type | Description | Severity |
|------|-------------|----------|
| Missing odometer | Without odometer reading | ⚠️ Warning |
| Odometer decreased | Lower than before | 🔴 Error |
| Consumption too low | Below minimum value | ⚠️ Warning |
| Consumption too high | Above maximum value | 🔴 Error |

#### Acknowledge
1. Select anomaly
2. Enter reason (required)
3. Click "Acknowledge"

Acknowledged entries are hidden and not reported via email.""",

            "einstellungen_text": """#### 🚗 Vehicles
- Enter owner name and email
- Individual consumption limits per vehicle
- Add notes

#### 📧 Email
- Configure SMTP server
- Customize email template
- Test connection

#### 👥 Users (admin only)
- Create, edit, delete users
- Assign roles
- Reset passwords

#### 💾 Backup
- Create backup (ZIP file)
- Restore backup""",

            "faq_text": """**Q: Why is consumption not calculated?**
> Consumption can only be calculated when both current AND previous refueling have a valid odometer reading.

**Q: What does "odometer decreased" mean?**
> The current odometer is lower than at the previous refueling. Possible causes: Wrong entry, different people.

**Q: What consumption values are normal?**
> Gasoline car: 6-10 L/100km | Diesel car: 5-8 L/100km | Van: 8-15 L/100km

**Q: How can I ignore an anomaly?**
> Acknowledge it with an explanatory comment. It will then be hidden.

**Q: Are AdBlue refuelings analyzed?**
> No, only fuels (Diesel, Super, Gasoline, Euro).""",

            "datenschutz_text": """**Important note:** The **operator** of this software is the responsible party under GDPR.

**Stored data:**
- Vehicle license plates and refueling records
- Names and email addresses
- Login data (passwords are hashed)

**Storage location:**
- All data is stored **exclusively locally**
- No transmission to external servers""",

            "kontakt_text": """For questions or problems, contact your organization's administrator.

---

**Software version:** 1.1 (2026-02-15)
**Development:** Christian Sauer

This software is free. If you would like to support further development:"""
        },

        # Passwort-Reset
        "passwort_reset": {
            "vergessen": "Forgot password?",
            "info": "Enter your username. If an email address is on file, you will receive a temporary password.",
            "senden": "Reset",
            "benutzername_fehlt": "Please enter a username.",
            "zu_frueh": "Please wait a moment before requesting again.",
            "email_gesendet_info": "If the user exists and an email is on file, a temporary password has been sent.",
            "smtp_nicht_konfiguriert": "Email sending is not configured. Please contact the administrator.",
            "betreff": "DKV Checker: Password Reset",
            "titel": "Password Reset",
            "anrede": "Hello {name},",
            "text": "Your password for the DKV Invoice Checker has been reset. Your temporary password is:",
            "hinweis": "Please change your password after your next login.",
            "fusszeile": "This email was automatically generated by the DKV Invoice Checker."
        },

        # Allgemein
        "allgemein": {
            "alle": "All",
            "ja": "Yes",
            "nein": "No",
            "speichern": "Save",
            "abbrechen": "Cancel",
            "loeschen": "Delete",
            "bearbeiten": "Edit",
            "fehler": "Error",
            "warnung": "Warning",
            "erfolg": "Success",
            "info": "Info",
            "gesamt": "Total"
        }
    }
}


def t(key, lang="de", **kwargs):
    """
    Übersetzungsfunktion mit Platzhalter-Support.

    Args:
        key: Verschachtelter Schlüssel, getrennt durch Punkte (z.B. "login.benutzername")
        lang: Sprach-Code ("de" oder "en")
        **kwargs: Platzhalter-Werte für String-Formatierung

    Returns:
        Übersetzter Text oder der Schlüssel falls nicht gefunden
    """
    keys = key.split(".")
    text = TEXTE.get(lang, TEXTE["de"])

    for k in keys:
        if isinstance(text, dict):
            text = text.get(k)
            if text is None:
                # Fallback auf Deutsch
                text = TEXTE["de"]
                for fallback_k in keys:
                    if isinstance(text, dict):
                        text = text.get(fallback_k)
                        if text is None:
                            return key
                    else:
                        return key
                break
        else:
            return key

    if not isinstance(text, str):
        return key

    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass

    return text
