#!/bin/bash
# DKV Abrechnungs-Checker Startskript

# Zum Skript-Verzeichnis wechseln
cd "$(dirname "$0")"

echo "=========================================="
echo "  DKV Abrechnungs-Checker wird gestartet"
echo "=========================================="
echo ""

# Prüfen ob venv existiert
if [ ! -d "venv" ]; then
    echo "Virtuelle Umgebung wird erstellt..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Abhängigkeiten werden installiert..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo ""
echo "Starte Streamlit-Server..."
echo "Die Anwendung öffnet sich gleich im Browser."
echo ""
echo "Zum Beenden: Ctrl+C drücken oder dieses Fenster schließen."
echo ""

# Streamlit starten und Browser öffnen
streamlit run dkv_checker.py
