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

# Mehrsprachigkeit importieren
from i18n import SPRACHEN, t

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
if "sprache" not in st.session_state:
    st.session_state["sprache"] = "de"

# Hilfsfunktion für Übersetzungen mit aktueller Sprache
def _(key, **kwargs):
    """Kurzform für t() mit automatischer Sprachauswahl aus Session State"""
    return t(key, st.session_state.get("sprache", "de"), **kwargs)

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

def speichere_manuellen_tankvorgang(historie, eintrag):
    """Speichert einen manuell erfassten Tankvorgang"""
    eintrag["quelldatei"] = "MANUELL"
    # Quittierungs-Felder initialisieren
    eintrag["quittiert"] = False
    eintrag["quittiert_kommentar"] = ""
    eintrag["quittiert_von"] = ""
    eintrag["quittiert_am"] = ""
    historie["tankvorgaenge"].append(eintrag)
    speichere_historie(historie)
    return True

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
    # Sprachauswahl
    st.selectbox(
        "🌐",
        list(SPRACHEN.keys()),
        format_func=lambda x: SPRACHEN[x],
        key="sprache",
        label_visibility="collapsed"
    )
    st.markdown("---")

    st.markdown(f"### {_('login.benutzer')}")

    if st.session_state["logged_in"]:
        # Passwort-Änderung erforderlich?
        if st.session_state.get("muss_passwort_aendern", False):
            st.warning(_("login.bitte_aendern"))
            with st.form("passwort_aendern_form"):
                neues_passwort = st.text_input(_("login.neues_passwort"), type="password")
                neues_passwort_bestaetigen = st.text_input(_("login.passwort_bestaetigen"), type="password")
                pw_submitted = st.form_submit_button(_("login.passwort_aendern"))

                if pw_submitted:
                    if len(neues_passwort) < 6:
                        st.error(_("login.mind_6_zeichen"))
                    elif neues_passwort != neues_passwort_bestaetigen:
                        st.error(_("login.passwort_ungleich"))
                    else:
                        aktualisiere_benutzer(st.session_state["username"], {
                            "passwort_hash": hash_passwort(neues_passwort),
                            "muss_passwort_aendern": False
                        })
                        st.session_state["muss_passwort_aendern"] = False
                        st.success(_("login.passwort_geaendert"))
                        st.rerun()
        else:
            # Normale Anzeige
            rolle_key = st.session_state["user_rolle"]
            rolle_name = _("rollen." + rolle_key) if rolle_key in ["admin", "manager", "viewer"] else rolle_key
            anzeige_name = st.session_state.get("user_name") or st.session_state["username"]
            st.success(_("login.angemeldet_als", name=anzeige_name))
            st.caption(_("login.rolle", rolle=rolle_name))

            # Passwort ändern (optional)
            with st.expander(_("login.passwort_aendern")):
                with st.form("passwort_optional_form"):
                    aktuelles_pw = st.text_input(_("login.aktuelles_passwort"), type="password", key="pw_aktuell")
                    neues_pw = st.text_input(_("login.neues_passwort"), type="password", key="pw_neu")
                    neues_pw_best = st.text_input(_("login.passwort_bestaetigen"), type="password", key="pw_best")
                    pw_opt_submitted = st.form_submit_button(_("login.passwort_aendern"))

                    if pw_opt_submitted:
                        benutzer = finde_benutzer(st.session_state["username"])
                        if not pruefe_passwort(aktuelles_pw, benutzer.get("passwort_hash", "")):
                            st.error(_("login.passwort_falsch"))
                        elif len(neues_pw) < 6:
                            st.error(_("login.mind_6_zeichen"))
                        elif neues_pw != neues_pw_best:
                            st.error(_("login.passwort_ungleich"))
                        else:
                            aktualisiere_benutzer(st.session_state["username"], {
                                "passwort_hash": hash_passwort(neues_pw)
                            })
                            st.success(_("login.passwort_geaendert"))

            if st.button(_("login.abmelden")):
                st.session_state["logged_in"] = False
                st.session_state["username"] = ""
                st.session_state["user_rolle"] = ""
                st.session_state["user_name"] = ""
                st.session_state["muss_passwort_aendern"] = False
                st.rerun()
    else:
        with st.form("login_form"):
            username = st.text_input(_("login.benutzername"))
            password = st.text_input(_("login.passwort"), type="password")
            submitted = st.form_submit_button(_("login.anmelden"))

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
                    st.error(_("login.ungueltige_daten"))

    st.markdown("---")
    st.markdown(f"### {_('sidebar.info')}")
    if st.session_state["logged_in"]:
        rolle = st.session_state["user_rolle"]
        if rolle in ["admin", "manager", "viewer"]:
            st.info(_("rollen." + rolle + "_desc"))
    else:
        st.info(_("sidebar.anmelden_info"))

    # Spenden-Hinweis
    st.markdown("---")
    spende_text = _("sidebar.spende_text")
    spende_link = _("sidebar.spende_link")
    st.markdown(
        f"""
        <div style="text-align: center; padding: 10px; background-color: #f0f2f6; border-radius: 5px;">
            <small>{spende_text}<br>
            <a href="https://www.paypal.com/paypalme/christiansauer87" target="_blank">☕ {spende_link}</a></small>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- Hauptanwendung ---

st.title(_("app_title"))

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
    f"📤 {_('tabs.import')}",
    f"📊 {_('tabs.verbrauch')}",
    f"📚 {_('tabs.historie')}",
    f"⚠️ {_('tabs.auffaelligkeiten')} ({len(offene_auffaelligkeiten)})",
    f"⚙️ {_('tabs.einstellungen')}",
    f"📖 {_('tabs.hilfe')}"
])

# --- TAB 1: Import & Analyse ---
with tab1:
    uploaded_files = st.file_uploader(
        _("import.upload_label"),
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
            st.warning(f"**{_('import.bereits_importiert', count=len(bereits_importiert))}** {_('import.werden_uebersprungen')}: {', '.join(bereits_importiert)}")

        if not neue_dateien:
            st.info(_("import.alle_importiert"))
        else:
            # Status-Anzeige
            st.info(f"**{_('import.neue_dateien', count=len(neue_dateien))}**")

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
                            import_fehler.append(f"{uploaded_file.name}: {_('import.keine_daten_pdf')}")
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

                st.subheader(_("import.rohdaten"))
                st.dataframe(df_alle_roh, use_container_width=True)

            if alle_daten:
                # Alle Kraftstoffdaten zusammenführen
                df_fuel_combined = pd.concat([df for _, df in alle_daten], ignore_index=True)
                df_fuel_combined = berechne_verbrauch(df_fuel_combined)

                # --- Verbrauchsanalyse ---
                st.subheader(_("import.verbrauchsanalyse"))

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
                st.subheader(_("import.zusammenfassung"))
                if ergebnisse:
                    st.dataframe(pd.DataFrame(ergebnisse), use_container_width=True)

                # Warnungen
                st.subheader(_("import.warnungen"))
                if warnungen:
                    warn_df = pd.DataFrame(warnungen)
                    st.dataframe(warn_df.style.apply(lambda x: ['background-color: #ffcccc'] * len(x), axis=1),
                                use_container_width=True)
                    st.warning(_("import.auffaelligkeiten_gefunden", count=len(warnungen)))
                else:
                    st.success(_("import.keine_auffaelligkeiten"))

                # --- Automatisches Speichern ---
                st.subheader(_("import.import_status"))

                if not kann_importieren:
                    st.info(_("import.keine_berechtigung"))
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
                        st.metric(_("import.neue_tankvorgaenge"), neue_vorgaenge_gesamt)
                    with col2:
                        st.metric(_("import.dateien_importiert"), len(importierte_dateien))
                    with col3:
                        st.metric(_("import.duplikate_uebersprungen"), duplikate_gesamt)

                    if neue_vorgaenge_gesamt > 0:
                        st.success(_("import.import_erfolgreich", count=neue_vorgaenge_gesamt, files=len(importierte_dateien)))
                        st.caption(f"☕ [{_('sidebar.spende_link')}](https://www.paypal.com/paypalme/christiansauer87)")
                    elif duplikate_gesamt > 0:
                        st.info(_("import.alle_duplikate"))

                    # Liste der importierten Dateien
                    with st.expander(_("import.importierte_anzeigen")):
                        for dateiname in importierte_dateien:
                            st.write(f"- {dateiname}")

    else:
        st.info(_("import.upload_info"))

    # --- Manueller Tankvorgang ---
    st.markdown("---")
    st.subheader(_("manual.titel"))

    if aktueller_benutzer_hat_recht("importieren"):
        with st.expander(_("manual.expander")):
            # Alle Kennzeichen aus Historie und Fahrzeug-Config sammeln
            alle_kennzeichen_manuell = set(hole_alle_kennzeichen_aus_historie(historie))
            for fz in fahrzeuge_config.get("fahrzeuge", []):
                alle_kennzeichen_manuell.add(fz["kennzeichen"])
            alle_kennzeichen_manuell = sorted(list(alle_kennzeichen_manuell))

            with st.form("manueller_tankvorgang"):
                col1, col2 = st.columns(2)

                with col1:
                    # Fahrzeug-Auswahl mit Option für neues Kennzeichen
                    kennzeichen_optionen = [_("manual.neues_kennzeichen")] + alle_kennzeichen_manuell
                    kennzeichen_auswahl = st.selectbox(
                        _("manual.fahrzeug"),
                        kennzeichen_optionen,
                        key="manual_kennzeichen_select"
                    )
                    neues_kennzeichen = st.text_input(
                        _("manual.kennzeichen_input"),
                        placeholder="AB-CD 123",
                        key="manual_neues_kennzeichen"
                    )

                    manual_datum = st.date_input(_("manual.datum"), key="manual_datum")
                    manual_zeit = st.time_input(_("manual.uhrzeit"), key="manual_zeit")
                    manual_km_stand = st.number_input(
                        _("manual.km_stand"),
                        min_value=0,
                        step=1,
                        key="manual_km_stand"
                    )

                with col2:
                    manual_menge = st.number_input(
                        _("manual.menge"),
                        min_value=0.0,
                        step=0.1,
                        format="%.2f",
                        key="manual_menge"
                    )
                    manual_betrag = st.number_input(
                        _("manual.betrag"),
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                        key="manual_betrag"
                    )
                    manual_tankstelle = st.text_input(
                        _("manual.tankstelle"),
                        placeholder="z.B. ARAL Hamburg",
                        key="manual_tankstelle"
                    )
                    manual_warenart = st.selectbox(
                        _("manual.warenart"),
                        ["DIESEL", "SUPER", "BENZIN", "EURO SUPER"],
                        key="manual_warenart"
                    )

                manual_zahlungsart = st.selectbox(
                    _("manual.zahlungsart"),
                    [_("manual.zahlungsart_privat"), _("manual.zahlungsart_firma"), _("manual.zahlungsart_sonstige")],
                    key="manual_zahlungsart"
                )
                manual_notiz = st.text_area(
                    _("manual.notiz"),
                    placeholder="z.B. Tankstelle ohne DKV-Akzeptanz",
                    key="manual_notiz"
                )

                if st.form_submit_button(_("manual.speichern"), type="primary"):
                    # Kennzeichen bestimmen
                    if kennzeichen_auswahl == _("manual.neues_kennzeichen"):
                        final_kennzeichen = neues_kennzeichen.strip().upper()
                    else:
                        final_kennzeichen = kennzeichen_auswahl

                    # Validierung
                    fehler = []
                    if not final_kennzeichen:
                        fehler.append(_("manual.fehler_kennzeichen"))
                    if manual_menge <= 0:
                        fehler.append(_("manual.fehler_menge"))
                    if manual_km_stand <= 0:
                        fehler.append(_("manual.fehler_km"))

                    # Duplikatsprüfung
                    datum_str = manual_datum.strftime("%Y-%m-%d")
                    zeit_str = manual_zeit.strftime("%H:%M")
                    ist_duplikat = any(
                        t["kennzeichen"] == final_kennzeichen and
                        t["datum"] == datum_str and
                        t["zeit"] == zeit_str
                        for t in historie["tankvorgaenge"]
                    )
                    if ist_duplikat:
                        fehler.append(_("manual.fehler_duplikat"))

                    if fehler:
                        for f in fehler:
                            st.error(f)
                    else:
                        # Eintrag erstellen
                        eintrag = {
                            "kennzeichen": final_kennzeichen,
                            "datum": datum_str,
                            "zeit": zeit_str,
                            "km_stand": manual_km_stand,
                            "menge_liter": manual_menge,
                            "verbrauch": None,  # Wird beim Speichern automatisch berechnet
                            "km_differenz": None,
                            "betrag_eur": manual_betrag,
                            "tankstelle": manual_tankstelle,
                            "warenart": manual_warenart,
                            "zahlungsart": manual_zahlungsart,
                            "notiz": manual_notiz
                        }

                        speichere_manuellen_tankvorgang(historie, eintrag)
                        st.success(_("manual.erfolg", kennzeichen=final_kennzeichen, datum=manual_datum.strftime('%d.%m.%Y')))
                        st.rerun()
    else:
        st.info(_("manual.keine_berechtigung"))

# --- TAB 2: Verbrauchsentwicklung ---
with tab2:
    st.subheader(_("verbrauch.titel"))

    # Daten erst nach Login anzeigen
    if not st.session_state["logged_in"]:
        st.info(_("sidebar.anmelden_info"))
    elif historie["tankvorgaenge"]:
        df_historie = pd.DataFrame(historie["tankvorgaenge"])
        df_historie["datum"] = pd.to_datetime(df_historie["datum"])
        df_historie = df_historie.sort_values(["datum", "zeit"])

        # Filter für gültige Verbrauchswerte
        df_chart = df_historie[df_historie["verbrauch"].notna()].copy()
        df_chart = df_chart[(df_chart["verbrauch"] > 3) & (df_chart["verbrauch"] < 25)]

        if len(df_chart) > 0:
            # Filter-Bereich
            st.markdown(f"#### {_('verbrauch.filter')}")

            # Datumsbereich ermitteln
            min_datum = df_chart["datum"].min().date()
            max_datum = df_chart["datum"].max().date()

            col_filter1, col_filter2, col_filter3 = st.columns([1, 1, 2])
            with col_filter1:
                start_datum = st.date_input(
                    _("verbrauch.von"),
                    value=min_datum,
                    min_value=min_datum,
                    max_value=max_datum,
                    key="verbrauch_start_datum"
                )
            with col_filter2:
                end_datum = st.date_input(
                    _("verbrauch.bis"),
                    value=max_datum,
                    min_value=min_datum,
                    max_value=max_datum,
                    key="verbrauch_end_datum"
                )
            with col_filter3:
                # Fahrzeugauswahl
                alle_fahrzeuge = df_chart["kennzeichen"].unique().tolist()
                ausgewaehlte = st.multiselect(
                    _("verbrauch.fahrzeuge"),
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
                st.markdown(f"### {_('verbrauch.pro_tankvorgang')}")

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
                st.markdown(f"### {_('verbrauch.monatlich')}")

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
                st.markdown(f"### {_('verbrauch.kosten')}")

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
                st.markdown(f"### {_('verbrauch.statistik')}")

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
                    st.info(_("verbrauch.fahrzeug_waehlen"))
                else:
                    st.warning(_("verbrauch.keine_daten_zeitraum"))
        else:
            st.warning(_("verbrauch.keine_daten"))
    else:
        st.info(_("verbrauch.keine_historie"))

# --- TAB 3: Historie ---
with tab3:
    st.subheader(_("historie.titel"))

    # Daten erst nach Login anzeigen
    if not st.session_state["logged_in"]:
        st.info(_("sidebar.anmelden_info"))
    elif historie["tankvorgaenge"]:
        df_alle = pd.DataFrame(historie["tankvorgaenge"])
        df_alle["datum"] = pd.to_datetime(df_alle["datum"])
        df_alle = df_alle.sort_values(["datum", "zeit"], ascending=False)

        # Alle Tankvorgänge
        st.markdown(f"### {_('historie.alle_tankvorgaenge')}")

        # Filter
        col1, col2, col3 = st.columns(3)
        with col1:
            fahrzeug_filter = st.selectbox(
                _("historie.filter_fahrzeug"),
                [_("historie.alle")] + df_alle["kennzeichen"].unique().tolist()
            )
        with col2:
            zeitraum = st.selectbox(
                _("historie.filter_zeitraum"),
                [_("historie.alle"), _("historie.letzte_30"), _("historie.letzte_90"), _("historie.letztes_jahr")]
            )
        with col3:
            # Quelldatei-Filter
            quelldateien = df_alle["quelldatei"].dropna().unique().tolist()
            quelldateien = [q for q in quelldateien if q]  # Leere entfernen
            datei_filter = st.selectbox(
                _("historie.filter_quelldatei"),
                [_("historie.alle")] + quelldateien
            )

        df_display = df_alle.copy()

        if fahrzeug_filter != _("historie.alle"):
            df_display = df_display[df_display["kennzeichen"] == fahrzeug_filter]

        if zeitraum != _("historie.alle"):
            heute = pd.Timestamp.now()
            if zeitraum == _("historie.letzte_30"):
                df_display = df_display[df_display["datum"] >= heute - pd.Timedelta(days=30)]
            elif zeitraum == _("historie.letzte_90"):
                df_display = df_display[df_display["datum"] >= heute - pd.Timedelta(days=90)]
            elif zeitraum == _("historie.letztes_jahr"):
                df_display = df_display[df_display["datum"] >= heute - pd.Timedelta(days=365)]

        if datei_filter != _("historie.alle"):
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
                st.info(_("historie.bearbeiten_info"))

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
                        st.success(_("historie.aenderungen_gespeichert", count=aenderungen))
                        st.rerun()
                    else:
                        st.info(_("historie.keine_aenderungen"))

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
            st.info(_("historie.keine_daten"))

        # Historie löschen
        st.markdown("---")
        st.markdown(f"### {_('historie.daten_verwalten')}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(_("historie.csv_export")):
                csv = df_alle.to_csv(index=False)
                st.download_button(
                    _("historie.csv_download"),
                    csv,
                    "dkv_historie.csv",
                    "text/csv"
                )

        with col2:
            if aktueller_benutzer_hat_recht("historie_loeschen"):
                if st.button(_("historie.historie_loeschen"), type="secondary"):
                    st.session_state["confirm_delete"] = True

                if st.session_state.get("confirm_delete"):
                    st.warning(_("historie.bestaetigen"))
                    if st.button(_("historie.ja_loeschen"), type="primary"):
                        historie = {"tankvorgaenge": [], "importe": []}
                        speichere_historie(historie)
                        st.session_state["confirm_delete"] = False
                        st.success(_("historie.geloescht"))
                        st.rerun()

        # Durchgeführte Importe (am Ende, einklappbar bei > 5 Dateien)
        st.markdown("---")
        if historie["importe"]:
            anzahl_importe = len(historie["importe"])
            if anzahl_importe > 5:
                with st.expander(f"{_('historie.importe')} ({_('historie.importe_dateien', count=anzahl_importe)})"):
                    st.dataframe(pd.DataFrame(historie["importe"]), use_container_width=True)
            else:
                st.markdown(f"### {_('historie.importe')}")
                st.dataframe(pd.DataFrame(historie["importe"]), use_container_width=True)
    else:
        st.info(_("historie.keine_daten_gespeichert"))

# --- TAB 4: Auffälligkeiten ---
with tab4:
    st.subheader(_("auffaelligkeiten.titel"))

    # Daten erst nach Login anzeigen
    if not st.session_state["logged_in"]:
        st.info(_("sidebar.anmelden_info"))
    elif alle_auffaelligkeiten:
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
        st.markdown(f"### {_('auffaelligkeiten.uebersicht')}")

        auff_df = pd.DataFrame(alle_auffaelligkeiten)

        # Filter-Bereich
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            # Filter nach Fahrzeug
            alle_fahrzeuge_auff = sorted(auff_df["fahrzeug"].unique().tolist())
            fahrzeug_filter_auff = st.selectbox(
                _("auffaelligkeiten.filter_fahrzeug"),
                [_("historie.alle")] + alle_fahrzeuge_auff,
                key="auff_fahrzeug_filter"
            )
        with col_filter2:
            # Filter für quittierte Einträge
            quittierte_ausblenden = st.checkbox(
                _("auffaelligkeiten.quittierte_ausblenden"),
                value=True,
                key="quittierte_ausblenden"
            )

        # Filter anwenden
        auff_df_filtered = auff_df.copy()
        if fahrzeug_filter_auff != _("historie.alle"):
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
                "fahrzeug": _("spalten.fahrzeug"),
                "datum": _("spalten.datum"),
                "zeit": _("spalten.zeit"),
                "typ": _("spalten.problem"),
                "details": _("spalten.details"),
                "status": _("spalten.quittiert")
            })

            st.dataframe(
                auff_display.style.apply(
                    lambda x: style_severity_with_quittiert(x.name, auff_df_filtered), axis=1
                ),
                use_container_width=True
            )
        else:
            if quittierte_ausblenden and len(quittiert_liste) > 0:
                st.success(_("auffaelligkeiten.alle_quittiert", count=len(quittiert_liste)))
            else:
                st.info(_("auffaelligkeiten.keine_vorhanden"))

        # --- Quittierungs-Bereich (nur mit Bearbeitungsrecht) ---
        st.markdown("---")
        st.markdown(f"### {_('auffaelligkeiten.quittieren_titel')}")

        if aktueller_benutzer_hat_recht("bearbeiten"):
            # Nur nicht-quittierte Auffälligkeiten anzeigen
            nicht_quittierte_df = auff_df[~auff_df["quittiert"].fillna(False)].copy()

            if fahrzeug_filter_auff != _("historie.alle"):
                nicht_quittierte_df = nicht_quittierte_df[nicht_quittierte_df["fahrzeug"] == fahrzeug_filter_auff]

            nicht_quittierte_df = nicht_quittierte_df.sort_values(["datum", "zeit"]).reset_index(drop=True)

            if len(nicht_quittierte_df) > 0:
                st.info(_("auffaelligkeiten.quittieren_info"))

                # Auswahl der zu quittierenden Auffälligkeit
                quitt_optionen = []
                for idx, row in nicht_quittierte_df.iterrows():
                    quitt_optionen.append(f"{row['fahrzeug']} | {row['datum']} {row['zeit']} | {row['typ']}")

                quitt_auswahl = st.selectbox(
                    _("auffaelligkeiten.auswahl"),
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

                        quitt_submit = st.form_submit_button(_("auffaelligkeiten.quittieren_button"), type="primary")

                        if quitt_submit:
                            if not quitt_kommentar or len(quitt_kommentar.strip()) < 3:
                                st.error(_("auffaelligkeiten.begruendung_fehler"))
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
                                st.success(_("auffaelligkeiten.quittiert_erfolg", typ=ausgewaehlte_auff['typ']))
                                st.session_state["aktiver_tab"] = 3  # Tab 4: Auffälligkeiten (0-basiert)
                                st.rerun()
            else:
                st.success(_("auffaelligkeiten.keine_offenen"))
        else:
            st.warning(_("auffaelligkeiten.keine_berechtigung_quittieren"))

        # --- Korrektur-Bereich (nur mit Bearbeitungsrecht) ---
        st.markdown("---")
        st.markdown(f"### {_('auffaelligkeiten.korrigieren_titel')}")

        if aktueller_benutzer_hat_recht("bearbeiten"):
            st.info(_("auffaelligkeiten.korrigieren_info"))

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
                            _("auffaelligkeiten.fahrzeug_auswaehlen"),
                            [_("historie.alle")] + korr_fahrzeuge,
                            key="korr_fahrzeug_filter"
                        )
                    with col_filter2:
                        korr_text_filter = st.text_input(
                            _("auffaelligkeiten.filter_suche"),
                            key="korr_text_filter",
                            placeholder=_("auffaelligkeiten.suchbegriff_eingeben")
                        )

                    # Filter anwenden
                    if korr_fahrzeug_filter != _("historie.alle"):
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
                            st.success(_("historie.aenderungen_gespeichert", count=aenderungen))
                            st.rerun()
                        else:
                            st.info(_("historie.keine_aenderungen"))
                else:
                    st.info(_("auffaelligkeiten.keine_auffaellig"))
        else:
            st.warning(_("auffaelligkeiten.keine_berechtigung_korrigieren"))

        # --- Benachrichtigungs-Bereich ---
        st.markdown("---")
        st.markdown(f"### {_('auffaelligkeiten.benachrichtigen_titel')}")

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
                st.warning(_("auffaelligkeiten.smtp_nicht_konfiguriert"))

            if benachrichtigbare:
                st.markdown(f"**{_('auffaelligkeiten.mit_email')}**")

                # Tabelle der benachrichtigbaren Fahrzeuge
                df_benachrichtig = pd.DataFrame(benachrichtigbare)
                df_benachrichtig_display = df_benachrichtig.rename(columns={
                    "kennzeichen": _("spalten.kennzeichen"),
                    "besitzer_name": _("spalten.besitzer"),
                    "besitzer_email": _("spalten.email"),
                    "fehler": _("allgemein.fehler"),
                    "warnungen": _("allgemein.warnung"),
                    "gesamt": _("allgemein.gesamt")
                })
                st.dataframe(df_benachrichtig_display, use_container_width=True)

                # Multiselect für Auswahl
                auswahl_optionen = [f"{b['kennzeichen']} - {b['besitzer_name']}" for b in benachrichtigbare]
                auswahl = st.multiselect(
                    _("auffaelligkeiten.auswahl_benachrichtigen"),
                    auswahl_optionen,
                    default=auswahl_optionen
                )

                if auswahl and smtp_ok:
                    if st.button(_("auffaelligkeiten.email_senden"), type="primary"):
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
                            st.success(_("auffaelligkeiten.email_erfolg", count=erfolge))
                        if fehler_liste:
                            st.error(_("auffaelligkeiten.email_fehler") + "\n" + "\n".join(fehler_liste))
                elif not smtp_ok:
                    st.info(_("auffaelligkeiten.smtp_konfigurieren"))

            if nicht_benachrichtigbare:
                st.markdown(f"**{_('auffaelligkeiten.ohne_email')}**")
                df_nicht = pd.DataFrame(nicht_benachrichtigbare)
                df_nicht_display = df_nicht.rename(columns={
                    "kennzeichen": _("spalten.kennzeichen"),
                    "fehler": _("allgemein.fehler"),
                    "warnungen": _("allgemein.warnung"),
                    "gesamt": _("allgemein.gesamt")
                })
                st.dataframe(df_nicht_display, use_container_width=True)
                st.info(_("auffaelligkeiten.ohne_email_info"))

            if not benachrichtigbare and not nicht_benachrichtigbare:
                st.info(_("auffaelligkeiten.keine_mit_auff"))
        else:
            st.warning(_("auffaelligkeiten.keine_berechtigung_email"))
    else:
        st.success(_("auffaelligkeiten.keine_auffaelligkeiten"))

# --- TAB 5: Einstellungen ---
with tab5:
    # Dynamische Sub-Tabs basierend auf Rechten
    sub_tab_namen = []
    ist_eingeloggt = st.session_state["logged_in"] and not st.session_state.get("muss_passwort_aendern", False)

    # Admin-Tabs nur wenn eingeloggt und berechtigt
    if ist_eingeloggt:
        if aktueller_benutzer_hat_recht("fahrzeuge_verwalten"):
            sub_tab_namen.append(f"🚗 {_('einstellungen.fahrzeuge')}")
        if aktueller_benutzer_hat_recht("smtp_config") or aktueller_benutzer_hat_recht("vorlage_config"):
            sub_tab_namen.append(f"📧 {_('einstellungen.email')}")
        if aktueller_benutzer_hat_recht("benutzer_verwalten"):
            sub_tab_namen.append(f"👥 {_('einstellungen.benutzer')}")
        if aktueller_benutzer_hat_recht("datensicherung"):
            sub_tab_namen.append(f"💾 {_('einstellungen.datensicherung')}")

    # "Über" ist immer sichtbar (auch ohne Login)
    sub_tab_namen.append(f"ℹ️ {_('einstellungen.ueber')}")

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
            benutzer_daten = lade_benutzer()
            benutzer_liste = benutzer_daten.get("benutzer", [])

            # Erfolgsmeldung nach Rerun anzeigen
            if "benutzer_erstellt_meldung" in st.session_state:
                st.success(_("einstellungen.benutzer_erstellt", name=st.session_state["benutzer_erstellt_meldung"]))
                del st.session_state["benutzer_erstellt_meldung"]

            # Neuen Benutzer anlegen (oben)
            with st.expander(f"➕ {_('einstellungen.neu_anlegen')}", expanded=False):
                with st.form("neuer_benutzer_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        neu_name = st.text_input(_("einstellungen.benutzername"), key="neu_benutzername")
                        neu_anzeigename = st.text_input(_("einstellungen.name"), key="neu_name")
                        neu_email = st.text_input(_("einstellungen.email"), key="neu_email")
                    with col2:
                        neu_pw = st.text_input(_("einstellungen.passwort"), type="password", key="neu_passwort")
                        neu_rolle = st.selectbox(_("einstellungen.rolle"), list(ROLLEN.keys()), format_func=lambda x: ROLLEN[x]["name"], key="neu_rolle")
                    if st.form_submit_button(_("einstellungen.erstellen"), type="primary"):
                        if not neu_name:
                            st.error(_("einstellungen.benutzername_erforderlich"))
                        elif len(neu_pw) < 6:
                            st.error(_("einstellungen.passwort_min_zeichen"))
                        else:
                            erfolg, msg = erstelle_benutzer(neu_name, neu_pw, neu_rolle, neu_anzeigename, neu_email)
                            if erfolg:
                                st.session_state["benutzer_erstellt_meldung"] = neu_name
                                st.rerun()
                            else:
                                st.error(msg)

            st.markdown("---")

            # Benutzerliste mit Bearbeiten/Löschen-Buttons
            if benutzer_liste:
                for idx, benutzer in enumerate(benutzer_liste):
                    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
                    with col1:
                        st.write(f"**{benutzer['benutzername']}**")
                    with col2:
                        st.write(benutzer.get("name", "-"))
                    with col3:
                        rolle_name = ROLLEN.get(benutzer.get("rolle", "viewer"), {}).get("name", "")
                        aktiv_status = "✓" if benutzer.get("aktiv", True) else "✗"
                        st.write(f"{rolle_name} ({aktiv_status})")
                    with col4:
                        if st.button("✏️", key=f"edit_{idx}", help=_("einstellungen.bearbeiten")):
                            st.session_state["benutzer_bearbeiten"] = benutzer["benutzername"]
                    with col5:
                        # Nicht den eigenen Account oder letzten Admin löschen
                        kann_loeschen = benutzer["benutzername"].lower() != st.session_state.get("username", "").lower()
                        if kann_loeschen:
                            if st.button("🗑️", key=f"del_{idx}", help=_("einstellungen.loeschen")):
                                erfolg, msg = loesche_benutzer(benutzer["benutzername"])
                                if erfolg:
                                    st.rerun()
                                else:
                                    st.error(msg)

                # Bearbeiten-Dialog
                if "benutzer_bearbeiten" in st.session_state:
                    benutzer_auswahl = st.session_state["benutzer_bearbeiten"]
                    ausgewaehlter = finde_benutzer(benutzer_auswahl)
                    if ausgewaehlter:
                        st.markdown("---")
                        st.markdown(f"#### {_('einstellungen.bearbeiten')}: {benutzer_auswahl}")
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_name = st.text_input(_("einstellungen.name"), value=ausgewaehlter.get("name", ""), key="edit_name")
                            edit_email = st.text_input(_("einstellungen.email"), value=ausgewaehlter.get("email", ""), key="edit_email")
                            edit_rolle = st.selectbox(_("einstellungen.rolle"), list(ROLLEN.keys()), index=list(ROLLEN.keys()).index(ausgewaehlter.get("rolle", "viewer")), format_func=lambda x: ROLLEN[x]["name"], key="edit_rolle")
                        with col2:
                            edit_aktiv = st.checkbox(_("einstellungen.aktiv"), value=ausgewaehlter.get("aktiv", True), key="edit_aktiv")
                            edit_pw_reset = st.checkbox(_("einstellungen.pw_reset"), value=ausgewaehlter.get("muss_passwort_aendern", False), key="edit_pw_reset")
                            neues_pw = st.text_input(_("einstellungen.neues_pw"), type="password", key="edit_neues_pw")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button(_("allgemein.speichern"), type="primary", key="save_benutzer"):
                                updates = {"name": edit_name, "email": edit_email, "rolle": edit_rolle, "aktiv": edit_aktiv, "muss_passwort_aendern": edit_pw_reset}
                                if neues_pw:
                                    if len(neues_pw) < 6:
                                        st.error(_("einstellungen.passwort_min_zeichen"))
                                    else:
                                        updates["passwort_hash"] = hash_passwort(neues_pw)
                                        aktualisiere_benutzer(benutzer_auswahl, updates)
                                        st.success(_("einstellungen.benutzer_gespeichert"))
                                        del st.session_state["benutzer_bearbeiten"]
                                        st.rerun()
                                else:
                                    aktualisiere_benutzer(benutzer_auswahl, updates)
                                    st.success(_("einstellungen.benutzer_gespeichert"))
                                    del st.session_state["benutzer_bearbeiten"]
                                    st.rerun()
                        with col2:
                            if st.button(_("allgemein.abbrechen"), key="cancel_edit"):
                                del st.session_state["benutzer_bearbeiten"]
                                st.rerun()

            # Rollen-Übersicht
            with st.expander(_("einstellungen.rollen_uebersicht")):
                st.markdown(f"""
| {_("einstellungen.rolle")} | {_("spalten.details")} |
|-------|--------|
| Administrator | {_("rollen.admin_rechte")} |
| Manager | {_("rollen.manager_rechte")} |
| Betrachter | {_("rollen.viewer_rechte")} |
""")
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
    st.markdown(f"## 📖 {_('hilfe.titel')}")
    st.markdown("---")

    # Inhaltsverzeichnis
    st.markdown(f"""
### {_('hilfe.inhaltsverzeichnis')}
1. [{_('hilfe.ueberblick')}](#overview)
2. [{_('hilfe.erste_schritte')}](#getting-started)
3. [{_('hilfe.import_analyse')}](#import-analysis)
4. [{_('hilfe.manueller_tankvorgang')}](#manual-entry)
5. [{_('hilfe.verbrauchsentwicklung')}](#consumption)
6. [{_('hilfe.historie')}](#history)
7. [{_('hilfe.auffaelligkeiten')}](#anomalies)
8. [{_('hilfe.einstellungen')}](#settings)
9. [{_('hilfe.faq')}](#faq)
""")

    st.markdown("---")

    # Überblick
    st.markdown(f"### {_('hilfe.ueberblick')}")
    st.markdown(_("hilfe.ueberblick_text"))

    st.markdown("---")

    # Erste Schritte
    st.markdown(f"### {_('hilfe.erste_schritte')}")
    st.markdown(_("hilfe.erste_schritte_text"))

    st.markdown("---")

    # Import & Analyse
    st.markdown(f"### {_('hilfe.import_analyse')}")
    st.markdown(_("hilfe.import_text"))

    st.markdown("---")

    # Manueller Tankvorgang
    st.markdown(f"### {_('hilfe.manueller_tankvorgang')}")
    st.markdown(_("hilfe.manueller_tankvorgang_text"))

    st.markdown("---")

    # Verbrauchsentwicklung
    st.markdown(f"### {_('hilfe.verbrauchsentwicklung')}")
    st.markdown(_("hilfe.verbrauch_text"))

    st.markdown("---")

    # Historie
    st.markdown(f"### {_('hilfe.historie')}")
    st.markdown(_("hilfe.historie_text"))

    st.markdown("---")

    # Auffälligkeiten
    st.markdown(f"### {_('hilfe.auffaelligkeiten')}")
    st.markdown(_("hilfe.auffaelligkeiten_text"))

    st.markdown("---")

    # Einstellungen
    st.markdown(f"### {_('hilfe.einstellungen')}")
    st.markdown(_("hilfe.einstellungen_text"))

    st.markdown("---")

    # Häufige Fragen
    st.markdown(f"### {_('hilfe.faq')}")
    st.markdown(_("hilfe.faq_text"))

    st.markdown("---")

    # Datenschutz
    st.markdown(f"### {_('hilfe.datenschutz')}")
    st.markdown(_("hilfe.datenschutz_text"))

    st.markdown("---")

    # Kontakt
    st.markdown(f"### {_('hilfe.kontakt')}")
    st.markdown(_("hilfe.kontakt_text"))
    st.link_button(
        _("hilfe.support_button"),
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
