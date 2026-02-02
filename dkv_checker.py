import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import altair as alt
import json
import os
import re
import hashlib
import secrets
import pdfplumber
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from io import StringIO, BytesIO
from datetime import datetime
import zipfile

# Konfiguration
st.set_page_config(page_title="DKV Abrechnungs-Checker", layout="wide")

# Datenverzeichnis (Standard: Projektverzeichnis, überschreibbar via Umgebungsvariable)
DATA_DIR = os.environ.get("DKV_DATA_DIR", os.path.dirname(__file__))
HISTORIE_DATEI = os.path.join(DATA_DIR, "historie.json")
FAHRZEUGE_DATEI = os.path.join(DATA_DIR, "fahrzeuge.json")
SMTP_CONFIG_DATEI = os.path.join(DATA_DIR, "smtp_config.json")
EMAIL_VORLAGE_DATEI = os.path.join(DATA_DIR, "email_vorlage.json")
BENUTZER_DATEI = os.path.join(DATA_DIR, "benutzer.json")

# Rollen und ihre Rechte
ROLLEN = {
    "admin": {
        "name": "Administrator",
        "beschreibung": "Vollzugriff auf alle Funktionen",
        "rechte": ["ansehen", "exportieren", "importieren", "bearbeiten", "email_senden",
                   "fahrzeuge_verwalten", "historie_loeschen", "smtp_config", "vorlage_config", "benutzer_verwalten", "datensicherung"]
    },
    "manager": {
        "name": "Manager",
        "beschreibung": "Daten verwalten und E-Mails versenden",
        "rechte": ["ansehen", "exportieren", "importieren", "bearbeiten", "email_senden", "fahrzeuge_verwalten"]
    },
    "viewer": {
        "name": "Betrachter",
        "beschreibung": "Nur Lesezugriff",
        "rechte": ["ansehen", "exportieren"]
    }
}

# Standard E-Mail-Vorlage
DEFAULT_EMAIL_VORLAGE = {
    "betreff": "DKV Checker: {anzahl_gesamt} Auffälligkeit(en) für {kennzeichen}",
    "anrede": "Hallo {besitzer_name},",
    "einleitung": "für Ihr Fahrzeug <strong>{kennzeichen}</strong> wurden folgende Auffälligkeiten festgestellt:",
    "abschluss": "Bitte überprüfen und korrigieren Sie die betroffenen Tankvorgänge.",
    "fusszeile": "Diese E-Mail wurde automatisch vom DKV Abrechnungs-Checker generiert."
}

# --- Session State initialisieren ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "user_rolle" not in st.session_state:
    st.session_state["user_rolle"] = ""
if "user_name" not in st.session_state:
    st.session_state["user_name"] = ""
if "muss_passwort_aendern" not in st.session_state:
    st.session_state["muss_passwort_aendern"] = False
if "aktiver_tab" not in st.session_state:
    st.session_state["aktiver_tab"] = None

def aktueller_benutzer_hat_recht(recht):
    """Prüft ob der aktuell eingeloggte Benutzer ein bestimmtes Recht hat"""
    if not st.session_state["logged_in"]:
        return False
    return hat_recht(st.session_state["user_rolle"], recht)

# --- Hilfsfunktionen ---

def parse_german_number(value):
    """Deutsche Zahlen umwandeln (1.234,56 -> 1234.56)"""
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    value = str(value).strip()
    value = value.replace(".", "").replace(",", ".")
    try:
        return float(value)
    except:
        return None

def lade_historie():
    """Historie aus JSON laden"""
    if os.path.exists(HISTORIE_DATEI):
        with open(HISTORIE_DATEI, "r", encoding="utf-8") as f:
            historie = json.load(f)
            # Sicherstellen dass alle Felder existieren
            for t in historie.get("tankvorgaenge", []):
                if "km_differenz" not in t:
                    t["km_differenz"] = None
                if "verbrauch" not in t:
                    t["verbrauch"] = None
                if "quelldatei" not in t:
                    t["quelldatei"] = ""  # Ältere Einträge ohne Quelldatei
                # Quittierungs-Felder
                if "quittiert" not in t:
                    t["quittiert"] = False
                if "quittiert_kommentar" not in t:
                    t["quittiert_kommentar"] = ""
                if "quittiert_von" not in t:
                    t["quittiert_von"] = ""
                if "quittiert_am" not in t:
                    t["quittiert_am"] = ""
            return historie
    return {"tankvorgaenge": [], "importe": []}

def speichere_historie(historie, neu_berechnen=True):
    """Historie in JSON speichern, optional Verbrauch neu berechnen"""
    if neu_berechnen and historie["tankvorgaenge"]:
        historie = berechne_verbrauch_historie(historie)
    with open(HISTORIE_DATEI, "w", encoding="utf-8") as f:
        json.dump(historie, f, ensure_ascii=False, indent=2)

def lade_fahrzeuge():
    """Fahrzeug-Besitzer-Zuordnung aus JSON laden"""
    if os.path.exists(FAHRZEUGE_DATEI):
        with open(FAHRZEUGE_DATEI, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"fahrzeuge": []}

def speichere_fahrzeuge(fahrzeuge):
    """Fahrzeug-Besitzer-Zuordnung in JSON speichern"""
    with open(FAHRZEUGE_DATEI, "w", encoding="utf-8") as f:
        json.dump(fahrzeuge, f, ensure_ascii=False, indent=2)

def lade_smtp_config():
    """SMTP-Konfiguration aus JSON laden"""
    if os.path.exists(SMTP_CONFIG_DATEI):
        with open(SMTP_CONFIG_DATEI, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "server": "",
        "port": 587,
        "benutzer": "",
        "passwort": "",
        "absender_name": "DKV Checker",
        "absender_email": "",
        "tls": True
    }

def speichere_smtp_config(config):
    """SMTP-Konfiguration in JSON speichern"""
    with open(SMTP_CONFIG_DATEI, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def lade_email_vorlage():
    """E-Mail-Vorlage aus JSON laden"""
    if os.path.exists(EMAIL_VORLAGE_DATEI):
        with open(EMAIL_VORLAGE_DATEI, "r", encoding="utf-8") as f:
            vorlage = json.load(f)
            # Fehlende Felder mit Defaults ergänzen
            for key, value in DEFAULT_EMAIL_VORLAGE.items():
                if key not in vorlage:
                    vorlage[key] = value
            return vorlage
    return DEFAULT_EMAIL_VORLAGE.copy()

def speichere_email_vorlage(vorlage):
    """E-Mail-Vorlage in JSON speichern"""
    with open(EMAIL_VORLAGE_DATEI, "w", encoding="utf-8") as f:
        json.dump(vorlage, f, ensure_ascii=False, indent=2)

# --- Datensicherung ---
BACKUP_DATEIEN = {
    "historie.json": HISTORIE_DATEI,
    "fahrzeuge.json": FAHRZEUGE_DATEI,
    "smtp_config.json": SMTP_CONFIG_DATEI,
    "email_vorlage.json": EMAIL_VORLAGE_DATEI,
    "benutzer.json": BENUTZER_DATEI
}

def erstelle_backup():
    """Erstellt ZIP-Datei mit allen Konfigurationsdateien"""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for dateiname, dateipfad in BACKUP_DATEIEN.items():
            if os.path.exists(dateipfad):
                with open(dateipfad, "r", encoding="utf-8") as f:
                    zf.writestr(dateiname, f.read())

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_name = f"dkv_backup_{timestamp}.zip"
    return zip_buffer.getvalue(), backup_name

def stelle_backup_wieder_her(zip_bytes):
    """Stellt Backup aus ZIP-Datei wieder her"""
    try:
        zip_buffer = BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            # Prüfen welche Dateien im ZIP vorhanden sind
            zip_dateien = zf.namelist()
            gefundene_dateien = []

            # JSON-Struktur validieren
            for dateiname in zip_dateien:
                if dateiname in BACKUP_DATEIEN:
                    try:
                        inhalt = zf.read(dateiname).decode("utf-8")
                        json.loads(inhalt)  # Validierung
                        gefundene_dateien.append(dateiname)
                    except json.JSONDecodeError:
                        return False, f"Ungültige JSON-Struktur in '{dateiname}'"

            if not gefundene_dateien:
                return False, "Keine gültigen Backup-Dateien im ZIP gefunden"

            # Dateien extrahieren und speichern
            for dateiname in gefundene_dateien:
                inhalt = zf.read(dateiname).decode("utf-8")
                dateipfad = BACKUP_DATEIEN[dateiname]
                with open(dateipfad, "w", encoding="utf-8") as f:
                    f.write(inhalt)

            return True, f"{len(gefundene_dateien)} Datei(en) wiederhergestellt: {', '.join(gefundene_dateien)}"

    except zipfile.BadZipFile:
        return False, "Ungültige ZIP-Datei"
    except Exception as e:
        return False, f"Fehler beim Wiederherstellen: {str(e)}"

# --- Passwort-Hashing ---
def hash_passwort(passwort, salt=None):
    """Erstellt einen sicheren Hash des Passworts mit PBKDF2"""
    if salt is None:
        salt = secrets.token_hex(32)
    # PBKDF2 mit SHA-256, 100.000 Iterationen
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',
        passwort.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${pw_hash}"

def pruefe_passwort(passwort, gespeicherter_hash):
    """Prüft ob das Passwort mit dem gespeicherten Hash übereinstimmt"""
    if '$' not in gespeicherter_hash:
        return False
    salt, _ = gespeicherter_hash.split('$', 1)
    return hash_passwort(passwort, salt) == gespeicherter_hash

# --- Benutzerverwaltung ---
def lade_benutzer():
    """Benutzer aus JSON laden, erstellt Standard-Admin falls nicht vorhanden"""
    if os.path.exists(BENUTZER_DATEI):
        with open(BENUTZER_DATEI, "r", encoding="utf-8") as f:
            return json.load(f)

    # Standard-Admin erstellen beim ersten Start
    standard_benutzer = {
        "benutzer": [
            {
                "benutzername": "admin",
                "passwort_hash": hash_passwort("admin"),
                "rolle": "admin",
                "name": "Administrator",
                "email": "",
                "aktiv": True,
                "muss_passwort_aendern": True  # Erzwingt Passwortänderung beim ersten Login
            }
        ]
    }
    speichere_benutzer(standard_benutzer)
    return standard_benutzer

def speichere_benutzer(benutzer_daten):
    """Benutzer in JSON speichern"""
    with open(BENUTZER_DATEI, "w", encoding="utf-8") as f:
        json.dump(benutzer_daten, f, ensure_ascii=False, indent=2)

def finde_benutzer(benutzername):
    """Findet einen Benutzer anhand des Benutzernamens"""
    benutzer_daten = lade_benutzer()
    for b in benutzer_daten.get("benutzer", []):
        if b["benutzername"].lower() == benutzername.lower():
            return b
    return None

def authentifiziere_benutzer(benutzername, passwort):
    """Prüft Login-Daten und gibt Benutzer-Objekt oder None zurück"""
    benutzer = finde_benutzer(benutzername)
    if benutzer and benutzer.get("aktiv", True):
        if pruefe_passwort(passwort, benutzer.get("passwort_hash", "")):
            return benutzer
    return None

def hat_recht(rolle, recht):
    """Prüft ob eine Rolle ein bestimmtes Recht hat"""
    if rolle not in ROLLEN:
        return False
    return recht in ROLLEN[rolle].get("rechte", [])

def aktualisiere_benutzer(benutzername, updates):
    """Aktualisiert einen Benutzer mit den angegebenen Feldern"""
    benutzer_daten = lade_benutzer()
    for i, b in enumerate(benutzer_daten.get("benutzer", [])):
        if b["benutzername"].lower() == benutzername.lower():
            benutzer_daten["benutzer"][i].update(updates)
            speichere_benutzer(benutzer_daten)
            return True
    return False

def erstelle_benutzer(benutzername, passwort, rolle, name="", email=""):
    """Erstellt einen neuen Benutzer"""
    benutzer_daten = lade_benutzer()

    # Prüfen ob Benutzername bereits existiert
    if finde_benutzer(benutzername):
        return False, "Benutzername bereits vergeben"

    neuer_benutzer = {
        "benutzername": benutzername,
        "passwort_hash": hash_passwort(passwort),
        "rolle": rolle,
        "name": name,
        "email": email,
        "aktiv": True,
        "muss_passwort_aendern": True
    }
    benutzer_daten["benutzer"].append(neuer_benutzer)
    speichere_benutzer(benutzer_daten)
    return True, "Benutzer erstellt"

def loesche_benutzer(benutzername):
    """Löscht einen Benutzer (außer den letzten Admin)"""
    benutzer_daten = lade_benutzer()

    # Zähle aktive Admins
    admins = [b for b in benutzer_daten["benutzer"] if b["rolle"] == "admin" and b["aktiv"]]
    benutzer = finde_benutzer(benutzername)

    if benutzer and benutzer["rolle"] == "admin" and len(admins) <= 1:
        return False, "Der letzte Administrator kann nicht gelöscht werden"

    benutzer_daten["benutzer"] = [b for b in benutzer_daten["benutzer"]
                                   if b["benutzername"].lower() != benutzername.lower()]
    speichere_benutzer(benutzer_daten)
    return True, "Benutzer gelöscht"

def hole_besitzer_fuer_kennzeichen(fahrzeuge, kennzeichen):
    """Gibt Besitzer-Daten für ein Kennzeichen zurück oder None"""
    for f in fahrzeuge.get("fahrzeuge", []):
        if f["kennzeichen"] == kennzeichen:
            return f
    return None

def hole_alle_kennzeichen_aus_historie(historie):
    """Gibt alle eindeutigen Kennzeichen aus der Historie zurück"""
    kennzeichen = set()
    for t in historie.get("tankvorgaenge", []):
        if t.get("kennzeichen"):
            kennzeichen.add(t["kennzeichen"])
    return sorted(list(kennzeichen))

def ersetze_platzhalter(text, platzhalter):
    """Ersetzt Platzhalter in einem Text"""
    for key, value in platzhalter.items():
        text = text.replace("{" + key + "}", str(value))
    return text

def erstelle_auffaelligkeiten_email(besitzer_name, kennzeichen, auffaelligkeiten, vorlage=None):
    """Erstellt HTML-E-Mail mit Auffälligkeiten für ein Fahrzeug"""
    if vorlage is None:
        vorlage = lade_email_vorlage()

    fehler = [a for a in auffaelligkeiten if a["schwere"] == "fehler"]
    warnungen = [a for a in auffaelligkeiten if a["schwere"] == "warnung"]

    # Platzhalter-Werte
    platzhalter = {
        "besitzer_name": besitzer_name,
        "kennzeichen": kennzeichen,
        "anzahl_gesamt": len(auffaelligkeiten),
        "anzahl_fehler": len(fehler),
        "anzahl_warnungen": len(warnungen),
        "datum_heute": datetime.now().strftime("%d.%m.%Y")
    }

    # Vorlagen-Texte mit Platzhaltern ersetzen
    anrede = ersetze_platzhalter(vorlage.get("anrede", DEFAULT_EMAIL_VORLAGE["anrede"]), platzhalter)
    einleitung = ersetze_platzhalter(vorlage.get("einleitung", DEFAULT_EMAIL_VORLAGE["einleitung"]), platzhalter)
    abschluss = ersetze_platzhalter(vorlage.get("abschluss", DEFAULT_EMAIL_VORLAGE["abschluss"]), platzhalter)
    fusszeile = ersetze_platzhalter(vorlage.get("fusszeile", DEFAULT_EMAIL_VORLAGE["fusszeile"]), platzhalter)

    # Auffälligkeiten-Tabelle erstellen
    tabellen_zeilen = ""
    for a in sorted(auffaelligkeiten, key=lambda x: (x["datum"], x["zeit"]), reverse=True):
        row_class = "fehler-row" if a["schwere"] == "fehler" else "warnung-row"
        tabellen_zeilen += f"""
                    <tr class="{row_class}">
                        <td>{a['datum']}</td>
                        <td>{a['zeit']}</td>
                        <td>{a['typ']}</td>
                        <td>{a['details']}</td>
                    </tr>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #2c3e50; }}
            .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .summary-item {{ display: inline-block; margin-right: 30px; }}
            .fehler {{ color: #c0392b; font-weight: bold; }}
            .warnung {{ color: #d35400; font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #34495e; color: white; }}
            tr.fehler-row {{ background-color: #ffcccc; }}
            tr.warnung-row {{ background-color: #ffe6cc; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #7f8c8d; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>DKV Abrechnungs-Checker: Auffälligkeiten</h1>

            <p>{anrede}</p>

            <p>{einleitung}</p>

            <div class="summary">
                <span class="summary-item"><strong>Gesamt:</strong> {len(auffaelligkeiten)}</span>
                <span class="summary-item"><span class="fehler">Fehler:</span> {len(fehler)}</span>
                <span class="summary-item"><span class="warnung">Warnungen:</span> {len(warnungen)}</span>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Datum</th>
                        <th>Zeit</th>
                        <th>Problem</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>{tabellen_zeilen}
                </tbody>
            </table>

            <p>{abschluss}</p>

            <div class="footer">
                <p>{fusszeile}</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def erstelle_email_betreff(kennzeichen, auffaelligkeiten, vorlage=None):
    """Erstellt den E-Mail-Betreff aus der Vorlage"""
    if vorlage is None:
        vorlage = lade_email_vorlage()

    fehler = [a for a in auffaelligkeiten if a["schwere"] == "fehler"]
    warnungen = [a for a in auffaelligkeiten if a["schwere"] == "warnung"]

    platzhalter = {
        "kennzeichen": kennzeichen,
        "anzahl_gesamt": len(auffaelligkeiten),
        "anzahl_fehler": len(fehler),
        "anzahl_warnungen": len(warnungen),
        "datum_heute": datetime.now().strftime("%d.%m.%Y")
    }

    betreff = ersetze_platzhalter(vorlage.get("betreff", DEFAULT_EMAIL_VORLAGE["betreff"]), platzhalter)
    return betreff

def teste_smtp_verbindung(config):
    """Testet die SMTP-Verbindung und gibt (erfolg, nachricht) zurück"""
    if not config.get("server"):
        return False, "Kein SMTP-Server konfiguriert"

    try:
        if config.get("tls", True):
            server = smtplib.SMTP(config["server"], config.get("port", 587), timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP(config["server"], config.get("port", 25), timeout=10)

        if config.get("benutzer") and config.get("passwort"):
            server.login(config["benutzer"], config["passwort"])

        server.quit()
        return True, "Verbindung erfolgreich!"
    except smtplib.SMTPAuthenticationError:
        return False, "Authentifizierung fehlgeschlagen. Bitte Benutzername und Passwort prüfen."
    except smtplib.SMTPConnectError:
        return False, f"Verbindung zu {config['server']}:{config.get('port', 587)} fehlgeschlagen."
    except Exception as e:
        return False, f"Fehler: {str(e)}"

def sende_benachrichtigung(smtp_config, empfaenger_email, betreff, html_body):
    """Sendet eine E-Mail und gibt (erfolg, nachricht) zurück"""
    if not smtp_config.get("server"):
        return False, "Kein SMTP-Server konfiguriert"

    if not smtp_config.get("absender_email"):
        return False, "Keine Absender-E-Mail konfiguriert"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = betreff
        msg["From"] = f"{smtp_config.get('absender_name', 'DKV Checker')} <{smtp_config['absender_email']}>"
        msg["To"] = empfaenger_email

        # HTML-Version
        html_part = MIMEText(html_body, "html", "utf-8")
        msg.attach(html_part)

        if smtp_config.get("tls", True):
            server = smtplib.SMTP(smtp_config["server"], smtp_config.get("port", 587), timeout=30)
            server.starttls()
        else:
            server = smtplib.SMTP(smtp_config["server"], smtp_config.get("port", 25), timeout=30)

        if smtp_config.get("benutzer") and smtp_config.get("passwort"):
            server.login(smtp_config["benutzer"], smtp_config["passwort"])

        server.sendmail(smtp_config["absender_email"], empfaenger_email, msg.as_string())
        server.quit()

        return True, f"E-Mail an {empfaenger_email} gesendet"
    except Exception as e:
        return False, f"Fehler beim Senden: {str(e)}"

def parse_dkv_csv(content):
    """DKV-CSV parsen und DataFrame zurückgeben"""
    lines = content.split("\n")
    header = lines[0]
    data_lines = [line for line in lines[5:] if line.strip() and ";" in line and not line.startswith(" ")]
    clean_csv = header + "\n" + "\n".join(data_lines)

    df = pd.read_csv(StringIO(clean_csv), delimiter=";", dtype=str)

    df_clean = pd.DataFrame()
    df_clean["Kennzeichen"] = df["Kennzeichen"].str.strip()
    df_clean["km_Stand"] = df["km-Stand"].apply(parse_german_number)
    df_clean["Datum"] = pd.to_datetime(df["Lieferdatum"], format="%d.%m.%Y", errors="coerce")
    df_clean["Zeit"] = df["Lieferzeit"].str.strip()
    df_clean["Menge_Liter"] = df["Menge"].apply(parse_german_number)
    df_clean["Warenart"] = df["Warenart"].str.strip()
    df_clean["Betrag_EUR"] = df["Wert incl. USt"].apply(parse_german_number)
    df_clean["Tankstelle"] = df["Name"].str.strip()

    return df_clean.sort_values(["Kennzeichen", "Datum", "Zeit"]).reset_index(drop=True)

def parse_dkv_pdf(pdf_bytes):
    """DKV-PDF parsen und DataFrame zurückgeben"""
    records = []
    current_vehicle = None

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            for table in tables:
                for row in table:
                    if not row or not row[0]:
                        continue

                    first_cell = str(row[0])

                    # Fahrzeug-Header erkennen
                    vehicle_match = re.search(r"VEHICLE:\s*([A-Z]{2,3}-[A-Z]{1,2}\s*\d+[A-Z]?)\s+CARD", first_cell)
                    if vehicle_match:
                        current_vehicle = vehicle_match.group(1).replace(" ", "")
                        continue

                    # TOTAL-Zeilen und Header überspringen
                    if "TOTAL:" in first_cell or "Gesamtsummen" in first_cell or "Lieferdatum" in first_cell:
                        continue

                    # Datenzeilen verarbeiten (können mehrere Einträge mit \n enthalten)
                    if re.match(r"\d{2}\.\d{2}\.\d{4}", first_cell) and current_vehicle:
                        # Zellen in Zeilen aufteilen
                        lines_col0 = first_cell.split("\n")
                        lines_col1 = (row[1] or "").split("\n") if len(row) > 1 else [""] * len(lines_col0)
                        lines_col3 = (row[3] or "").split("\n") if len(row) > 3 else [""] * len(lines_col0)
                        lines_col10 = (row[10] or "").split("\n") if len(row) > 10 else [""] * len(lines_col0)

                        for i, line in enumerate(lines_col0):
                            # Datum extrahieren
                            datum_match = re.match(r"(\d{2}\.\d{2}\.\d{4})\s+(.+)", line)
                            if not datum_match:
                                continue

                            datum = datum_match.group(1)
                            rest_line = datum_match.group(2)

                            # Zeit aus der Zeile extrahieren (Format HH:MM)
                            zeit = ""
                            zeit_match = re.search(r"(\d{2}:\d{2})", rest_line)
                            if zeit_match:
                                zeit = zeit_match.group(1)

                            # km-Stand: Zahl nach der Zeit
                            km_stand = None
                            if zeit:
                                after_time = rest_line[rest_line.index(zeit) + 5:].strip()
                                km_match = re.match(r"(\d+)", after_time)
                                if km_match:
                                    km_stand = km_match.group(1)

                            # Tankstelle: Text zwischen Datum und Stationsnummer
                            station_match = re.search(r"(\d{7})", rest_line)
                            tankstelle = ""
                            if station_match:
                                tankstelle = rest_line[:station_match.start()].strip()

                            # Produkt aus Spalte 1
                            produkt = ""
                            if i < len(lines_col1):
                                prod_match = re.match(r"([A-Z0-9\s\(\)]+)\s+\d{4}", lines_col1[i])
                                if prod_match:
                                    produkt = prod_match.group(1).strip()

                            # Menge aus Spalte 3
                            menge = None
                            if i < len(lines_col3):
                                menge = parse_german_number(lines_col3[i].strip())

                            # Betrag aus Spalte 10 (Gesamtwert brutto)
                            betrag = None
                            if i < len(lines_col10):
                                betrag = parse_german_number(lines_col10[i].strip())

                            if menge and menge > 0:
                                records.append({
                                    "Kennzeichen": current_vehicle,
                                    "Datum": datum,
                                    "Tankstelle": tankstelle,
                                    "Zeit": zeit,
                                    "km_Stand": parse_german_number(km_stand) if km_stand else None,
                                    "Warenart": produkt,
                                    "Menge_Liter": menge,
                                    "Betrag_EUR": betrag
                                })

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df["Datum"] = pd.to_datetime(df["Datum"], format="%d.%m.%Y", errors="coerce")

    return df.sort_values(["Kennzeichen", "Datum", "Zeit"]).reset_index(drop=True)

def berechne_verbrauch(df):
    """Verbrauch berechnen und DataFrame erweitern"""
    result = []

    for kennzeichen in df["Kennzeichen"].unique():
        fahrzeug_df = df[df["Kennzeichen"] == kennzeichen].copy()
        fahrzeug_df = fahrzeug_df.sort_values(["Datum", "Zeit"]).reset_index(drop=True)

        fahrzeug_df["km_vorher"] = fahrzeug_df["km_Stand"].shift(1)
        fahrzeug_df["km_differenz"] = fahrzeug_df["km_Stand"] - fahrzeug_df["km_vorher"]
        fahrzeug_df["Verbrauch_L100km"] = (fahrzeug_df["Menge_Liter"] / fahrzeug_df["km_differenz"]) * 100

        result.append(fahrzeug_df)

    return pd.concat(result, ignore_index=True) if result else df

def berechne_verbrauch_historie(historie):
    """Berechnet Verbrauch und km-Differenz für alle Einträge in der Historie neu"""
    if not historie["tankvorgaenge"]:
        return historie

    # Alle Tankvorgänge als Liste bearbeiten
    tankvorgaenge = historie["tankvorgaenge"].copy()

    # Nach Fahrzeug gruppieren und sortieren
    from collections import defaultdict
    fahrzeuge = defaultdict(list)

    for i, t in enumerate(tankvorgaenge):
        fahrzeuge[t["kennzeichen"]].append((i, t))

    # Pro Fahrzeug berechnen
    for kennzeichen, eintraege in fahrzeuge.items():
        # Nach Datum und Zeit sortieren
        eintraege_sorted = sorted(eintraege, key=lambda x: (x[1]["datum"], x[1]["zeit"] or ""))

        km_vorher = None
        for j, (original_idx, eintrag) in enumerate(eintraege_sorted):
            km_aktuell = eintrag.get("km_stand")

            if j == 0 or km_vorher is None:
                # Erster Eintrag oder vorheriger km-Stand fehlt
                tankvorgaenge[original_idx]["km_differenz"] = None
                tankvorgaenge[original_idx]["verbrauch"] = None
            else:
                if km_aktuell is not None and km_aktuell > 0:
                    km_diff = km_aktuell - km_vorher
                    tankvorgaenge[original_idx]["km_differenz"] = km_diff

                    menge = eintrag.get("menge_liter")
                    if km_diff > 0 and menge is not None and menge > 0:
                        verbrauch = (menge / km_diff) * 100
                        tankvorgaenge[original_idx]["verbrauch"] = round(verbrauch, 2)
                    else:
                        tankvorgaenge[original_idx]["verbrauch"] = None
                else:
                    tankvorgaenge[original_idx]["km_differenz"] = None
                    tankvorgaenge[original_idx]["verbrauch"] = None

            # km-Stand für nächste Iteration merken (nur wenn gültig)
            if km_aktuell is not None and km_aktuell > 0:
                km_vorher = km_aktuell

    historie["tankvorgaenge"] = tankvorgaenge
    return historie

def pruefe_auffaelligkeiten(historie):
    """Prüft Historie auf Auffälligkeiten und gibt Liste zurück"""
    auffaelligkeiten = []

    if not historie["tankvorgaenge"]:
        return auffaelligkeiten

    # Fahrzeug-spezifische Verbrauchsgrenzen laden
    fahrzeuge_config = lade_fahrzeuge()
    fahrzeug_grenzen = {}
    for fz in fahrzeuge_config.get("fahrzeuge", []):
        fahrzeug_grenzen[fz["kennzeichen"]] = {
            "min": fz.get("verbrauch_min", 3),
            "max": fz.get("verbrauch_max", 25)
        }

    # Standard-Grenzen
    DEFAULT_MIN = 3
    DEFAULT_MAX = 25

    df = pd.DataFrame(historie["tankvorgaenge"])
    df["datum"] = pd.to_datetime(df["datum"])

    for kennzeichen in df["kennzeichen"].unique():
        fahrzeug_df = df[df["kennzeichen"] == kennzeichen].copy()
        fahrzeug_df = fahrzeug_df.sort_values(["datum", "zeit"]).reset_index(drop=True)

        # Grenzen für dieses Fahrzeug
        grenzen = fahrzeug_grenzen.get(kennzeichen, {"min": DEFAULT_MIN, "max": DEFAULT_MAX})
        verbrauch_min = grenzen["min"] if grenzen["min"] else DEFAULT_MIN
        verbrauch_max = grenzen["max"] if grenzen["max"] else DEFAULT_MAX

        for idx, row in fahrzeug_df.iterrows():
            eintrag_id = f"{row['kennzeichen']}_{row['datum'].strftime('%Y-%m-%d')}_{row['zeit']}"

            # Quittierungs-Info aus dem Tankvorgang holen
            quittiert = row.get("quittiert", False)
            quittiert_kommentar = row.get("quittiert_kommentar", "")
            quittiert_von = row.get("quittiert_von", "")
            quittiert_am = row.get("quittiert_am", "")

            # Fehlender km-Stand
            if pd.isna(row["km_stand"]) or row["km_stand"] == 0:
                auffaelligkeiten.append({
                    "id": eintrag_id,
                    "fahrzeug": kennzeichen,
                    "datum": row["datum"].strftime("%d.%m.%Y"),
                    "zeit": row["zeit"],
                    "typ": "Fehlender km-Stand",
                    "details": f"Tankvorgang ohne km-Angabe ({row['menge_liter']:.1f} L)",
                    "schwere": "warnung",
                    "quittiert": quittiert,
                    "quittiert_kommentar": quittiert_kommentar,
                    "quittiert_von": quittiert_von,
                    "quittiert_am": quittiert_am
                })

            # km-Stand gesunken
            if idx > 0:
                vorheriger = fahrzeug_df.iloc[idx - 1]
                if pd.notna(row["km_stand"]) and pd.notna(vorheriger["km_stand"]):
                    diff = row["km_stand"] - vorheriger["km_stand"]
                    if diff < 0:
                        auffaelligkeiten.append({
                            "id": eintrag_id,
                            "fahrzeug": kennzeichen,
                            "datum": row["datum"].strftime("%d.%m.%Y"),
                            "zeit": row["zeit"],
                            "typ": "km-Stand gesunken",
                            "details": f"Differenz: {diff:.0f} km (vorher: {vorheriger['km_stand']:.0f})",
                            "schwere": "fehler",
                            "quittiert": quittiert,
                            "quittiert_kommentar": quittiert_kommentar,
                            "quittiert_von": quittiert_von,
                            "quittiert_am": quittiert_am
                        })

            # Verbrauch prüfen (mit fahrzeugspezifischen Grenzen)
            if pd.notna(row["verbrauch"]):
                if row["verbrauch"] < verbrauch_min:
                    auffaelligkeiten.append({
                        "id": eintrag_id,
                        "fahrzeug": kennzeichen,
                        "datum": row["datum"].strftime("%d.%m.%Y"),
                        "zeit": row["zeit"],
                        "typ": "Verbrauch zu niedrig",
                        "details": f"{row['verbrauch']:.1f} L/100km (Grenze: {verbrauch_min} L/100km)",
                        "schwere": "warnung",
                        "quittiert": quittiert,
                        "quittiert_kommentar": quittiert_kommentar,
                        "quittiert_von": quittiert_von,
                        "quittiert_am": quittiert_am
                    })
                elif row["verbrauch"] > verbrauch_max:
                    auffaelligkeiten.append({
                        "id": eintrag_id,
                        "fahrzeug": kennzeichen,
                        "datum": row["datum"].strftime("%d.%m.%Y"),
                        "zeit": row["zeit"],
                        "typ": "Verbrauch zu hoch",
                        "details": f"{row['verbrauch']:.1f} L/100km (Grenze: {verbrauch_max} L/100km)",
                        "schwere": "fehler",
                        "quittiert": quittiert,
                        "quittiert_kommentar": quittiert_kommentar,
                        "quittiert_von": quittiert_von,
                        "quittiert_am": quittiert_am
                    })

    return auffaelligkeiten

def style_auffaelligkeiten(row, auffaellige_ids):
    """Styling-Funktion für DataFrame mit Auffälligkeiten"""
    row_id = f"{row['kennzeichen']}_{pd.to_datetime(row['datum']).strftime('%Y-%m-%d')}_{row['zeit']}"
    if row_id in auffaellige_ids:
        return ['background-color: #ffcccc'] * len(row)
    return [''] * len(row)

# --- Sidebar: Login ---
with st.sidebar:
    st.markdown("### Benutzer")

    if st.session_state["logged_in"]:
        # Passwort-Änderung erforderlich?
        if st.session_state.get("muss_passwort_aendern", False):
            st.warning("Bitte ändern Sie Ihr Passwort!")
            with st.form("passwort_aendern_form"):
                neues_passwort = st.text_input("Neues Passwort", type="password")
                neues_passwort_bestaetigen = st.text_input("Passwort bestätigen", type="password")
                pw_submitted = st.form_submit_button("Passwort ändern")

                if pw_submitted:
                    if len(neues_passwort) < 6:
                        st.error("Passwort muss mindestens 6 Zeichen lang sein")
                    elif neues_passwort != neues_passwort_bestaetigen:
                        st.error("Passwörter stimmen nicht überein")
                    else:
                        aktualisiere_benutzer(st.session_state["username"], {
                            "passwort_hash": hash_passwort(neues_passwort),
                            "muss_passwort_aendern": False
                        })
                        st.session_state["muss_passwort_aendern"] = False
                        st.success("Passwort geändert!")
                        st.rerun()
        else:
            # Normale Anzeige
            rolle_name = ROLLEN.get(st.session_state["user_rolle"], {}).get("name", st.session_state["user_rolle"])
            anzeige_name = st.session_state.get("user_name") or st.session_state["username"]
            st.success(f"Angemeldet als: {anzeige_name}")
            st.caption(f"Rolle: {rolle_name}")

            # Passwort ändern (optional)
            with st.expander("Passwort ändern"):
                with st.form("passwort_optional_form"):
                    aktuelles_pw = st.text_input("Aktuelles Passwort", type="password", key="pw_aktuell")
                    neues_pw = st.text_input("Neues Passwort", type="password", key="pw_neu")
                    neues_pw_best = st.text_input("Passwort bestätigen", type="password", key="pw_best")
                    pw_opt_submitted = st.form_submit_button("Ändern")

                    if pw_opt_submitted:
                        benutzer = finde_benutzer(st.session_state["username"])
                        if not pruefe_passwort(aktuelles_pw, benutzer.get("passwort_hash", "")):
                            st.error("Aktuelles Passwort ist falsch")
                        elif len(neues_pw) < 6:
                            st.error("Neues Passwort muss mindestens 6 Zeichen lang sein")
                        elif neues_pw != neues_pw_best:
                            st.error("Passwörter stimmen nicht überein")
                        else:
                            aktualisiere_benutzer(st.session_state["username"], {
                                "passwort_hash": hash_passwort(neues_pw)
                            })
                            st.success("Passwort geändert!")

            if st.button("Abmelden"):
                st.session_state["logged_in"] = False
                st.session_state["username"] = ""
                st.session_state["user_rolle"] = ""
                st.session_state["user_name"] = ""
                st.session_state["muss_passwort_aendern"] = False
                st.rerun()
    else:
        with st.form("login_form"):
            username = st.text_input("Benutzername")
            password = st.text_input("Passwort", type="password")
            submitted = st.form_submit_button("Anmelden")

            if submitted:
                benutzer = authentifiziere_benutzer(username, password)
                if benutzer:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = benutzer["benutzername"]
                    st.session_state["user_rolle"] = benutzer.get("rolle", "viewer")
                    st.session_state["user_name"] = benutzer.get("name", "")
                    st.session_state["muss_passwort_aendern"] = benutzer.get("muss_passwort_aendern", False)
                    st.rerun()
                else:
                    st.error("Ungültige Anmeldedaten oder Konto deaktiviert")

    st.markdown("---")
    st.markdown("### Info")
    if st.session_state["logged_in"]:
        rolle = st.session_state["user_rolle"]
        if rolle in ROLLEN:
            st.info(ROLLEN[rolle]["beschreibung"])
    else:
        st.info("Melden Sie sich an, um Daten bearbeiten zu können.")

    # Spenden-Hinweis
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; padding: 10px; background-color: #f0f2f6; border-radius: 5px;">
            <small>Diese Software ist kostenlos.<br>
            <a href="https://www.paypal.com/paypalme/christiansauer87" target="_blank">☕ Entwicklung unterstützen</a></small>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- Hauptanwendung ---

st.title("DKV Abrechnungs-Checker")

# Historie laden
historie = lade_historie()

# Auffälligkeiten berechnen
alle_auffaelligkeiten = pruefe_auffaelligkeiten(historie)
auffaellige_ids = set(a["id"] for a in alle_auffaelligkeiten)
# Nur nicht-quittierte Auffälligkeiten für Tab-Zähler
offene_auffaelligkeiten = [a for a in alle_auffaelligkeiten if not a.get("quittiert", False)]

# Fahrzeuge und SMTP-Konfiguration laden
fahrzeuge_config = lade_fahrzeuge()
smtp_config = lade_smtp_config()

# Tabs für verschiedene Ansichten
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📤 Import & Analyse",
    "📊 Verbrauchsentwicklung",
    "📚 Historie",
    f"⚠️ Auffälligkeiten ({len(offene_auffaelligkeiten)})",
    "⚙️ Einstellungen",
    "📖 Hilfe"
])

# --- TAB 1: Import & Analyse ---
with tab1:
    uploaded_files = st.file_uploader(
        "DKV-Dateien hochladen (CSV oder PDF)",
        type=["csv", "pdf"],
        accept_multiple_files=True
    )

    # Prüfen ob Dateien bereits importiert wurden
    bereits_importierte_dateien = [imp.get("dateiname", "") for imp in historie.get("importe", [])]

    if uploaded_files:
        # Prüfung der Import-Berechtigung vorab
        kann_importieren = aktueller_benutzer_hat_recht("importieren")

        # Dateien kategorisieren: neu vs. bereits importiert
        neue_dateien = []
        bereits_importiert = []
        for uf in uploaded_files:
            if uf.name in bereits_importierte_dateien:
                bereits_importiert.append(uf.name)
            else:
                neue_dateien.append(uf)

        # Warnung für bereits importierte Dateien
        if bereits_importiert:
            st.warning(f"**{len(bereits_importiert)} Datei(en) bereits importiert** (werden übersprungen): {', '.join(bereits_importiert)}")

        if not neue_dateien:
            st.info("Alle hochgeladenen Dateien wurden bereits importiert.")
        else:
            # Status-Anzeige
            st.info(f"**{len(neue_dateien)} neue Datei(en)** werden verarbeitet...")

            # Alle Daten sammeln
            alle_daten = []
            alle_rohdaten = []
            import_fehler = []

            for uploaded_file in neue_dateien:
                try:
                    if uploaded_file.name.lower().endswith(".pdf"):
                        pdf_bytes = uploaded_file.read()
                        df_clean = parse_dkv_pdf(pdf_bytes)
                        if df_clean.empty:
                            import_fehler.append(f"{uploaded_file.name}: Keine Daten aus PDF extrahiert")
                            continue
                    else:
                        content = uploaded_file.read().decode("utf-8")
                        df_clean = parse_dkv_csv(content)

                    # Quelldatei-Spalte hinzufügen
                    df_clean["Quelldatei"] = uploaded_file.name
                    alle_rohdaten.append(df_clean)

                    # Nur Kraftstoff (kein AdBlue)
                    kraftstoff_filter = df_clean["Warenart"].str.contains("DIESEL|SUPER|BENZIN|EURO", case=False, na=False)
                    df_fuel = df_clean[kraftstoff_filter].copy()
                    if not df_fuel.empty:
                        alle_daten.append((uploaded_file.name, df_fuel))
                except Exception as e:
                    import_fehler.append(f"{uploaded_file.name}: {str(e)}")

            # Fehler anzeigen
            if import_fehler:
                for fehler in import_fehler:
                    st.error(fehler)

            if alle_rohdaten:
                # Alle Rohdaten zusammenführen
                df_alle_roh = pd.concat(alle_rohdaten, ignore_index=True)

                st.subheader("Rohdaten")
                st.dataframe(df_alle_roh, use_container_width=True)

            if alle_daten:
                # Alle Kraftstoffdaten zusammenführen
                df_fuel_combined = pd.concat([df for _, df in alle_daten], ignore_index=True)
                df_fuel_combined = berechne_verbrauch(df_fuel_combined)

                # --- Verbrauchsanalyse ---
                st.subheader("Verbrauchsanalyse pro Fahrzeug")

                warnungen = []
                ergebnisse = []

                for kennzeichen in df_fuel_combined["Kennzeichen"].unique():
                    fahrzeug_df = df_fuel_combined[df_fuel_combined["Kennzeichen"] == kennzeichen].copy()
                    fahrzeug_df = fahrzeug_df.reset_index(drop=True)

                    st.markdown(f"### {kennzeichen}")

                    # Prüfungen
                    fehlende_km = fahrzeug_df[fahrzeug_df["km_Stand"].isna() | (fahrzeug_df["km_Stand"] == 0)]
                    for _, row in fehlende_km.iterrows():
                        warnungen.append({
                            "Fahrzeug": kennzeichen,
                            "Datum": row["Datum"].strftime("%d.%m.%Y") if pd.notna(row["Datum"]) else "?",
                            "Problem": "Fehlender km-Stand",
                            "Details": f"Tankvorgang ohne km-Angabe ({row['Menge_Liter']:.1f} L)"
                        })

                    # Tabelle mit Hervorhebung erstellen
                    display_df = fahrzeug_df[["Datum", "km_Stand", "Menge_Liter", "km_differenz", "Verbrauch_L100km", "Tankstelle", "Quelldatei"]].copy()
                    display_df["Datum"] = display_df["Datum"].dt.strftime("%d.%m.%Y")

                    # Auffälligkeiten markieren
                    def highlight_rows(row):
                        styles = [''] * len(row)
                        idx = row.name
                        if idx >= len(fahrzeug_df):
                            return styles
                        # km-Stand fehlt oder 0
                        if pd.isna(fahrzeug_df.iloc[idx]["km_Stand"]) or fahrzeug_df.iloc[idx]["km_Stand"] == 0:
                            return ['background-color: #ffcccc'] * len(row)
                        # km gesunken
                        if pd.notna(fahrzeug_df.iloc[idx]["km_differenz"]) and fahrzeug_df.iloc[idx]["km_differenz"] < 0:
                            return ['background-color: #ffcccc'] * len(row)
                        # Verbrauch außerhalb Grenzen
                        verbrauch = fahrzeug_df.iloc[idx]["Verbrauch_L100km"]
                        if pd.notna(verbrauch) and (verbrauch < 3 or verbrauch > 25):
                            return ['background-color: #ffcccc'] * len(row)
                        return styles

                    display_df = display_df.rename(columns={
                        "km_Stand": "km-Stand",
                        "Menge_Liter": "Liter",
                        "km_differenz": "km gefahren",
                        "Verbrauch_L100km": "L/100km",
                        "Quelldatei": "Datei"
                    })

                    styled_df = display_df.style.apply(highlight_rows, axis=1)
                    st.dataframe(styled_df, use_container_width=True)

                    # Weitere Prüfungen
                    for _, row in fahrzeug_df.iterrows():
                        if pd.notna(row["km_differenz"]) and row["km_differenz"] < 0:
                            warnungen.append({
                                "Fahrzeug": kennzeichen,
                                "Datum": row["Datum"].strftime("%d.%m.%Y"),
                                "Problem": "km-Stand gesunken!",
                                "Details": f"Differenz: {row['km_differenz']:.0f} km"
                            })

                        if pd.notna(row["Verbrauch_L100km"]):
                            if row["Verbrauch_L100km"] < 3:
                                warnungen.append({
                                    "Fahrzeug": kennzeichen,
                                    "Datum": row["Datum"].strftime("%d.%m.%Y"),
                                    "Problem": "Verbrauch zu niedrig",
                                    "Details": f"{row['Verbrauch_L100km']:.1f} L/100km"
                                })
                            elif row["Verbrauch_L100km"] > 25:
                                warnungen.append({
                                    "Fahrzeug": kennzeichen,
                                    "Datum": row["Datum"].strftime("%d.%m.%Y"),
                                    "Problem": "Verbrauch zu hoch",
                                    "Details": f"{row['Verbrauch_L100km']:.1f} L/100km"
                                })

                    # Statistik
                    valid_consumption = fahrzeug_df["Verbrauch_L100km"].dropna()
                    valid_consumption = valid_consumption[(valid_consumption > 3) & (valid_consumption < 25)]
                    if len(valid_consumption) > 0:
                        ergebnisse.append({
                            "Fahrzeug": kennzeichen,
                            "Durchschnittsverbrauch": f"{valid_consumption.mean():.1f} L/100km",
                            "Tankvorgänge": len(fahrzeug_df),
                            "Gesamtmenge": f"{fahrzeug_df['Menge_Liter'].sum():.1f} L",
                            "Gesamtkosten": f"{fahrzeug_df['Betrag_EUR'].sum():.2f} EUR"
                        })

                # Zusammenfassung
                st.subheader("Zusammenfassung")
                if ergebnisse:
                    st.dataframe(pd.DataFrame(ergebnisse), use_container_width=True)

                # Warnungen
                st.subheader("Warnungen & Auffälligkeiten")
                if warnungen:
                    warn_df = pd.DataFrame(warnungen)
                    st.dataframe(warn_df.style.apply(lambda x: ['background-color: #ffcccc'] * len(x), axis=1),
                                use_container_width=True)
                    st.warning(f"{len(warnungen)} Auffälligkeit(en) gefunden!")
                else:
                    st.success("Keine Auffälligkeiten gefunden.")

                # --- Automatisches Speichern ---
                st.subheader("Import-Status")

                if not kann_importieren:
                    st.info("Sie haben keine Berechtigung zum Importieren. Melden Sie sich mit einem entsprechenden Konto an.")
                else:
                    # Automatisch speichern
                    neue_vorgaenge_gesamt = 0
                    duplikate_gesamt = 0
                    importierte_dateien = []

                    for dateiname, df_fuel in alle_daten:
                        neue_vorgaenge = 0
                        for _, row in df_fuel.iterrows():
                            eintrag = {
                                "kennzeichen": row["Kennzeichen"],
                                "datum": row["Datum"].strftime("%Y-%m-%d") if pd.notna(row["Datum"]) else None,
                                "zeit": row["Zeit"],
                                "km_stand": row["km_Stand"],
                                "menge_liter": row["Menge_Liter"],
                                "verbrauch": None,  # Wird beim Speichern automatisch berechnet
                                "betrag_eur": row["Betrag_EUR"],
                                "tankstelle": row["Tankstelle"],
                                "warenart": row["Warenart"],
                                "quelldatei": dateiname
                            }

                            # Duplikate vermeiden (gleiches Datum, Zeit, Kennzeichen)
                            ist_duplikat = any(
                                t["kennzeichen"] == eintrag["kennzeichen"] and
                                t["datum"] == eintrag["datum"] and
                                t["zeit"] == eintrag["zeit"]
                                for t in historie["tankvorgaenge"]
                            )

                            if not ist_duplikat:
                                historie["tankvorgaenge"].append(eintrag)
                                neue_vorgaenge += 1
                            else:
                                duplikate_gesamt += 1

                        neue_vorgaenge_gesamt += neue_vorgaenge

                        # Import-Eintrag für diese Datei
                        historie["importe"].append({
                            "datum": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "dateiname": dateiname,
                            "anzahl_vorgaenge": neue_vorgaenge
                        })
                        importierte_dateien.append(dateiname)

                    speichere_historie(historie)

                    # Erfolgsmeldung
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Neue Tankvorgänge", neue_vorgaenge_gesamt)
                    with col2:
                        st.metric("Dateien importiert", len(importierte_dateien))
                    with col3:
                        st.metric("Duplikate übersprungen", duplikate_gesamt)

                    if neue_vorgaenge_gesamt > 0:
                        st.success(f"Import erfolgreich: {neue_vorgaenge_gesamt} neue Tankvorgänge aus {len(importierte_dateien)} Datei(en) gespeichert.")
                        st.caption("Gefällt Ihnen diese Software? [Unterstützen Sie die Entwicklung mit einer Spende](https://www.paypal.com/paypalme/christiansauer87)")
                    elif duplikate_gesamt > 0:
                        st.info("Alle Datensätze waren bereits in der Historie vorhanden (Duplikate).")

                    # Liste der importierten Dateien
                    with st.expander("Importierte Dateien anzeigen"):
                        for dateiname in importierte_dateien:
                            st.write(f"- {dateiname}")

    else:
        st.info("Bitte DKV-Dateien (CSV oder PDF) hochladen, um die Analyse zu starten. Sie können mehrere Dateien gleichzeitig auswählen.")

# --- TAB 2: Verbrauchsentwicklung ---
with tab2:
    st.subheader("Verbrauchsentwicklung über Zeit")

    if historie["tankvorgaenge"]:
        df_historie = pd.DataFrame(historie["tankvorgaenge"])
        df_historie["datum"] = pd.to_datetime(df_historie["datum"])
        df_historie = df_historie.sort_values(["datum", "zeit"])

        # Filter für gültige Verbrauchswerte
        df_chart = df_historie[df_historie["verbrauch"].notna()].copy()
        df_chart = df_chart[(df_chart["verbrauch"] > 3) & (df_chart["verbrauch"] < 25)]

        if len(df_chart) > 0:
            # Filter-Bereich
            st.markdown("#### Filter")

            # Datumsbereich ermitteln
            min_datum = df_chart["datum"].min().date()
            max_datum = df_chart["datum"].max().date()

            col_filter1, col_filter2, col_filter3 = st.columns([1, 1, 2])
            with col_filter1:
                start_datum = st.date_input(
                    "Von",
                    value=min_datum,
                    min_value=min_datum,
                    max_value=max_datum,
                    key="verbrauch_start_datum"
                )
            with col_filter2:
                end_datum = st.date_input(
                    "Bis",
                    value=max_datum,
                    min_value=min_datum,
                    max_value=max_datum,
                    key="verbrauch_end_datum"
                )
            with col_filter3:
                # Fahrzeugauswahl
                alle_fahrzeuge = df_chart["kennzeichen"].unique().tolist()
                ausgewaehlte = st.multiselect(
                    "Fahrzeuge",
                    alle_fahrzeuge,
                    default=alle_fahrzeuge,
                    key="verbrauch_fahrzeuge"
                )

            # Datumsfilter anwenden
            df_chart = df_chart[
                (df_chart["datum"].dt.date >= start_datum) &
                (df_chart["datum"].dt.date <= end_datum)
            ]

            if ausgewaehlte and len(df_chart) > 0:
                df_filtered = df_chart[df_chart["kennzeichen"].isin(ausgewaehlte)]

                # Verbrauchsdiagramm
                st.markdown("### Verbrauch pro Tankvorgang")

                chart = alt.Chart(df_filtered).mark_line(point=True).encode(
                    x=alt.X("datum:T", title="Datum"),
                    y=alt.Y("verbrauch:Q", title="Verbrauch (L/100km)", scale=alt.Scale(zero=False)),
                    color=alt.Color("kennzeichen:N", title="Fahrzeug"),
                    tooltip=[
                        alt.Tooltip("datum:T", title="Datum", format="%d.%m.%Y"),
                        alt.Tooltip("kennzeichen:N", title="Fahrzeug"),
                        alt.Tooltip("verbrauch:Q", title="L/100km", format=".1f"),
                        alt.Tooltip("menge_liter:Q", title="Getankt (L)", format=".1f"),
                        alt.Tooltip("tankstelle:N", title="Tankstelle")
                    ]
                ).properties(height=400).interactive()

                st.altair_chart(chart, use_container_width=True)

                # Durchschnittsverbrauch pro Monat
                st.markdown("### Monatlicher Durchschnittsverbrauch")

                df_filtered["monat"] = df_filtered["datum"].dt.to_period("M").astype(str)
                monatlich = df_filtered.groupby(["monat", "kennzeichen"]).agg({
                    "verbrauch": "mean",
                    "menge_liter": "sum",
                    "betrag_eur": "sum"
                }).reset_index()

                chart_monat = alt.Chart(monatlich).mark_bar().encode(
                    x=alt.X("monat:N", title="Monat"),
                    y=alt.Y("verbrauch:Q", title="Ø Verbrauch (L/100km)"),
                    color=alt.Color("kennzeichen:N", title="Fahrzeug"),
                    tooltip=[
                        alt.Tooltip("monat:N", title="Monat"),
                        alt.Tooltip("kennzeichen:N", title="Fahrzeug"),
                        alt.Tooltip("verbrauch:Q", title="Ø L/100km", format=".1f"),
                        alt.Tooltip("menge_liter:Q", title="Gesamt Liter", format=".1f"),
                        alt.Tooltip("betrag_eur:Q", title="Gesamt EUR", format=".2f")
                    ]
                ).properties(height=300)

                st.altair_chart(chart_monat, use_container_width=True)

                # Kosten pro Monat
                st.markdown("### Monatliche Kosten")

                chart_kosten = alt.Chart(monatlich).mark_bar().encode(
                    x=alt.X("monat:N", title="Monat"),
                    y=alt.Y("betrag_eur:Q", title="Kosten (EUR)"),
                    color=alt.Color("kennzeichen:N", title="Fahrzeug"),
                    tooltip=[
                        alt.Tooltip("monat:N", title="Monat"),
                        alt.Tooltip("kennzeichen:N", title="Fahrzeug"),
                        alt.Tooltip("betrag_eur:Q", title="EUR", format=".2f")
                    ]
                ).properties(height=300)

                st.altair_chart(chart_kosten, use_container_width=True)

                # Statistik-Tabelle
                st.markdown("### Gesamtstatistik")

                statistik = df_filtered.groupby("kennzeichen").agg({
                    "verbrauch": ["mean", "min", "max"],
                    "menge_liter": "sum",
                    "betrag_eur": "sum",
                    "datum": "count"
                }).reset_index()
                statistik.columns = ["Fahrzeug", "Ø Verbrauch", "Min", "Max", "Gesamt Liter", "Gesamt EUR", "Tankvorgänge"]
                statistik["Ø Verbrauch"] = statistik["Ø Verbrauch"].apply(lambda x: f"{x:.1f} L/100km")
                statistik["Min"] = statistik["Min"].apply(lambda x: f"{x:.1f}")
                statistik["Max"] = statistik["Max"].apply(lambda x: f"{x:.1f}")
                statistik["Gesamt Liter"] = statistik["Gesamt Liter"].apply(lambda x: f"{x:.1f} L")
                statistik["Gesamt EUR"] = statistik["Gesamt EUR"].apply(lambda x: f"{x:.2f} €")

                st.dataframe(statistik, use_container_width=True)
            else:
                if not ausgewaehlte:
                    st.info("Bitte wählen Sie mindestens ein Fahrzeug aus.")
                else:
                    st.warning("Keine Daten im ausgewählten Zeitraum vorhanden.")
        else:
            st.warning("Keine gültigen Verbrauchsdaten in der Historie.")
    else:
        st.info("Noch keine Daten in der Historie. Importiere zuerst eine CSV-Datei im Tab 'Import & Analyse'.")

# --- TAB 3: Historie ---
with tab3:
    st.subheader("Gespeicherte Daten")

    if historie["tankvorgaenge"]:
        df_alle = pd.DataFrame(historie["tankvorgaenge"])
        df_alle["datum"] = pd.to_datetime(df_alle["datum"])
        df_alle = df_alle.sort_values(["datum", "zeit"], ascending=False)

        # Alle Tankvorgänge
        st.markdown("### Alle Tankvorgänge")

        # Filter
        col1, col2, col3 = st.columns(3)
        with col1:
            fahrzeug_filter = st.selectbox(
                "Nach Fahrzeug filtern",
                ["Alle"] + df_alle["kennzeichen"].unique().tolist()
            )
        with col2:
            zeitraum = st.selectbox(
                "Zeitraum",
                ["Alle", "Letzte 30 Tage", "Letzte 90 Tage", "Letztes Jahr"]
            )
        with col3:
            # Quelldatei-Filter
            quelldateien = df_alle["quelldatei"].dropna().unique().tolist()
            quelldateien = [q for q in quelldateien if q]  # Leere entfernen
            datei_filter = st.selectbox(
                "Nach Quelldatei filtern",
                ["Alle"] + quelldateien
            )

        df_display = df_alle.copy()

        if fahrzeug_filter != "Alle":
            df_display = df_display[df_display["kennzeichen"] == fahrzeug_filter]

        if zeitraum != "Alle":
            heute = pd.Timestamp.now()
            if zeitraum == "Letzte 30 Tage":
                df_display = df_display[df_display["datum"] >= heute - pd.Timedelta(days=30)]
            elif zeitraum == "Letzte 90 Tage":
                df_display = df_display[df_display["datum"] >= heute - pd.Timedelta(days=90)]
            elif zeitraum == "Letztes Jahr":
                df_display = df_display[df_display["datum"] >= heute - pd.Timedelta(days=365)]

        if datei_filter != "Alle":
            df_display = df_display[df_display["quelldatei"] == datei_filter]

        # Index zurücksetzen nach Filtern
        df_display = df_display.reset_index(drop=True)

        if len(df_display) > 0:
            # Auffälligkeits-IDs für diese Zeilen berechnen
            df_display["_auff_id"] = df_display.apply(
                lambda row: f"{row['kennzeichen']}_{row['datum'].strftime('%Y-%m-%d')}_{row['zeit']}", axis=1
            )
            df_display["_ist_auffaellig"] = df_display["_auff_id"].isin(auffaellige_ids)

            # Sicherstellen dass km_differenz und verbrauch existieren
            if "km_differenz" not in df_display.columns:
                df_display["km_differenz"] = None
            if "verbrauch" not in df_display.columns:
                df_display["verbrauch"] = None

            # Wenn Bearbeitungsrecht: Editierbare Tabelle
            if aktueller_benutzer_hat_recht("bearbeiten"):
                st.info("Doppelklicken Sie auf eine Zelle zum Bearbeiten.")

                # Editierbare Kopie erstellen (mit km_differenz und verbrauch zur Anzeige)
                edit_cols = ["kennzeichen", "datum", "zeit", "km_stand", "km_differenz", "menge_liter", "verbrauch", "betrag_eur", "tankstelle", "quelldatei", "_auff_id", "_ist_auffaellig"]
                df_edit = df_display[edit_cols].copy()
                df_edit["datum"] = df_edit["datum"].dt.strftime("%d.%m.%Y")

                # Auffälligkeits-Typen und Quittierungs-Status als Dictionary
                auff_info_map = {}
                for a in alle_auffaelligkeiten:
                    auff_info_map[a["id"]] = {
                        "typ": a["typ"],
                        "quittiert": a.get("quittiert", False)
                    }

                # Kurzformen für Auffälligkeits-Typen
                AUFF_KURZFORM = {
                    "Fehlender km-Stand": "km?",
                    "km-Stand gesunken": "km↓",
                    "Verbrauch zu niedrig": "L↓",
                    "Verbrauch zu hoch": "L↑"
                }

                # Status-Spalte mit Kurzform (quittierte mit ✓ statt ⚠️)
                def get_status_text(row):
                    if not row["_ist_auffaellig"]:
                        return ""
                    info = auff_info_map.get(row["_auff_id"], {})
                    typ = info.get("typ", "")
                    kurzform = AUFF_KURZFORM.get(typ, "?")
                    if info.get("quittiert", False):
                        return f"✓ {kurzform}"
                    return f"⚠️ {kurzform}"

                df_edit["_status"] = df_edit.apply(get_status_text, axis=1)

                # Spalten umbenennen für Anzeige
                df_edit_display = df_edit.rename(columns={
                    "_status": "Status",
                    "kennzeichen": "Fahrzeug",
                    "datum": "Datum",
                    "zeit": "Zeit",
                    "km_stand": "km-Stand",
                    "km_differenz": "km gefahren",
                    "menge_liter": "Liter",
                    "verbrauch": "L/100km",
                    "betrag_eur": "EUR",
                    "tankstelle": "Tankstelle",
                    "quelldatei": "Quelldatei"
                })

                # Editierbare Tabelle
                edited_df = st.data_editor(
                    df_edit_display[["Status", "Fahrzeug", "Datum", "Zeit", "km-Stand", "km gefahren", "Liter", "L/100km", "EUR", "Tankstelle", "Quelldatei"]],
                    use_container_width=True,
                    num_rows="fixed",
                    disabled=["Status", "Fahrzeug", "Datum", "Zeit", "km gefahren", "L/100km", "Quelldatei"],  # Berechnete Felder nicht editierbar
                    column_config={
                        "Status": st.column_config.TextColumn(
                            "Status",
                            width="small",
                            help="⚠️ = Offen, ✓ = Quittiert\n\nKurzformen:\n• km? = Fehlender km-Stand\n• km↓ = km-Stand gesunken\n• L↓ = Verbrauch zu niedrig\n• L↑ = Verbrauch zu hoch"
                        ),
                        "km-Stand": st.column_config.NumberColumn("km-Stand", min_value=0, format="%.0f"),
                        "km gefahren": st.column_config.NumberColumn("km gefahren", format="%.0f"),
                        "Liter": st.column_config.NumberColumn("Liter", min_value=0, format="%.2f"),
                        "L/100km": st.column_config.NumberColumn("L/100km", format="%.1f"),
                        "EUR": st.column_config.NumberColumn("EUR", min_value=0, format="%.2f"),
                    },
                    key="historie_editor"
                )

                # Änderungen erkennen und speichern
                if st.button("Änderungen speichern", type="primary", key="save_historie"):
                    aenderungen = 0
                    for idx, row in edited_df.iterrows():
                        original_id = df_edit.iloc[idx]["_auff_id"]
                        # Originaldaten finden
                        kennzeichen, datum_str, zeit = original_id.split("_")[0], original_id.split("_")[1], "_".join(original_id.split("_")[2:])

                        # In Historie suchen und aktualisieren
                        for i, t in enumerate(historie["tankvorgaenge"]):
                            if (t["kennzeichen"] == kennzeichen and
                                t["datum"] == datum_str and
                                t["zeit"] == zeit):

                                # Prüfen ob Änderungen vorliegen
                                neuer_km = row["km-Stand"]
                                neue_menge = row["Liter"]
                                neuer_betrag = row["EUR"]
                                neue_tankstelle = row["Tankstelle"]

                                if (t["km_stand"] != neuer_km or
                                    t["menge_liter"] != neue_menge or
                                    t["betrag_eur"] != neuer_betrag or
                                    t["tankstelle"] != neue_tankstelle):

                                    historie["tankvorgaenge"][i]["km_stand"] = neuer_km
                                    historie["tankvorgaenge"][i]["menge_liter"] = neue_menge
                                    historie["tankvorgaenge"][i]["betrag_eur"] = neuer_betrag
                                    historie["tankvorgaenge"][i]["tankstelle"] = neue_tankstelle
                                    historie["tankvorgaenge"][i]["verbrauch"] = None  # Wird neu berechnet
                                    aenderungen += 1
                                break

                    if aenderungen > 0:
                        speichere_historie(historie)
                        st.success(f"{aenderungen} Änderung(en) gespeichert!")
                        st.rerun()
                    else:
                        st.info("Keine Änderungen erkannt.")

            else:
                # Kein Bearbeitungsrecht: Nur Anzeige
                df_display_show = df_display.copy()
                df_display_show["datum"] = df_display_show["datum"].dt.strftime("%d.%m.%Y")

                # Auffälligkeits-Typen und Quittierungs-Status als Dictionary
                auff_info_map_ro = {}
                for a in alle_auffaelligkeiten:
                    auff_info_map_ro[a["id"]] = {
                        "typ": a["typ"],
                        "quittiert": a.get("quittiert", False)
                    }

                # Kurzformen für Auffälligkeits-Typen
                AUFF_KURZFORM_RO = {
                    "Fehlender km-Stand": "km?",
                    "km-Stand gesunken": "km↓",
                    "Verbrauch zu niedrig": "L↓",
                    "Verbrauch zu hoch": "L↑"
                }

                # Status-Spalte mit Kurzform (quittierte mit ✓ statt ⚠️)
                def get_status_text_ro(row):
                    if not row["_ist_auffaellig"]:
                        return ""
                    info = auff_info_map_ro.get(row["_auff_id"], {})
                    typ = info.get("typ", "")
                    kurzform = AUFF_KURZFORM_RO.get(typ, "?")
                    if info.get("quittiert", False):
                        return f"✓ {kurzform}"
                    return f"⚠️ {kurzform}"

                df_display_show["Status"] = df_display_show.apply(get_status_text_ro, axis=1)

                df_display_show = df_display_show.rename(columns={
                    "kennzeichen": "Fahrzeug",
                    "datum": "Datum",
                    "zeit": "Zeit",
                    "km_stand": "km-Stand",
                    "km_differenz": "km gefahren",
                    "menge_liter": "Liter",
                    "verbrauch": "L/100km",
                    "betrag_eur": "EUR",
                    "tankstelle": "Tankstelle",
                    "quelldatei": "Quelldatei"
                })

                # Styling-Funktion (rot für offene, grün für quittierte Auffälligkeiten)
                def highlight_row(row):
                    if df_display.loc[row.name, "_ist_auffaellig"]:
                        auff_id = df_display.loc[row.name, "_auff_id"]
                        info = auff_info_map_ro.get(auff_id, {})
                        if info.get("quittiert", False):
                            return ['background-color: #d4edda'] * len(row)  # Grün für quittiert
                        return ['background-color: #ffcccc'] * len(row)  # Rot für offen
                    return [''] * len(row)

                # Anzeige mit Styling
                display_cols = ["Status", "Fahrzeug", "Datum", "Zeit", "km-Stand", "km gefahren", "Liter", "L/100km", "EUR", "Tankstelle", "Quelldatei"]
                if auffaellige_ids:
                    st.dataframe(
                        df_display_show[display_cols].style.apply(highlight_row, axis=1),
                        use_container_width=True
                    )
                else:
                    st.dataframe(df_display_show[display_cols], use_container_width=True)
        else:
            st.info("Keine Daten für die ausgewählten Filter gefunden.")

        # Historie löschen
        st.markdown("---")
        st.markdown("### Daten verwalten")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Historie als CSV exportieren"):
                csv = df_alle.to_csv(index=False)
                st.download_button(
                    "CSV herunterladen",
                    csv,
                    "dkv_historie.csv",
                    "text/csv"
                )

        with col2:
            if aktueller_benutzer_hat_recht("historie_loeschen"):
                if st.button("Gesamte Historie löschen", type="secondary"):
                    st.session_state["confirm_delete"] = True

                if st.session_state.get("confirm_delete"):
                    st.warning("Wirklich alle Daten löschen?")
                    if st.button("Ja, alles löschen!", type="primary"):
                        historie = {"tankvorgaenge": [], "importe": []}
                        speichere_historie(historie)
                        st.session_state["confirm_delete"] = False
                        st.success("Historie gelöscht!")
                        st.rerun()

        # Durchgeführte Importe (am Ende, einklappbar bei > 5 Dateien)
        st.markdown("---")
        if historie["importe"]:
            anzahl_importe = len(historie["importe"])
            if anzahl_importe > 5:
                with st.expander(f"Durchgeführte Importe ({anzahl_importe} Dateien)"):
                    st.dataframe(pd.DataFrame(historie["importe"]), use_container_width=True)
            else:
                st.markdown("### Durchgeführte Importe")
                st.dataframe(pd.DataFrame(historie["importe"]), use_container_width=True)
    else:
        st.info("Noch keine Daten gespeichert.")

# --- TAB 4: Auffälligkeiten ---
with tab4:
    st.subheader("Auffälligkeiten & Korrekturen")

    if alle_auffaelligkeiten:
        # Zusammenfassung - unterscheide quittierte und nicht-quittierte
        nicht_quittiert = [a for a in alle_auffaelligkeiten if not a.get("quittiert", False)]
        quittiert_liste = [a for a in alle_auffaelligkeiten if a.get("quittiert", False)]
        fehler = [a for a in nicht_quittiert if a["schwere"] == "fehler"]
        warnungen = [a for a in nicht_quittiert if a["schwere"] == "warnung"]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Offen", len(nicht_quittiert))
        with col2:
            st.metric("Fehler", len(fehler))
        with col3:
            st.metric("Warnungen", len(warnungen))
        with col4:
            st.metric("Quittiert", len(quittiert_liste))

        st.markdown("---")

        # Auffälligkeiten als Tabelle
        st.markdown("### Übersicht aller Auffälligkeiten")

        auff_df = pd.DataFrame(alle_auffaelligkeiten)

        # Filter-Bereich
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            # Filter nach Fahrzeug
            alle_fahrzeuge_auff = sorted(auff_df["fahrzeug"].unique().tolist())
            fahrzeug_filter_auff = st.selectbox(
                "Nach Fahrzeug filtern",
                ["Alle"] + alle_fahrzeuge_auff,
                key="auff_fahrzeug_filter"
            )
        with col_filter2:
            # Filter für quittierte Einträge
            quittierte_ausblenden = st.checkbox(
                "Quittierte ausblenden",
                value=True,
                key="quittierte_ausblenden"
            )

        # Filter anwenden
        auff_df_filtered = auff_df.copy()
        if fahrzeug_filter_auff != "Alle":
            auff_df_filtered = auff_df_filtered[auff_df_filtered["fahrzeug"] == fahrzeug_filter_auff]
        if quittierte_ausblenden:
            auff_df_filtered = auff_df_filtered[~auff_df_filtered["quittiert"].fillna(False)]

        auff_df_filtered = auff_df_filtered.reset_index(drop=True)

        # Nach Datum und Zeit sortieren (chronologisch)
        auff_df_filtered = auff_df_filtered.sort_values(["datum", "zeit"]).reset_index(drop=True)

        def style_severity_with_quittiert(row_idx, df):
            row = df.iloc[row_idx]
            if row.get("quittiert", False):
                return ['background-color: #d4edda'] * 6  # Grün für quittiert
            elif row["schwere"] == "fehler":
                return ['background-color: #ff9999'] * 6
            else:
                return ['background-color: #ffcc99'] * 6

        if len(auff_df_filtered) > 0:
            # Spalte für Quittierungs-Status hinzufügen
            auff_df_filtered["status"] = auff_df_filtered.apply(
                lambda row: "✓ " + row.get("quittiert_kommentar", "")[:30] if row.get("quittiert", False) else "",
                axis=1
            )

            auff_display = auff_df_filtered[["fahrzeug", "datum", "zeit", "typ", "details", "status"]].rename(columns={
                "fahrzeug": "Fahrzeug",
                "datum": "Datum",
                "zeit": "Zeit",
                "typ": "Problem",
                "details": "Details",
                "status": "Quittiert"
            })

            st.dataframe(
                auff_display.style.apply(
                    lambda x: style_severity_with_quittiert(x.name, auff_df_filtered), axis=1
                ),
                use_container_width=True
            )
        else:
            if quittierte_ausblenden and len(quittiert_liste) > 0:
                st.success(f"Alle Auffälligkeiten wurden quittiert ({len(quittiert_liste)} quittiert).")
            else:
                st.info("Keine Auffälligkeiten vorhanden.")

        # --- Quittierungs-Bereich (nur mit Bearbeitungsrecht) ---
        st.markdown("---")
        st.markdown("### Auffälligkeiten quittieren")

        if aktueller_benutzer_hat_recht("bearbeiten"):
            # Nur nicht-quittierte Auffälligkeiten anzeigen
            nicht_quittierte_df = auff_df[~auff_df["quittiert"].fillna(False)].copy()

            if fahrzeug_filter_auff != "Alle":
                nicht_quittierte_df = nicht_quittierte_df[nicht_quittierte_df["fahrzeug"] == fahrzeug_filter_auff]

            nicht_quittierte_df = nicht_quittierte_df.sort_values(["datum", "zeit"]).reset_index(drop=True)

            if len(nicht_quittierte_df) > 0:
                st.info("Markieren Sie Auffälligkeiten als geprüft, wenn sie erklärt sind (z.B. Mietwagen getankt).")

                # Auswahl der zu quittierenden Auffälligkeit
                quitt_optionen = []
                for idx, row in nicht_quittierte_df.iterrows():
                    quitt_optionen.append(f"{row['fahrzeug']} | {row['datum']} {row['zeit']} | {row['typ']}")

                quitt_auswahl = st.selectbox(
                    "Auffälligkeit auswählen",
                    quitt_optionen,
                    key="quitt_auswahl"
                )

                if quitt_auswahl:
                    # Details der ausgewählten Auffälligkeit anzeigen
                    auswahl_idx = quitt_optionen.index(quitt_auswahl)
                    ausgewaehlte_auff = nicht_quittierte_df.iloc[auswahl_idx]

                    col_detail1, col_detail2 = st.columns(2)
                    with col_detail1:
                        st.markdown(f"**Fahrzeug:** {ausgewaehlte_auff['fahrzeug']}")
                        st.markdown(f"**Datum/Zeit:** {ausgewaehlte_auff['datum']} {ausgewaehlte_auff['zeit']}")
                    with col_detail2:
                        st.markdown(f"**Problem:** {ausgewaehlte_auff['typ']}")
                        st.markdown(f"**Details:** {ausgewaehlte_auff['details']}")

                    # Quittierungs-Formular
                    with st.form("quittieren_form"):
                        quitt_kommentar = st.text_area(
                            "Begründung (Pflichtfeld)",
                            placeholder="z.B. 'Mietwagen getankt', 'Tachofehler bekannt', 'Nachtank nach Panne'...",
                            help="Bitte geben Sie eine Erklärung für die Auffälligkeit an."
                        )

                        quitt_submit = st.form_submit_button("Auffälligkeit quittieren", type="primary")

                        if quitt_submit:
                            if not quitt_kommentar or len(quitt_kommentar.strip()) < 3:
                                st.error("Bitte geben Sie eine Begründung ein (mindestens 3 Zeichen).")
                            else:
                                # Tankvorgang in Historie finden und quittieren
                                auff_id = ausgewaehlte_auff["id"]
                                kennzeichen, datum_str, zeit = auff_id.split("_")[0], auff_id.split("_")[1], "_".join(auff_id.split("_")[2:])

                                for i, t in enumerate(historie["tankvorgaenge"]):
                                    if (t["kennzeichen"] == kennzeichen and
                                        t["datum"] == datum_str and
                                        t["zeit"] == zeit):
                                        historie["tankvorgaenge"][i]["quittiert"] = True
                                        historie["tankvorgaenge"][i]["quittiert_kommentar"] = quitt_kommentar.strip()
                                        historie["tankvorgaenge"][i]["quittiert_von"] = st.session_state.get("username", "")
                                        historie["tankvorgaenge"][i]["quittiert_am"] = datetime.now().strftime("%d.%m.%Y %H:%M")
                                        break

                                speichere_historie(historie)
                                st.success(f"Auffälligkeit quittiert: {ausgewaehlte_auff['typ']}")
                                st.session_state["aktiver_tab"] = 3  # Tab 4: Auffälligkeiten (0-basiert)
                                st.rerun()
            else:
                st.success("Keine offenen Auffälligkeiten zum Quittieren vorhanden.")
        else:
            st.warning("Sie benötigen Bearbeitungsrechte, um Auffälligkeiten quittieren zu können.")

        # --- Korrektur-Bereich (nur mit Bearbeitungsrecht) ---
        st.markdown("---")
        st.markdown("### Auffällige Einträge korrigieren")

        if aktueller_benutzer_hat_recht("bearbeiten"):
            st.info("Doppelklicken Sie auf eine Zelle zum Bearbeiten. Danach 'Änderungen speichern' klicken.")

            # Auffällige Einträge aus Historie laden
            if historie["tankvorgaenge"]:
                df_edit = pd.DataFrame(historie["tankvorgaenge"])
                df_edit["datum"] = pd.to_datetime(df_edit["datum"])
                df_edit["_id"] = df_edit.apply(
                    lambda row: f"{row['kennzeichen']}_{row['datum'].strftime('%Y-%m-%d')}_{row['zeit']}", axis=1
                )

                # Nur auffällige Einträge
                df_auff = df_edit[df_edit["_id"].isin(auffaellige_ids)].copy()

                if len(df_auff) > 0:
                    # Filter für Korrektur-Bereich
                    col_filter1, col_filter2 = st.columns(2)
                    with col_filter1:
                        korr_fahrzeuge = sorted(df_auff["kennzeichen"].unique().tolist())
                        korr_fahrzeug_filter = st.selectbox(
                            "Fahrzeug auswählen",
                            ["Alle"] + korr_fahrzeuge,
                            key="korr_fahrzeug_filter"
                        )
                    with col_filter2:
                        korr_text_filter = st.text_input(
                            "Suche (Tankstelle, Datum...)",
                            key="korr_text_filter",
                            placeholder="Suchbegriff eingeben..."
                        )

                    # Filter anwenden
                    if korr_fahrzeug_filter != "Alle":
                        df_auff = df_auff[df_auff["kennzeichen"] == korr_fahrzeug_filter]

                    if korr_text_filter:
                        suchbegriff = korr_text_filter.lower()
                        df_auff = df_auff[
                            df_auff.apply(lambda row:
                                suchbegriff in str(row["tankstelle"]).lower() or
                                suchbegriff in row["datum"].strftime("%d.%m.%Y") or
                                suchbegriff in str(row.get("quelldatei", "")).lower(),
                                axis=1
                            )
                        ]

                    # Chronologisch sortieren (älteste zuerst)
                    df_auff = df_auff.sort_values(["datum", "zeit"], ascending=True).reset_index(drop=True)

                if len(df_auff) > 0:
                    # Editierbare Tabelle erstellen
                    # Sicherstellen dass km_differenz und verbrauch existieren
                    if "km_differenz" not in df_auff.columns:
                        df_auff["km_differenz"] = None
                    if "verbrauch" not in df_auff.columns:
                        df_auff["verbrauch"] = None

                    df_auff_display = df_auff[["kennzeichen", "datum", "zeit", "km_stand", "km_differenz", "menge_liter", "verbrauch", "betrag_eur", "tankstelle", "_id"]].copy()
                    df_auff_display["datum"] = df_auff_display["datum"].dt.strftime("%d.%m.%Y")
                    df_auff_display = df_auff_display.rename(columns={
                        "kennzeichen": "Fahrzeug",
                        "datum": "Datum",
                        "zeit": "Zeit",
                        "km_stand": "km-Stand",
                        "km_differenz": "km gefahren",
                        "menge_liter": "Liter",
                        "verbrauch": "L/100km",
                        "betrag_eur": "EUR",
                        "tankstelle": "Tankstelle"
                    })

                    edited_auff = st.data_editor(
                        df_auff_display[["Fahrzeug", "Datum", "Zeit", "km-Stand", "km gefahren", "Liter", "L/100km", "EUR", "Tankstelle"]],
                        use_container_width=True,
                        num_rows="fixed",
                        disabled=["Fahrzeug", "Datum", "Zeit", "km gefahren", "L/100km"],  # Berechnete Felder nicht editierbar
                        column_config={
                            "km-Stand": st.column_config.NumberColumn("km-Stand", min_value=0, format="%.0f"),
                            "km gefahren": st.column_config.NumberColumn("km gefahren", format="%.0f"),
                            "Liter": st.column_config.NumberColumn("Liter", min_value=0, format="%.2f"),
                            "L/100km": st.column_config.NumberColumn("L/100km", format="%.1f"),
                            "EUR": st.column_config.NumberColumn("EUR", min_value=0, format="%.2f"),
                        },
                        key="auff_editor"
                    )

                    # Änderungen speichern
                    if st.button("Änderungen speichern", type="primary", key="save_auff"):
                        aenderungen = 0
                        for idx, row in edited_auff.iterrows():
                            original_id = df_auff_display.iloc[idx]["_id"]
                            kennzeichen, datum_str, zeit = original_id.split("_")[0], original_id.split("_")[1], "_".join(original_id.split("_")[2:])

                            for i, t in enumerate(historie["tankvorgaenge"]):
                                if (t["kennzeichen"] == kennzeichen and
                                    t["datum"] == datum_str and
                                    t["zeit"] == zeit):

                                    neuer_km = row["km-Stand"]
                                    neue_menge = row["Liter"]
                                    neuer_betrag = row["EUR"]
                                    neue_tankstelle = row["Tankstelle"]

                                    if (t["km_stand"] != neuer_km or
                                        t["menge_liter"] != neue_menge or
                                        t["betrag_eur"] != neuer_betrag or
                                        t["tankstelle"] != neue_tankstelle):

                                        historie["tankvorgaenge"][i]["km_stand"] = neuer_km
                                        historie["tankvorgaenge"][i]["menge_liter"] = neue_menge
                                        historie["tankvorgaenge"][i]["betrag_eur"] = neuer_betrag
                                        historie["tankvorgaenge"][i]["tankstelle"] = neue_tankstelle
                                        historie["tankvorgaenge"][i]["verbrauch"] = None
                                        aenderungen += 1
                                    break

                        if aenderungen > 0:
                            speichere_historie(historie)
                            st.success(f"{aenderungen} Änderung(en) gespeichert!")
                            st.rerun()
                        else:
                            st.info("Keine Änderungen erkannt.")
                else:
                    st.info("Keine auffälligen Einträge zum Bearbeiten vorhanden.")
        else:
            st.warning("Sie benötigen Bearbeitungsrechte, um Daten korrigieren zu können.")

        # --- Benachrichtigungs-Bereich ---
        st.markdown("---")
        st.markdown("### Besitzer benachrichtigen")

        if aktueller_benutzer_hat_recht("email_senden"):
            # Nur nicht-quittierte Auffälligkeiten für E-Mail-Benachrichtigungen
            offene_auff_fuer_email = [a for a in alle_auffaelligkeiten if not a.get("quittiert", False)]

            # Auffälligkeiten nach Fahrzeug gruppieren
            auff_nach_fahrzeug = {}
            for a in offene_auff_fuer_email:
                if a["fahrzeug"] not in auff_nach_fahrzeug:
                    auff_nach_fahrzeug[a["fahrzeug"]] = []
                auff_nach_fahrzeug[a["fahrzeug"]].append(a)

            # Fahrzeuge mit E-Mail-Adresse finden
            benachrichtigbare = []
            nicht_benachrichtigbare = []

            for kennzeichen, auff_liste in auff_nach_fahrzeug.items():
                besitzer = hole_besitzer_fuer_kennzeichen(fahrzeuge_config, kennzeichen)
                fehler_count = len([a for a in auff_liste if a["schwere"] == "fehler"])
                warn_count = len([a for a in auff_liste if a["schwere"] == "warnung"])

                if besitzer and besitzer.get("besitzer_email"):
                    benachrichtigbare.append({
                        "kennzeichen": kennzeichen,
                        "besitzer_name": besitzer.get("besitzer_name", ""),
                        "besitzer_email": besitzer.get("besitzer_email", ""),
                        "fehler": fehler_count,
                        "warnungen": warn_count,
                        "gesamt": len(auff_liste)
                    })
                else:
                    nicht_benachrichtigbare.append({
                        "kennzeichen": kennzeichen,
                        "fehler": fehler_count,
                        "warnungen": warn_count,
                        "gesamt": len(auff_liste)
                    })

            # Prüfen ob SMTP konfiguriert ist
            smtp_ok = smtp_config.get("server") and smtp_config.get("absender_email")

            if not smtp_ok:
                st.warning("SMTP-Server nicht vollständig konfiguriert. Bitte im Tab 'Einstellungen' konfigurieren.")

            if benachrichtigbare:
                st.markdown("**Fahrzeuge mit hinterlegter E-Mail-Adresse:**")

                # Tabelle der benachrichtigbaren Fahrzeuge
                df_benachrichtig = pd.DataFrame(benachrichtigbare)
                df_benachrichtig_display = df_benachrichtig.rename(columns={
                    "kennzeichen": "Kennzeichen",
                    "besitzer_name": "Besitzer",
                    "besitzer_email": "E-Mail",
                    "fehler": "Fehler",
                    "warnungen": "Warnungen",
                    "gesamt": "Gesamt"
                })
                st.dataframe(df_benachrichtig_display, use_container_width=True)

                # Multiselect für Auswahl
                auswahl_optionen = [f"{b['kennzeichen']} - {b['besitzer_name']}" for b in benachrichtigbare]
                auswahl = st.multiselect(
                    "Fahrzeuge für Benachrichtigung auswählen:",
                    auswahl_optionen,
                    default=auswahl_optionen
                )

                if auswahl and smtp_ok:
                    if st.button("E-Mail-Benachrichtigungen senden", type="primary"):
                        erfolge = 0
                        fehler_liste = []

                        for auswahl_item in auswahl:
                            kennzeichen = auswahl_item.split(" - ")[0]
                            # Besitzer-Daten finden
                            for b in benachrichtigbare:
                                if b["kennzeichen"] == kennzeichen:
                                    # E-Mail erstellen
                                    auff_fuer_fahrzeug = auff_nach_fahrzeug[kennzeichen]
                                    email_vorlage = lade_email_vorlage()
                                    html_body = erstelle_auffaelligkeiten_email(
                                        b["besitzer_name"],
                                        kennzeichen,
                                        auff_fuer_fahrzeug,
                                        email_vorlage
                                    )
                                    betreff = erstelle_email_betreff(kennzeichen, auff_fuer_fahrzeug, email_vorlage)

                                    # E-Mail senden
                                    erfolg, nachricht = sende_benachrichtigung(
                                        smtp_config,
                                        b["besitzer_email"],
                                        betreff,
                                        html_body
                                    )

                                    if erfolg:
                                        erfolge += 1
                                    else:
                                        fehler_liste.append(f"{kennzeichen}: {nachricht}")
                                    break

                        if erfolge > 0:
                            st.success(f"{erfolge} E-Mail(s) erfolgreich gesendet!")
                        if fehler_liste:
                            st.error("Fehler beim Senden:\n" + "\n".join(fehler_liste))
                elif not smtp_ok:
                    st.info("Bitte zuerst SMTP-Server im Tab 'Einstellungen' konfigurieren.")

            if nicht_benachrichtigbare:
                st.markdown("**Fahrzeuge ohne E-Mail-Adresse:**")
                df_nicht = pd.DataFrame(nicht_benachrichtigbare)
                df_nicht_display = df_nicht.rename(columns={
                    "kennzeichen": "Kennzeichen",
                    "fehler": "Fehler",
                    "warnungen": "Warnungen",
                    "gesamt": "Gesamt"
                })
                st.dataframe(df_nicht_display, use_container_width=True)
                st.info("Für diese Fahrzeuge kann keine E-Mail gesendet werden. Bitte im Tab 'Einstellungen' Besitzer-Daten hinterlegen.")

            if not benachrichtigbare and not nicht_benachrichtigbare:
                st.info("Keine Fahrzeuge mit Auffälligkeiten gefunden.")
        else:
            st.warning("Sie benötigen entsprechende Rechte, um Benachrichtigungen zu versenden.")
    else:
        st.success("Keine Auffälligkeiten gefunden! Alle Daten sind in Ordnung.")

# --- TAB 5: Einstellungen ---
with tab5:
    # Dynamische Sub-Tabs basierend auf Rechten
    sub_tab_namen = []
    ist_eingeloggt = st.session_state["logged_in"] and not st.session_state.get("muss_passwort_aendern", False)

    # Admin-Tabs nur wenn eingeloggt und berechtigt
    if ist_eingeloggt:
        if aktueller_benutzer_hat_recht("fahrzeuge_verwalten"):
            sub_tab_namen.append("🚗 Fahrzeuge")
        if aktueller_benutzer_hat_recht("smtp_config") or aktueller_benutzer_hat_recht("vorlage_config"):
            sub_tab_namen.append("📧 E-Mail")
        if aktueller_benutzer_hat_recht("benutzer_verwalten"):
            sub_tab_namen.append("👥 Benutzer")
        if aktueller_benutzer_hat_recht("datensicherung"):
            sub_tab_namen.append("💾 Datensicherung")

    # "Über" ist immer sichtbar (auch ohne Login)
    sub_tab_namen.append("ℹ️ Über")

    sub_tabs = st.tabs(sub_tab_namen)
    tab_index = 0

    # === FAHRZEUGE ===
    if ist_eingeloggt and aktueller_benutzer_hat_recht("fahrzeuge_verwalten"):
        with sub_tabs[tab_index]:
            st.markdown("#### Fahrzeug-Verwaltung")
            st.markdown("Ordnen Sie Kennzeichen den jeweiligen Besitzern zu, um E-Mail-Benachrichtigungen zu ermöglichen.")
            alle_kennzeichen = hole_alle_kennzeichen_aus_historie(historie)
            if alle_kennzeichen:
                fahrzeug_liste = []
                for kennzeichen in alle_kennzeichen:
                    besitzer = hole_besitzer_fuer_kennzeichen(fahrzeuge_config, kennzeichen)
                    if besitzer:
                        fahrzeug_liste.append({
                            "kennzeichen": kennzeichen,
                            "besitzer_name": besitzer.get("besitzer_name", ""),
                            "besitzer_email": besitzer.get("besitzer_email", ""),
                            "verbrauch_min": besitzer.get("verbrauch_min", 3.0),
                            "verbrauch_max": besitzer.get("verbrauch_max", 25.0),
                            "notizen": besitzer.get("notizen", "")
                        })
                    else:
                        fahrzeug_liste.append({
                            "kennzeichen": kennzeichen,
                            "besitzer_name": "",
                            "besitzer_email": "",
                            "verbrauch_min": 3.0,
                            "verbrauch_max": 25.0,
                            "notizen": ""
                        })
                df_fahrzeuge = pd.DataFrame(fahrzeug_liste)
                nicht_zugeordnet = len([f for f in fahrzeug_liste if not f["besitzer_email"]])
                if nicht_zugeordnet > 0:
                    st.warning(f"{nicht_zugeordnet} Fahrzeug(e) ohne E-Mail-Adresse")
                st.markdown("**Verbrauchsgrenzen:** Warnungen werden ausgelöst wenn der Verbrauch außerhalb des angegebenen Bereichs liegt.")
                df_fahrzeuge_display = df_fahrzeuge.rename(columns={
                    "kennzeichen": "Kennzeichen",
                    "besitzer_name": "Besitzer-Name",
                    "besitzer_email": "E-Mail",
                    "verbrauch_min": "Min L/100km",
                    "verbrauch_max": "Max L/100km",
                    "notizen": "Notizen"
                })
                edited_fahrzeuge = st.data_editor(
                    df_fahrzeuge_display,
                    use_container_width=True,
                    num_rows="fixed",
                    disabled=["Kennzeichen"],
                    column_config={
                        "Kennzeichen": st.column_config.TextColumn("Kennzeichen", width="small"),
                        "Besitzer-Name": st.column_config.TextColumn("Besitzer-Name", width="medium"),
                        "E-Mail": st.column_config.TextColumn("E-Mail", width="medium"),
                        "Min L/100km": st.column_config.NumberColumn("Min L/100km", min_value=0.0, max_value=50.0, step=0.5, format="%.1f", width="small"),
                        "Max L/100km": st.column_config.NumberColumn("Max L/100km", min_value=0.0, max_value=100.0, step=0.5, format="%.1f", width="small"),
                        "Notizen": st.column_config.TextColumn("Notizen", width="medium")
                    },
                    key="fahrzeuge_editor"
                )
                if st.button("Fahrzeug-Daten speichern", type="primary", key="save_fahrzeuge"):
                    neue_fahrzeuge = {"fahrzeuge": []}
                    for idx, row in edited_fahrzeuge.iterrows():
                        neue_fahrzeuge["fahrzeuge"].append({
                            "kennzeichen": row["Kennzeichen"],
                            "besitzer_name": row["Besitzer-Name"] if pd.notna(row["Besitzer-Name"]) else "",
                            "besitzer_email": row["E-Mail"] if pd.notna(row["E-Mail"]) else "",
                            "verbrauch_min": float(row["Min L/100km"]) if pd.notna(row["Min L/100km"]) else 3.0,
                            "verbrauch_max": float(row["Max L/100km"]) if pd.notna(row["Max L/100km"]) else 25.0,
                            "notizen": row["Notizen"] if pd.notna(row["Notizen"]) else ""
                        })
                    speichere_fahrzeuge(neue_fahrzeuge)
                    st.success("Fahrzeug-Daten gespeichert!")
                    st.rerun()
            else:
                st.info("Noch keine Fahrzeuge in der Historie. Importieren Sie zuerst DKV-Daten.")
        tab_index += 1

    # === E-MAIL (SMTP + Vorlage kombiniert) ===
    if ist_eingeloggt and (aktueller_benutzer_hat_recht("smtp_config") or aktueller_benutzer_hat_recht("vorlage_config")):
        with sub_tabs[tab_index]:
            email_sub_namen = []
            if aktueller_benutzer_hat_recht("smtp_config"):
                email_sub_namen.append("Server-Einstellungen")
            if aktueller_benutzer_hat_recht("vorlage_config"):
                email_sub_namen.append("Vorlage")
            if len(email_sub_namen) > 1:
                email_sub_tabs = st.tabs(email_sub_namen)
                email_tab_idx = 0
                if aktueller_benutzer_hat_recht("smtp_config"):
                    with email_sub_tabs[email_tab_idx]:
                        st.markdown("#### SMTP-Server")
                        col1, col2 = st.columns(2)
                        with col1:
                            smtp_server = st.text_input("Server", value=smtp_config.get("server", ""), key="smtp_server")
                            smtp_port = st.number_input("Port", value=smtp_config.get("port", 587), min_value=1, max_value=65535, key="smtp_port")
                            smtp_benutzer = st.text_input("Benutzername", value=smtp_config.get("benutzer", ""), key="smtp_benutzer")
                            smtp_passwort = st.text_input("Passwort", value=smtp_config.get("passwort", ""), type="password", key="smtp_passwort")
                        with col2:
                            smtp_absender_name = st.text_input("Absender-Name", value=smtp_config.get("absender_name", "DKV Checker"), key="smtp_absender_name")
                            smtp_absender_email = st.text_input("Absender-E-Mail", value=smtp_config.get("absender_email", ""), key="smtp_absender_email")
                            smtp_tls = st.checkbox("TLS verwenden", value=smtp_config.get("tls", True), key="smtp_tls")
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("Verbindung testen", key="test_smtp"):
                                test_config = {"server": smtp_server, "port": int(smtp_port), "benutzer": smtp_benutzer, "passwort": smtp_passwort, "tls": smtp_tls}
                                erfolg, nachricht = teste_smtp_verbindung(test_config)
                                if erfolg:
                                    st.success(nachricht)
                                else:
                                    st.error(nachricht)
                        with col_btn2:
                            if st.button("Speichern", type="primary", key="save_smtp"):
                                neue_smtp_config = {"server": smtp_server, "port": int(smtp_port), "benutzer": smtp_benutzer, "passwort": smtp_passwort, "absender_name": smtp_absender_name, "absender_email": smtp_absender_email, "tls": smtp_tls}
                                speichere_smtp_config(neue_smtp_config)
                                st.success("Gespeichert!")
                                st.rerun()
                        with st.expander("Hilfe: Gängige SMTP-Einstellungen"):
                            st.markdown("""
| Anbieter | Server | Port |
|----------|--------|------|
| Gmail | smtp.gmail.com | 587 |
| Microsoft 365 | smtp.office365.com | 587 |
| Web.de | smtp.web.de | 587 |
| GMX | mail.gmx.net | 587 |
""")
                        email_tab_idx += 1
                if aktueller_benutzer_hat_recht("vorlage_config"):
                    with email_sub_tabs[email_tab_idx]:
                        st.markdown("#### E-Mail-Vorlage")
                        email_vorlage = lade_email_vorlage()
                        with st.expander("Verfügbare Platzhalter"):
                            st.markdown("`{besitzer_name}` `{kennzeichen}` `{anzahl_gesamt}` `{anzahl_fehler}` `{anzahl_warnungen}` `{datum_heute}`")
                        vorlage_betreff = st.text_input("Betreff", value=email_vorlage.get("betreff", DEFAULT_EMAIL_VORLAGE["betreff"]), key="vorlage_betreff")
                        vorlage_anrede = st.text_input("Anrede", value=email_vorlage.get("anrede", DEFAULT_EMAIL_VORLAGE["anrede"]), key="vorlage_anrede")
                        vorlage_einleitung = st.text_area("Einleitung", value=email_vorlage.get("einleitung", DEFAULT_EMAIL_VORLAGE["einleitung"]), key="vorlage_einleitung", height=80)
                        vorlage_abschluss = st.text_area("Abschluss", value=email_vorlage.get("abschluss", DEFAULT_EMAIL_VORLAGE["abschluss"]), key="vorlage_abschluss", height=80)
                        vorlage_fusszeile = st.text_input("Fußzeile", value=email_vorlage.get("fusszeile", DEFAULT_EMAIL_VORLAGE["fusszeile"]), key="vorlage_fusszeile")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Vorlage speichern", type="primary", key="save_vorlage"):
                                neue_vorlage = {"betreff": vorlage_betreff, "anrede": vorlage_anrede, "einleitung": vorlage_einleitung, "abschluss": vorlage_abschluss, "fusszeile": vorlage_fusszeile}
                                speichere_email_vorlage(neue_vorlage)
                                st.success("Gespeichert!")
                                st.rerun()
                        with col2:
                            if st.button("Standard wiederherstellen", key="reset_vorlage"):
                                speichere_email_vorlage(DEFAULT_EMAIL_VORLAGE.copy())
                                st.success("Wiederhergestellt!")
                                st.rerun()
                        with st.expander("Vorschau"):
                            beispiel_auff = [{"datum": "15.01.2026", "zeit": "08:30", "typ": "Verbrauch zu hoch", "details": "28.5 L/100km", "schwere": "fehler"}]
                            beispiel_vorlage = {"betreff": vorlage_betreff, "anrede": vorlage_anrede, "einleitung": vorlage_einleitung, "abschluss": vorlage_abschluss, "fusszeile": vorlage_fusszeile}
                            st.components.v1.html(erstelle_auffaelligkeiten_email("Max Mustermann", "B-XY 1234", beispiel_auff, beispiel_vorlage), height=400, scrolling=True)
            else:
                if aktueller_benutzer_hat_recht("smtp_config"):
                    st.markdown("#### SMTP-Server")
                    col1, col2 = st.columns(2)
                    with col1:
                        smtp_server = st.text_input("Server", value=smtp_config.get("server", ""), key="smtp_server")
                        smtp_port = st.number_input("Port", value=smtp_config.get("port", 587), min_value=1, max_value=65535, key="smtp_port")
                        smtp_benutzer = st.text_input("Benutzername", value=smtp_config.get("benutzer", ""), key="smtp_benutzer")
                        smtp_passwort = st.text_input("Passwort", value=smtp_config.get("passwort", ""), type="password", key="smtp_passwort")
                    with col2:
                        smtp_absender_name = st.text_input("Absender-Name", value=smtp_config.get("absender_name", "DKV Checker"), key="smtp_absender_name")
                        smtp_absender_email = st.text_input("Absender-E-Mail", value=smtp_config.get("absender_email", ""), key="smtp_absender_email")
                        smtp_tls = st.checkbox("TLS verwenden", value=smtp_config.get("tls", True), key="smtp_tls")
                    if st.button("Speichern", type="primary", key="save_smtp"):
                        neue_smtp_config = {"server": smtp_server, "port": int(smtp_port), "benutzer": smtp_benutzer, "passwort": smtp_passwort, "absender_name": smtp_absender_name, "absender_email": smtp_absender_email, "tls": smtp_tls}
                        speichere_smtp_config(neue_smtp_config)
                        st.success("Gespeichert!")
                        st.rerun()
                if aktueller_benutzer_hat_recht("vorlage_config"):
                    st.markdown("#### E-Mail-Vorlage")
                    email_vorlage = lade_email_vorlage()
                    vorlage_betreff = st.text_input("Betreff", value=email_vorlage.get("betreff", DEFAULT_EMAIL_VORLAGE["betreff"]), key="vorlage_betreff")
                    vorlage_anrede = st.text_input("Anrede", value=email_vorlage.get("anrede", DEFAULT_EMAIL_VORLAGE["anrede"]), key="vorlage_anrede")
                    vorlage_einleitung = st.text_area("Einleitung", value=email_vorlage.get("einleitung", DEFAULT_EMAIL_VORLAGE["einleitung"]), key="vorlage_einleitung", height=80)
                    vorlage_abschluss = st.text_area("Abschluss", value=email_vorlage.get("abschluss", DEFAULT_EMAIL_VORLAGE["abschluss"]), key="vorlage_abschluss", height=80)
                    vorlage_fusszeile = st.text_input("Fußzeile", value=email_vorlage.get("fusszeile", DEFAULT_EMAIL_VORLAGE["fusszeile"]), key="vorlage_fusszeile")
                    if st.button("Vorlage speichern", type="primary", key="save_vorlage"):
                        neue_vorlage = {"betreff": vorlage_betreff, "anrede": vorlage_anrede, "einleitung": vorlage_einleitung, "abschluss": vorlage_abschluss, "fusszeile": vorlage_fusszeile}
                        speichere_email_vorlage(neue_vorlage)
                        st.success("Gespeichert!")
                        st.rerun()
        tab_index += 1

    # === BENUTZER ===
    if ist_eingeloggt and aktueller_benutzer_hat_recht("benutzer_verwalten"):
        with sub_tabs[tab_index]:
            benutzer_sub = st.tabs(["Übersicht", "Bearbeiten", "Neu anlegen"])
            benutzer_daten = lade_benutzer()
            benutzer_liste = benutzer_daten.get("benutzer", [])
            with benutzer_sub[0]:
                if benutzer_liste:
                    benutzer_df = pd.DataFrame([{
                        "Benutzer": b["benutzername"],
                        "Name": b.get("name", ""),
                        "Rolle": ROLLEN.get(b.get("rolle", "viewer"), {}).get("name", ""),
                        "Aktiv": "Ja" if b.get("aktiv", True) else "Nein"
                    } for b in benutzer_liste])
                    st.dataframe(benutzer_df, use_container_width=True)
                with st.expander("Rollen-Übersicht"):
                    st.markdown("""
| Rolle | Rechte |
|-------|--------|
| Administrator | Vollzugriff |
| Manager | Import, Bearbeiten, E-Mails, Fahrzeuge |
| Betrachter | Nur Lesen |
""")
            with benutzer_sub[1]:
                if benutzer_liste:
                    benutzer_auswahl = st.selectbox("Benutzer", [b["benutzername"] for b in benutzer_liste], key="benutzer_auswahl")
                    if benutzer_auswahl:
                        ausgewaehlter = finde_benutzer(benutzer_auswahl)
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_name = st.text_input("Name", value=ausgewaehlter.get("name", ""), key="edit_name")
                            edit_email = st.text_input("E-Mail", value=ausgewaehlter.get("email", ""), key="edit_email")
                            edit_rolle = st.selectbox("Rolle", list(ROLLEN.keys()), index=list(ROLLEN.keys()).index(ausgewaehlter.get("rolle", "viewer")), format_func=lambda x: ROLLEN[x]["name"], key="edit_rolle")
                        with col2:
                            edit_aktiv = st.checkbox("Aktiv", value=ausgewaehlter.get("aktiv", True), key="edit_aktiv")
                            edit_pw_reset = st.checkbox("Passwort-Änderung erzwingen", value=ausgewaehlter.get("muss_passwort_aendern", False), key="edit_pw_reset")
                            neues_pw = st.text_input("Neues Passwort (leer = unverändert)", type="password", key="edit_neues_pw")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Speichern", type="primary", key="save_benutzer"):
                                updates = {"name": edit_name, "email": edit_email, "rolle": edit_rolle, "aktiv": edit_aktiv, "muss_passwort_aendern": edit_pw_reset}
                                if neues_pw:
                                    if len(neues_pw) < 6:
                                        st.error("Mind. 6 Zeichen")
                                    else:
                                        updates["passwort_hash"] = hash_passwort(neues_pw)
                                        aktualisiere_benutzer(benutzer_auswahl, updates)
                                        st.success("Gespeichert!")
                                        st.rerun()
                                else:
                                    aktualisiere_benutzer(benutzer_auswahl, updates)
                                    st.success("Gespeichert!")
                                    st.rerun()
                        with col2:
                            if benutzer_auswahl.lower() != st.session_state["username"].lower():
                                if st.button("Löschen", type="secondary", key="delete_benutzer"):
                                    erfolg, msg = loesche_benutzer(benutzer_auswahl)
                                    if erfolg:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
            with benutzer_sub[2]:
                with st.form("neuer_benutzer_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        neu_name = st.text_input("Benutzername", key="neu_benutzername")
                        neu_anzeigename = st.text_input("Name", key="neu_name")
                        neu_email = st.text_input("E-Mail", key="neu_email")
                    with col2:
                        neu_pw = st.text_input("Passwort", type="password", key="neu_passwort")
                        neu_rolle = st.selectbox("Rolle", list(ROLLEN.keys()), format_func=lambda x: ROLLEN[x]["name"], key="neu_rolle")
                    if st.form_submit_button("Erstellen", type="primary"):
                        if not neu_name:
                            st.error("Benutzername erforderlich")
                        elif len(neu_pw) < 6:
                            st.error("Passwort mind. 6 Zeichen")
                        else:
                            erfolg, msg = erstelle_benutzer(neu_name, neu_pw, neu_rolle, neu_anzeigename, neu_email)
                            if erfolg:
                                st.success(f"'{neu_name}' erstellt!")
                                st.rerun()
                            else:
                                st.error(msg)
        tab_index += 1

    # === DATENSICHERUNG ===
    if ist_eingeloggt and aktueller_benutzer_hat_recht("datensicherung"):
        with sub_tabs[tab_index]:
            st.markdown("#### Datensicherung & Wiederherstellung")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("##### 📥 Backup erstellen")
                st.markdown("""
Erstellt eine ZIP-Datei mit allen Konfigurationsdaten:
- **historie.json** - Alle Tankvorgänge
- **fahrzeuge.json** - Fahrzeug-Besitzer-Zuordnung
- **smtp_config.json** - E-Mail-Servereinstellungen
- **email_vorlage.json** - E-Mail-Vorlagen
- **benutzer.json** - Benutzerkonten
""")
                if st.button("🔽 Backup erstellen", type="primary", key="btn_backup"):
                    backup_bytes, backup_name = erstelle_backup()
                    st.download_button(
                        label=f"📦 {backup_name} herunterladen",
                        data=backup_bytes,
                        file_name=backup_name,
                        mime="application/zip",
                        key="download_backup"
                    )
                    st.success("Backup erfolgreich erstellt!")

            with col2:
                st.markdown("##### 📤 Backup wiederherstellen")
                st.warning("⚠️ **Achtung:** Die Wiederherstellung überschreibt alle bestehenden Daten!")

                uploaded_zip = st.file_uploader(
                    "ZIP-Datei hochladen",
                    type=["zip"],
                    key="backup_upload"
                )

                if uploaded_zip:
                    bestaetigung = st.checkbox(
                        "Ich bestätige, dass alle bestehenden Daten überschrieben werden sollen",
                        key="backup_bestaetigung"
                    )

                    if st.button("🔄 Wiederherstellen", type="primary", disabled=not bestaetigung, key="btn_restore"):
                        erfolg, meldung = stelle_backup_wieder_her(uploaded_zip.getvalue())
                        if erfolg:
                            st.success(f"✅ {meldung}")
                            st.info("Bitte laden Sie die Seite neu, um die wiederhergestellten Daten zu sehen.")
                            st.rerun()
                        else:
                            st.error(f"❌ {meldung}")
        tab_index += 1

    # === ÜBER ===
    with sub_tabs[tab_index]:
        st.markdown("#### Über diese Software")
        st.markdown("""
**DKV Abrechnungs-Checker**

Analyse von DKV-Tankkartenabrechnungen mit automatischer Erkennung von Auffälligkeiten im Kraftstoffverbrauch.

**Funktionen:**
- Import von DKV-Abrechnungen (CSV und PDF)
- Automatische Verbrauchsberechnung
- Erkennung von Anomalien (ungewöhnlicher Verbrauch, sinkende km-Stände)
- E-Mail-Benachrichtigung an Fahrzeughalter
- Mehrbenutzersystem mit Rollen
""")
        st.markdown("---")
        st.markdown("#### Entwicklung unterstützen")
        st.markdown("""
Diese Software ist **kostenlos** und wird in der Freizeit entwickelt.

Wenn Ihnen die Software gefällt und Sie die Weiterentwicklung unterstützen möchten,
freue ich mich über eine kleine Spende:
""")
        st.link_button(
            "☕ Mit PayPal unterstützen",
            "https://www.paypal.com/paypalme/christiansauer87",
            type="primary"
        )

        st.markdown("---")
        st.markdown("#### 🔒 Datenschutz")
        with st.expander("Datenschutzhinweise anzeigen"):
            st.markdown("""
**Welche Daten werden verarbeitet?**
- Fahrzeug-Kennzeichen und Tankvorgänge (aus DKV-Abrechnungen)
- Namen und E-Mail-Adressen von Fahrzeugbesitzern (falls hinterlegt)
- Benutzerkonten (Benutzername, Name, E-Mail, Rolle)
- SMTP-Zugangsdaten für E-Mail-Versand (falls konfiguriert)

**Wo werden die Daten gespeichert?**
- Alle Daten werden **ausschließlich lokal** auf dem Server/Computer gespeichert,
  auf dem diese Software betrieben wird.
- Es erfolgt **keine Übermittlung** an externe Server oder Dritte.
- Datenformat: JSON-Dateien im Programmverzeichnis bzw. Docker-Volume.

**Datensicherheit**
- Benutzer-Passwörter werden mit PBKDF2-SHA256 gehasht (nicht im Klartext gespeichert)
- Zugriff nur nach Anmeldung mit Benutzer/Passwort
- Rollenbasierte Zugriffskontrolle

**Verantwortlichkeit (DSGVO)**
- **Verantwortlicher** im Sinne der DSGVO ist die Organisation/Firma, die diese Software betreibt
  – nicht der Software-Entwickler.
- Der Betreiber ist verpflichtet:
  - Betroffene Personen (Mitarbeiter/Fahrzeugnutzer) über die Datenverarbeitung zu informieren
  - Die Verarbeitung im Verarbeitungsverzeichnis zu dokumentieren
  - Auskunfts- und Löschungsanfragen zu bearbeiten

**Empfehlungen für Betreiber**
- Informieren Sie Ihre Mitarbeiter über die Nutzung dieser Software
- Nehmen Sie die Verarbeitung in Ihr Verarbeitungsverzeichnis auf
- Sichern Sie die Daten regelmäßig (JSON-Dateien oder CSV-Export)
- Beschränken Sie den Zugriff auf berechtigte Personen

**Kontakt**
Bei Fragen zum Datenschutz dieser Software wenden Sie sich an den
Datenschutzbeauftragten Ihrer Organisation.
""")

        st.markdown("---")
        st.caption("© 2025 Christian Sauer")

# --- TAB 6: Hilfe ---
with tab6:
    st.markdown("## 📖 Benutzerhandbuch")
    st.markdown("---")

    # Inhaltsverzeichnis
    st.markdown("""
### Inhaltsverzeichnis
1. [Überblick](#überblick)
2. [Erste Schritte](#erste-schritte)
3. [Import & Analyse](#import-analyse)
4. [Verbrauchsentwicklung](#verbrauchsentwicklung)
5. [Historie](#historie)
6. [Auffälligkeiten](#auffälligkeiten)
7. [Einstellungen](#einstellungen)
8. [Häufige Fragen](#häufige-fragen)
""")

    st.markdown("---")

    # Überblick
    st.markdown("""
### Überblick

Der **DKV Abrechnungs-Checker** ist eine Anwendung zur Analyse von DKV-Tankkartenabrechnungen.
Die Software erkennt automatisch Auffälligkeiten im Kraftstoffverbrauch und hilft bei der
Kontrolle der Tankkartennutzung.

**Hauptfunktionen:**
- 📤 Import von DKV-Abrechnungen (CSV und PDF)
- 📊 Visualisierung der Verbrauchsentwicklung
- 📚 Vollständige Historie aller Tankvorgänge
- ⚠️ Automatische Erkennung von Auffälligkeiten
- 📧 E-Mail-Benachrichtigung an Fahrzeughalter
- 👥 Mehrbenutzersystem mit Rollen
""")

    st.markdown("---")

    # Erste Schritte
    st.markdown("""
### Erste Schritte

#### 1. Anmeldung
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
1. Gehen Sie zum Tab "📤 Import & Analyse"
2. Laden Sie eine DKV-Abrechnungsdatei hoch (CSV oder PDF)
3. Die Daten werden automatisch analysiert und gespeichert
""")

    st.markdown("---")

    # Import & Analyse
    st.markdown("""
### Import & Analyse

#### Unterstützte Dateiformate

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
3. Automatische Duplikatsprüfung:
   - Bereits importierte Dateien werden erkannt
   - Doppelte Tankvorgänge werden übersprungen
4. Neue Daten werden sofort in der Historie gespeichert

#### Was wird importiert?
- Kennzeichen des Fahrzeugs
- Datum und Uhrzeit
- Kilometerstand
- Getankte Menge (Liter)
- Betrag (EUR)
- Tankstelle und Warenart
""")

    st.markdown("---")

    # Verbrauchsentwicklung
    st.markdown("""
### Verbrauchsentwicklung

Dieser Tab zeigt die **grafische Auswertung** des Kraftstoffverbrauchs.

#### Filteroptionen
- **Zeitraum:** Von-Bis-Datumsauswahl
- **Fahrzeug:** Einzelnes Fahrzeug oder alle

#### Diagramme
- **Verbrauch über Zeit:** Zeigt den Verbrauch (L/100km) pro Tankvorgang
- **Monatliche Aggregation:** Durchschnittsverbrauch pro Monat
- Interaktive Altair-Charts mit Zoom und Tooltips

#### Interpretation
- Konstanter Verbrauch = normaler Betrieb
- Plötzliche Spitzen = mögliche Auffälligkeit
- Saisonale Schwankungen sind normal (Winter/Sommer)
""")

    st.markdown("---")

    # Historie
    st.markdown("""
### Historie

Die **vollständige Übersicht** aller importierten Tankvorgänge.

#### Filteroptionen
- **Fahrzeug:** Nach Kennzeichen filtern
- **Zeitraum:** Von-Bis-Datumsauswahl
- **Quelldatei:** Nach Import-Datei filtern
- **Textsuche:** Suche in Tankstelle, Datum, Quelldatei

#### Tabellenspalten
| Spalte | Beschreibung |
|--------|--------------|
| Datum / Zeit | Zeitpunkt der Tankung |
| Kennzeichen | Fahrzeug-Kennzeichen |
| km-Stand | Aktueller Kilometerstand |
| km gefahren | Differenz zum vorherigen Tankvorgang |
| Liter | Getankte Menge |
| L/100km | Berechneter Verbrauch |
| EUR | Rechnungsbetrag |
| Tankstelle | Ort der Tankung |
| Status | Auffälligkeiten (⚠️ offen, ✓ quittiert) |

#### Status-Symbole
- `⚠️ km?` = Fehlender Kilometerstand
- `⚠️ km↓` = Kilometerstand gesunken
- `⚠️ L↓` = Verbrauch zu niedrig
- `⚠️ L↑` = Verbrauch zu hoch
- `✓` = Quittiert (mit grünem Hintergrund)

#### Daten bearbeiten
Nach Anmeldung (je nach Rolle) können Sie:
- Kilometerstände korrigieren
- Litermengen anpassen
- Beträge ändern
- Änderungen werden automatisch gespeichert

#### Daten exportieren
- Klicken Sie auf "Als CSV exportieren"
- Gefilterte Daten werden heruntergeladen
""")

    st.markdown("---")

    # Auffälligkeiten
    st.markdown("""
### Auffälligkeiten

Hier werden **automatisch erkannte Probleme** angezeigt.

#### Erkannte Auffälligkeiten

| Typ | Beschreibung | Schwere |
|-----|--------------|---------|
| **Fehlender km-Stand** | Tankvorgang ohne Kilometerangabe | ⚠️ Warnung |
| **km-Stand gesunken** | Aktueller Stand niedriger als vorheriger | 🔴 Fehler |
| **Verbrauch zu niedrig** | Unter Minimalwert (Standard: 3 L/100km) | ⚠️ Warnung |
| **Verbrauch zu hoch** | Über Maximalwert (Standard: 25 L/100km) | 🔴 Fehler |

#### Fahrzeugspezifische Grenzwerte
In den Einstellungen können pro Fahrzeug individuelle Verbrauchsgrenzen definiert werden
(z.B. für Transporter höhere Werte).

#### Auffälligkeiten quittieren
1. Wählen Sie eine Auffälligkeit aus
2. Geben Sie einen **Kommentar** ein (Pflichtfeld)
   - z.B. "Mietwagen getankt", "Werkstattfahrt", "km-Stand nachträglich korrigiert"
3. Klicken Sie auf "Quittieren"
4. Quittierte Auffälligkeiten werden ausgeblendet (Filter "Quittierte ausblenden")

#### E-Mail-Benachrichtigung
- Pro Fahrzeug kann ein Besitzer mit E-Mail hinterlegt werden
- Klicken Sie auf "Benachrichtigung senden" um den Besitzer zu informieren
- Es werden nur offene (nicht quittierte) Auffälligkeiten gemeldet
""")

    st.markdown("---")

    # Einstellungen
    st.markdown("""
### Einstellungen

#### 🚗 Fahrzeuge
Hier verwalten Sie die Fahrzeug-Stammdaten:
- **Besitzer-Name:** Name des Fahrzeughalters
- **E-Mail:** Für Benachrichtigungen
- **Verbrauchsgrenzen:** Min/Max L/100km pro Fahrzeug
- **Notizen:** Zusätzliche Informationen

#### 📧 E-Mail
**Server-Einstellungen:**
- SMTP-Server und Port konfigurieren
- Zugangsdaten eingeben
- TLS-Verschlüsselung aktivieren
- Verbindung testen

**Gängige SMTP-Server:**
| Anbieter | Server | Port |
|----------|--------|------|
| Gmail | smtp.gmail.com | 587 |
| Microsoft 365 | smtp.office365.com | 587 |
| Web.de | smtp.web.de | 587 |
| GMX | mail.gmx.net | 587 |

**E-Mail-Vorlage:**
- Betreff und Text anpassen
- Platzhalter verwenden: `{besitzer_name}`, `{kennzeichen}`, `{anzahl_gesamt}`, etc.
- Vorschau der E-Mail anzeigen

#### 👥 Benutzer (nur Admin)
- Benutzer anlegen, bearbeiten, löschen
- Rollen zuweisen
- Passwörter zurücksetzen
- Konten aktivieren/deaktivieren
""")

    st.markdown("---")

    # Häufige Fragen
    st.markdown("""
### Häufige Fragen

**F: Warum wird der Verbrauch nicht berechnet?**
> Der Verbrauch kann nur berechnet werden, wenn der aktuelle UND der vorherige Tankvorgang
> einen gültigen Kilometerstand haben. Beim ersten Tankvorgang eines Fahrzeugs ist daher
> noch kein Verbrauch verfügbar.

**F: Warum werden manche Tankvorgänge nicht importiert?**
> Die Duplikatsprüfung verhindert doppelte Einträge. Wenn Kennzeichen, Datum und Uhrzeit
> bereits existieren, wird der Vorgang übersprungen.

**F: Was bedeutet "km-Stand gesunken"?**
> Der aktuelle Kilometerstand ist niedriger als beim vorherigen Tankvorgang.
> Mögliche Ursachen:
> - Falscher Eintrag an der Tankstelle
> - Verschiedene Personen haben unterschiedliche Werte eingegeben
> - Tachomanipulation (selten)

**F: Welche Verbrauchswerte sind normal?**
> - PKW Benzin: 6-10 L/100km
> - PKW Diesel: 5-8 L/100km
> - Transporter: 8-15 L/100km
> - LKW: 15-35 L/100km

**F: Wie kann ich eine Auffälligkeit ignorieren?**
> Quittieren Sie die Auffälligkeit mit einem erklärenden Kommentar.
> Sie wird dann standardmäßig ausgeblendet und nicht mehr per E-Mail gemeldet.

**F: Werden AdBlue-Tankungen ausgewertet?**
> Nein, der Verbrauch wird nur für Kraftstoffe berechnet (Diesel, Super, Benzin, Euro).
> AdBlue-Tankvorgänge werden importiert, aber nicht in die Verbrauchsberechnung einbezogen.

**F: Kann ich die Daten sichern?**
> Ja, exportieren Sie regelmäßig die Historie als CSV-Datei.
> Alternativ sichern Sie die JSON-Dateien im Programmverzeichnis:
> - `historie.json` (Tankvorgänge)
> - `fahrzeuge.json` (Fahrzeug-Stammdaten)
> - `benutzer.json` (Benutzerkonten)
""")

    st.markdown("---")

    # Datenschutz
    st.markdown("""
### Datenschutz & DSGVO

**Wichtiger Hinweis:** Der **Betreiber** dieser Software (Ihre Organisation/Firma) ist
der Verantwortliche im Sinne der DSGVO – nicht der Software-Entwickler.

**Gespeicherte Daten:**
- Fahrzeug-Kennzeichen und Tankvorgänge
- Namen und E-Mail-Adressen (Fahrzeugbesitzer, Benutzer)
- Anmeldedaten (Passwörter werden gehasht gespeichert)

**Speicherort:**
- Alle Daten werden **ausschließlich lokal** gespeichert
- Keine Übermittlung an externe Server oder Dritte
- Datenformat: JSON-Dateien im Programmverzeichnis

**Pflichten des Betreibers:**
- Mitarbeiter/Fahrzeugnutzer über die Verarbeitung informieren
- Verarbeitung im Verarbeitungsverzeichnis dokumentieren
- Auskunfts- und Löschungsanfragen bearbeiten

Ausführliche Datenschutzhinweise finden Sie unter **Einstellungen → Über → Datenschutzhinweise**.
""")

    st.markdown("---")

    # Kontakt
    st.markdown("""
### Kontakt & Unterstützung

Bei Fragen oder Problemen wenden Sie sich an den Administrator Ihrer Organisation.

---

**Software-Version:** 1.0
**Entwicklung:** Christian Sauer

Diese Software ist kostenlos. Wenn Sie die Weiterentwicklung unterstützen möchten:
""")
    st.link_button(
        "☕ Mit PayPal unterstützen",
        "https://www.paypal.com/paypalme/christiansauer87",
        type="secondary"
    )

# --- Tab-Navigation nach Aktionen ---
# JavaScript-Workaround um nach st.rerun() zum gewünschten Tab zu springen
if st.session_state.get("aktiver_tab") is not None:
    tab_index = st.session_state["aktiver_tab"]
    st.session_state["aktiver_tab"] = None  # Zurücksetzen
    components.html(f"""
        <script>
            setTimeout(() => {{
                const tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
                if (tabs.length > {tab_index}) {{
                    tabs[{tab_index}].click();
                }}
            }}, 100);
        </script>
    """, height=0)
