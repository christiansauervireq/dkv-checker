#!/bin/bash
# SSL-Zertifikat-Generator für DKV-Checker
# Erstellt ein selbst-signiertes Zertifikat für lokale Entwicklung/Tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSL_DIR="$SCRIPT_DIR/ssl"

echo "=== SSL-Zertifikat-Generator ==="
echo ""

# SSL-Verzeichnis erstellen
mkdir -p "$SSL_DIR"

# Prüfen ob bereits Zertifikate existieren
if [ -f "$SSL_DIR/cert.pem" ] && [ -f "$SSL_DIR/key.pem" ]; then
    echo "Existierende Zertifikate gefunden."
    read -p "Überschreiben? (j/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Jj]$ ]]; then
        echo "Abgebrochen."
        exit 0
    fi
fi

echo "Erstelle selbst-signiertes SSL-Zertifikat..."

# Zertifikat generieren (gültig für 365 Tage)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/key.pem" \
    -out "$SSL_DIR/cert.pem" \
    -subj "/CN=dkv-checker/O=Self-Signed/C=DE" \
    2>/dev/null

echo ""
echo "Zertifikat erfolgreich erstellt!"
echo "  - Zertifikat: $SSL_DIR/cert.pem"
echo "  - Schlüssel:  $SSL_DIR/key.pem"
echo ""
echo "Hinweis: Dies ist ein selbst-signiertes Zertifikat."
echo "Browser werden eine Sicherheitswarnung anzeigen."
echo ""
echo "Starten Sie die Anwendung mit:"
echo "  docker-compose up -d"
echo ""
echo "Dann öffnen Sie: https://localhost"
